import csv
from io import StringIO
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import TrackerRecord, User
from ..permissions import EXPORT_DATA, VIEW_ALL_RECORDS
from ..dependencies import user_permissions
from ..services.audit import audit

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/tracker.csv")
def export_tracker(db: Session = Depends(get_db), user: User = Depends(require_permission(EXPORT_DATA))):
    stmt = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None))
    if VIEW_ALL_RECORDS not in user_permissions(user, db):
        stmt = stmt.where(or_(TrackerRecord.owner_user_id == user.id, TrackerRecord.created_by_id == user.id))
    records = db.execute(stmt.order_by(TrackerRecord.ticket_id)).scalars().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket ID", "Date Started", "Date Ended", "Tester", "Status", "Zephyr Upload", "Comments", "Version"])
    for record in records:
        writer.writerow([record.ticket_id, record.date_started, record.date_ended, record.tester_name_raw, record.status, record.zephyr_upload, record.comments, record.version])
    audit(db, user, "export", "tracker_records", None, None, {"rows": len(records), "format": "csv"})
    db.commit()
    return PlainTextResponse(output.getvalue(), media_type="text/csv")
