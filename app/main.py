from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy import or_
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .config import get_settings
from .dependencies import current_user_or_none, user_permissions
from .models import AuditLog, ImportBatch, TrackerRecord, User
from .permissions import IMPORT_EXCEL, VIEW_ALL_RECORDS
from .routers import admin, audit, auth, dashboard, exports, imports, tracker
from .seed import seed_reference_data
from .services.dashboard import backlog_metrics, dashboard_metrics, filter_options

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()
app = FastAPI(title="Team Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(auth.router)
app.include_router(tracker.router)
app.include_router(imports.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(audit.router)
app.include_router(exports.router)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        seed_reference_data(db)


def page_context(request: Request, user: User | None, db: Session) -> dict:
    permissions = user_permissions(user, db) if user else set()
    return {"request": request, "user": user, "permissions": permissions}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(current_user_or_none)):
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request, "error": request.query_params.get("error")})


@app.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    if not user:
        return RedirectResponse("/login")
    context = page_context(request, user, db)
    current_month = date.today().replace(day=1)
    default_start = (current_month - timedelta(days=5 * 31)).replace(day=1)
    context.update({"metrics": dashboard_metrics(db), "filters": filter_options(db), "page": "dashboard", "view": "dashboard", "default_start_month": default_start.strftime("%Y-%m"), "default_end_month": date.today().strftime("%Y-%m"), "default_month": current_month.strftime("%Y-%m")})
    return templates.TemplateResponse("dashboard.html", context)


def report_page(view: str, request: Request, db: Session, user: User | None):
    if not user:
        return RedirectResponse("/login")
    context = page_context(request, user, db)
    current_month = date.today().replace(day=1)
    current_month_end = date(current_month.year, current_month.month, monthrange(current_month.year, current_month.month)[1])
    default_start = (current_month - timedelta(days=5 * 31)).replace(day=1)
    metrics = dashboard_metrics(db, start=current_month, end=current_month_end, granularity="week" if view == "weekly" else "month", report_view=view)
    context.update({"metrics": metrics, "filters": filter_options(db), "page": view, "view": view, "default_start_month": default_start.strftime("%Y-%m"), "default_end_month": date.today().strftime("%Y-%m"), "default_month": current_month.strftime("%Y-%m")})
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/monthly", response_class=HTMLResponse)
def monthly_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    return report_page("monthly", request, db, user)


@app.get("/weekly", response_class=HTMLResponse)
def weekly_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    return report_page("weekly", request, db, user)


@app.get("/utilization", response_class=HTMLResponse)
def utilization_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    return report_page("utilization", request, db, user)


@app.get("/backlog", response_class=HTMLResponse)
def backlog_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    if not user:
        return RedirectResponse("/login")
    current_month = date.today().replace(day=1)
    default_start = (current_month - timedelta(days=5 * 31)).replace(day=1)
    current_month_end = date(current_month.year, current_month.month, monthrange(current_month.year, current_month.month)[1])
    context = page_context(request, user, db)
    context.update({
        "rows": backlog_metrics(db, default_start, current_month_end),
        "filters": filter_options(db),
        "page": "backlog",
        "view": "backlog",
        "default_start_month": default_start.strftime("%Y-%m"),
        "default_end_month": current_month.strftime("%Y-%m"),
    })
    return templates.TemplateResponse("backlog.html", context)


@app.get("/tracker", response_class=HTMLResponse)
def tracker_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    if not user:
        return RedirectResponse("/login")
    permissions = user_permissions(user, db)
    stmt = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None))
    if VIEW_ALL_RECORDS not in permissions:
        stmt = stmt.where(or_(TrackerRecord.owner_user_id == user.id, TrackerRecord.created_by_id == user.id))
    records = db.execute(stmt.order_by(TrackerRecord.updated_at.desc()).limit(5000)).scalars().all()
    context = page_context(request, user, db)
    context.update({"records": records, "today": date.today(), "filters": filter_options(db), "page": "tracker"})
    return templates.TemplateResponse("tracker.html", context)


@app.get("/import", response_class=HTMLResponse)
def import_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    if not user:
        return RedirectResponse("/login")
    if IMPORT_EXCEL not in user_permissions(user, db):
        return RedirectResponse("/")
    imports_list = db.execute(select(ImportBatch).order_by(ImportBatch.started_at.desc()).limit(20)).scalars().all()
    settings = get_settings()
    webhook_token = settings.webhook_token or "<WEBHOOK_TOKEN>"
    app_url = str(request.base_url).rstrip("/")
    context = page_context(request, user, db)
    context.update({
        "imports": imports_list,
        "page": "import",
        "webhook_url": f"{app_url}/api/imports/webhook?token={webhook_token}&mode=replace",
        "office_script_sync_url": f"{app_url}/api/imports/office-script-sync?token={webhook_token}&mode=replace",
    })
    return templates.TemplateResponse("import.html", context)


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    if not user:
        return RedirectResponse("/login")
    permissions = user_permissions(user, db)
    if "manage_users" not in permissions:
        return RedirectResponse("/")
    context = page_context(request, user, db)
    context.update({"page": "admin"})
    return templates.TemplateResponse("admin.html", context)


@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_or_none)):
    if not user:
        return RedirectResponse("/login")
    permissions = user_permissions(user, db)
    if "view_audit_log" not in permissions:
        return RedirectResponse("/")
    logs = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).scalars().all()
    context = page_context(request, user, db)
    context.update({"logs": logs, "page": "audit"})
    return templates.TemplateResponse("audit.html", context)
