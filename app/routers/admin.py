from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_permission
from ..models import Role, User
from ..permissions import MANAGE_USERS
from ..schemas import UserCreate, UserUpdate
from ..security import hash_password
from ..services.audit import audit

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def users(db: Session = Depends(get_db), actor: User = Depends(require_permission(MANAGE_USERS))):
    return db.execute(select(User).order_by(User.email)).scalars().all()


@router.get("/roles")
def roles(db: Session = Depends(get_db), actor: User = Depends(require_permission(MANAGE_USERS))):
    return db.execute(select(Role).order_by(Role.name)).scalars().all()


@router.post("/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission(MANAGE_USERS))):
    role = db.get(Role, payload.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Role does not exist")
    user = User(email=payload.email.lower(), display_name=payload.display_name, password_hash=hash_password(payload.password), role_id=payload.role_id, active=payload.active)
    db.add(user)
    db.flush()
    audit(db, actor, "create_user", "user", user.id, None, {"email": user.email, "role_id": user.role_id})
    db.commit()
    return {"id": user.id, "email": user.email}


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission(MANAGE_USERS))):
    if user_id == actor.id and payload.role_id is not None:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old = {"display_name": user.display_name, "role_id": user.role_id, "active": user.active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    audit(db, actor, "update_user", "user", user.id, old, payload.model_dump(exclude_unset=True))
    db.commit()
    return {"ok": True}
