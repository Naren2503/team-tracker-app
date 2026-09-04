from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import AuditLog, User
from ..permissions import VIEW_AUDIT

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def audit_logs(q: str | None = None, action: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW_AUDIT))):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(AuditLog.entity_id.ilike(like), AuditLog.entity_type.ilike(like), AuditLog.new_value_json.ilike(like)))
    return db.execute(stmt.order_by(AuditLog.created_at.desc()).limit(500)).scalars().all()
