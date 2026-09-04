import csv
from io import StringIO
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import ImportBatch, ImportRow, User
from ..permissions import IMPORT_EXCEL
from ..services.importer import import_workbook, preview_import
from ..config import get_settings

router = APIRouter(prefix="/api/imports", tags=["imports"])


def validate_upload(file: UploadFile, content: bytes) -> None:
    settings = get_settings()
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xlsm files are allowed")
    if len(content) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is larger than the configured upload limit")


@router.post("/preview")
async def preview(file: UploadFile = File(...), user: User = Depends(require_permission(IMPORT_EXCEL))):
    content = await file.read()
    validate_upload(file, content)
    return preview_import(content)


@router.post("")
async def import_file(mode: str = Form("merge"), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_permission(IMPORT_EXCEL))):
    content = await file.read()
    validate_upload(file, content)
    batch = import_workbook(db, user, file.filename or "upload.xlsx", content, mode)
    return {"id": batch.id, "status": batch.status, "successful_rows": batch.successful_rows, "rejected_rows": batch.rejected_rows}


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
