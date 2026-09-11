import csv
from io import StringIO
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import TrackerRecord, User, WorkLog
from ..permissions import EXPORT_DATA, VIEW_ALL_RECORDS
from ..dependencies import user_permissions
from ..services.audit import audit

router = APIRouter(prefix="/api/exports", tags=["exports"])


def csv_response(content: str, filename: str) -> PlainTextResponse:
    return PlainTextResponse(content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


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
    return csv_response(output.getvalue(), "dq-team-tracker-records.csv")


@router.get("/work-logs.csv")
def export_work_logs(db: Session = Depends(get_db), user: User = Depends(require_permission(EXPORT_DATA))):
    stmt = select(WorkLog).where(WorkLog.deleted_at.is_(None))
    if VIEW_ALL_RECORDS not in user_permissions(user, db):
        stmt = stmt.where(WorkLog.created_by_id == user.id)
    work_logs = db.execute(stmt.order_by(WorkLog.work_date, WorkLog.source_sheet, WorkLog.source_row)).scalars().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket ID", "Workstream", "Tester", "Task", "Priority", "Date", "Work Log Hours", "Passed TC", "Passed Steps", "Failed TC", "Failed Steps", "Daily Comments", "Source Sheet", "Source Row"])
    for work_log in work_logs:
        writer.writerow([work_log.ticket_id_raw, work_log.workstream, work_log.tester_name_raw, work_log.task, work_log.priority, work_log.work_date, work_log.work_log_hours, work_log.passed_tc, work_log.passed_steps, work_log.failed_tc, work_log.failed_steps, work_log.daily_comments, work_log.source_sheet, work_log.source_row])
    audit(db, user, "export", "work_logs", None, None, {"rows": len(work_logs), "format": "csv"})
    db.commit()
    return csv_response(output.getvalue(), "dq-team-tracker-work-logs.csv")
