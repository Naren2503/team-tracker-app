import csv
from io import StringIO
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import TrackerRecord, User
from ..permissions import EXPORT_DATA
from ..services.audit import audit

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/tracker.csv")
def export_tracker(db: Session = Depends(get_db), user: User = Depends(require_permission(EXPORT_DATA))):
    records = db.execute(select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None)).order_by(TrackerRecord.ticket_id)).scalars().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket ID", "Date Started", "Date Ended", "Tester", "Status", "Zephyr Upload", "Comments", "Version"])
    for record in records:
        writer.writerow([record.ticket_id, record.date_started, record.date_ended, record.tester_name_raw, record.status, record.zephyr_upload, record.comments, record.version])
    audit(db, user, "export", "tracker_records", None, None, {"rows": len(records), "format": "csv"})
    db.commit()
    return PlainTextResponse(output.getvalue(), media_type="text/csv")
