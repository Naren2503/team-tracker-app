import json
from typing import Any
from sqlalchemy.orm import Session
from ..models import AuditLog, User


def audit(db: Session, actor: User | None, action: str, entity_type: str, entity_id: str | int | None, old: Any = None, new: Any = None) -> None:
    db.add(AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        old_value_json=json.dumps(old, default=str) if old is not None else None,
        new_value_json=json.dumps(new, default=str) if new is not None else None,
    ))
