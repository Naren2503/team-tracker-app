import csv
import hmac
from io import StringIO
from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import ImportBatch, ImportRow, Role, User
from ..permissions import IMPORT_EXCEL
from ..services.importer import import_grid_data, import_workbook, preview_import
from ..config import get_settings

router = APIRouter(prefix="/api/imports", tags=["imports"])


class OfficeScriptSyncRequest(BaseModel):
    sheets: dict[str, list[list[Any]]]
    mode: str = "replace"


def verify_webhook_token(token: str) -> None:
    expected_token = get_settings().webhook_token
    if not expected_token:
        raise HTTPException(status_code=503, detail="Webhook sync is not configured")
    if not hmac.compare_digest(token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid token")


def validate_upload(file_name: str, content: bytes) -> None:
    settings = get_settings()
    if not file_name or not file_name.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xlsm files are allowed")
    if len(content) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is larger than the configured upload limit")


def get_sync_actor(db: Session) -> User:
    settings = get_settings()
    user = None
    if settings.seed_admin_email:
        user = db.execute(select(User).where(User.email == settings.seed_admin_email.lower())).scalar_one_or_none()
    if not user:
        user = db.execute(select(User).join(Role).where(Role.name == "Admin")).scalars().first()
    if not user:
        user = db.execute(select(User)).scalars().first()
    if not user:
        raise HTTPException(status_code=500, detail="No system user found to perform import")
    return user


@router.post("/preview")
async def preview(file: UploadFile = File(...), user: User = Depends(require_permission(IMPORT_EXCEL))):
    content = await file.read()
    validate_upload(file.filename or "", content)
    return preview_import(content)


@router.post("")
async def import_file(mode: str = Form("merge"), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_permission(IMPORT_EXCEL))):
    content = await file.read()
    validate_upload(file.filename or "upload.xlsx", content)
    batch = import_workbook(db, user, file.filename or "upload.xlsx", content, mode)
    return {"id": batch.id, "status": batch.status, "successful_rows": batch.successful_rows, "rejected_rows": batch.rejected_rows}


@router.post("/webhook")
async def webhook_import(
    request: Request,
    token: str = Query(...),
    mode: str = Query("merge"),
    db: Session = Depends(get_db),
):
    verify_webhook_token(token)

    content_type = request.headers.get("content-type", "")
    content = b""
    file_name = request.headers.get("X-Team-Tracker-Source", "teams_auto_sync.xlsm")
    if not file_name.lower().endswith((".xlsx", ".xlsm")):
        file_name = "teams_auto_sync.xlsm"

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded = form.get("file")
        if not uploaded:
            raise HTTPException(status_code=400, detail="Missing file in multipart form")
        content = await uploaded.read()
        file_name = getattr(uploaded, "filename", file_name)
    else:
        content = await request.body()

    if not content:
        raise HTTPException(status_code=400, detail="Empty payload received")

    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid Excel file (.xlsx / .xlsm)")

    actor = get_sync_actor(db)
    batch = import_workbook(db, actor, file_name, content, mode)
    return {
        "status": "success",
        "batch_id": batch.id,
        "import_status": batch.status,
        "successful_rows": batch.successful_rows,
        "rejected_rows": batch.rejected_rows,
    }


@router.post("/office-script-sync")
async def office_script_sync(
    payload: OfficeScriptSyncRequest,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    verify_webhook_token(token)

    if not payload.sheets:
        raise HTTPException(status_code=400, detail="No sheet data provided in payload")

    actor = get_sync_actor(db)
    batch = import_grid_data(db, actor, "Excel Online Office Script", payload.sheets, payload.mode)
    return {
        "status": "success",
        "batch_id": batch.id,
        "import_status": batch.status,
        "successful_rows": batch.successful_rows,
        "rejected_rows": batch.rejected_rows,
    }


@router.get("")
def history(db: Session = Depends(get_db), user: User = Depends(require_permission(IMPORT_EXCEL))):
    return db.execute(select(ImportBatch).order_by(ImportBatch.started_at.desc()).limit(50)).scalars().all()


@router.get("/{import_id}/errors.csv")
def error_report(import_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission(IMPORT_EXCEL))):
    rows = db.execute(select(ImportRow).where(ImportRow.import_id == import_id, ImportRow.status == "rejected")).scalars().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["sheet", "row_number", "error_message", "raw_json"])
    for row in rows:
        writer.writerow([row.sheet_name, row.row_number, row.error_message, row.raw_json])
    return PlainTextResponse(output.getvalue(), media_type="text/csv")
