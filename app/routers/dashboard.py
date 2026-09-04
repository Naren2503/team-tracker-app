from calendar import monthrange
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..services.dashboard import dashboard_metrics, filter_options

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics")
def metrics(start: date | None = None, end: date | None = None, month: str | None = None, tester: str | None = None, status: str | None = None, granularity: str = "month", week: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if month:
        try:
            year, month_number = (int(value) for value in month.split("-"))
            start = date(year, month_number, 1)
            end = date(year, month_number, monthrange(year, month_number)[1])
        except (TypeError, ValueError):
            pass
    return dashboard_metrics(db, start=start, end=end, tester=tester, status=status, granularity=granularity, week=week)


@router.get("/filters")
def filters(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return filter_options(db)
