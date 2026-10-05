import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .models import Lookup, Permission, Role, RolePermission, User
from .permissions import ALL_PERMISSIONS, ROLE_DEFAULTS
from .security import hash_password

logger = logging.getLogger("app.seed")


def seed_reference_data(db: Session) -> None:
    permissions = {}
    for code in ALL_PERMISSIONS:
        permission = db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()
        if not permission:
            permission = Permission(code=code, description=code.replace("_", " ").title())
            db.add(permission)
            db.flush()
        permissions[code] = permission

    for role_name, permission_codes in ROLE_DEFAULTS.items():
        role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Default {role_name} role")
            db.add(role)
            db.flush()
        existing = {rp.permission.code for rp in role.permissions}
        for code in permission_codes:
            if code not in existing:
                db.add(RolePermission(role_id=role.id, permission_id=permissions[code].id))

    lookup_values = {
        "status": ["Completed", "In progress", "Blocked", "Pending", "Withdrawn"],
        "priority": ["High", "Medium", "Low"],
        "task": ["Analysis", "Design", "Execution", "Innovation", "Support/Meetings", "Learnings"],
        "workstream": ["FT", "BT", "DQ", "Others"],
        "upload_status": ["Uploaded - Signed Off", "Uploaded - In progress"],
    }
    for kind, values in lookup_values.items():
        for value in values:
            normalized = value.lower()
            if not db.execute(select(Lookup).where(Lookup.kind == kind, Lookup.normalized == normalized)).scalar_one_or_none():
                db.add(Lookup(kind=kind, label=value, normalized=normalized))

    settings = get_settings()
    logger.info("Seed admin config: email=%r reset=%s backend=%s", settings.seed_admin_email, settings.seed_admin_reset, settings.database_url.split("://")[0])
    if settings.seed_admin_email and settings.seed_admin_password:
        seed_email = settings.seed_admin_email.lower()
        existing = db.execute(select(User).where(User.email == seed_email)).scalar_one_or_none()
        admin_role = db.execute(select(Role).where(Role.name == "Admin")).scalar_one()
        if not existing:
            db.add(User(email=seed_email, display_name=settings.seed_admin_name, password_hash=hash_password(settings.seed_admin_password), role_id=admin_role.id, active=True))
            logger.info("Seed admin %r created", seed_email)
        elif settings.seed_admin_reset:
            existing.password_hash = hash_password(settings.seed_admin_password)
            existing.role_id = admin_role.id
            existing.active = True
            logger.info("Seed admin %r password/role/active reset", seed_email)
        else:
            logger.info("Seed admin %r already exists; set SEED_ADMIN_RESET=true to re-apply the password", seed_email)
        known = [user.email for user in db.execute(select(User.email).order_by(User.email)).scalars().all()]
        logger.info("Existing user emails: %s", known)
    else:
        logger.warning("SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD not set; no admin seeded")
    db.commit()
