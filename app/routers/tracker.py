from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, user_permissions
from ..models import TrackerRecord, User
from ..permissions import CREATE_RECORDS, DELETE_RECORDS, EDIT_ALL_RECORDS, EDIT_OWN_RECORDS, VIEW_ALL_RECORDS
from ..schemas import TrackerRecordIn, TrackerRecordOut
from ..services.audit import audit

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


def can_edit(record: TrackerRecord, user: User, permissions: set[str]) -> bool:
    if EDIT_ALL_RECORDS in permissions:
        return True
    return EDIT_OWN_RECORDS in permissions and (record.owner_user_id == user.id or record.created_by_id == user.id)


@router.get("", response_model=list[TrackerRecordOut])
def list_records(q: str | None = None, status_filter: str | None = Query(default=None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    permissions = user_permissions(user, db)
    stmt = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None))
    if VIEW_ALL_RECORDS not in permissions:
        stmt = stmt.where(or_(TrackerRecord.owner_user_id == user.id, TrackerRecord.created_by_id == user.id))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(TrackerRecord.ticket_id.ilike(like), TrackerRecord.comments.ilike(like), TrackerRecord.tester_name_raw.ilike(like)))
    if status_filter:
        stmt = stmt.where(TrackerRecord.status == status_filter)
    return db.execute(stmt.order_by(TrackerRecord.updated_at.desc()).limit(500)).scalars().all()


@router.post("", response_model=TrackerRecordOut)
def create_record(payload: TrackerRecordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if CREATE_RECORDS not in user_permissions(user, db):
        raise HTTPException(status_code=403, detail="Permission denied")
    record = TrackerRecord(**payload.model_dump(exclude={"version"}), created_by_id=user.id, updated_by_id=user.id, owner_user_id=payload.owner_user_id or user.id)
    db.add(record)
    db.flush()
    audit(db, user, "create", "tracker_record", record.id, None, payload.model_dump())
    db.commit()
    db.refresh(record)
    return record


@router.put("/{record_id}", response_model=TrackerRecordOut)
def update_record(record_id: int, payload: TrackerRecordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(TrackerRecord, record_id)
    if not record or record.deleted_at:
        raise HTTPException(status_code=404, detail="Record not found")
    permissions = user_permissions(user, db)
    if not can_edit(record, user, permissions):
        raise HTTPException(status_code=403, detail="Permission denied")
    if payload.version is not None and payload.version != record.version:
        raise HTTPException(status_code=409, detail="Record was updated by someone else. Refresh and try again.")
    old = {"ticket_id": record.ticket_id, "status": record.status, "version": record.version}
    for field, value in payload.model_dump(exclude={"version"}).items():
        setattr(record, field, value)
    record.version += 1
    record.updated_by_id = user.id
    audit(db, user, "update", "tracker_record", record.id, old, payload.model_dump())
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if DELETE_RECORDS not in user_permissions(user, db):
        raise HTTPException(status_code=403, detail="Permission denied")
    record = db.get(TrackerRecord, record_id)
    if not record or record.deleted_at:
        raise HTTPException(status_code=404, detail="Record not found")
    record.deleted_at = datetime.utcnow()
    record.updated_by_id = user.id
    audit(db, user, "soft_delete", "tracker_record", record.id, {"deleted_at": None}, {"deleted_at": record.deleted_at})
    db.commit()
    return {"ok": True}
