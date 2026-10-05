from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import PasswordResetToken, User
from ..security import create_access_token, generate_reset_token, hash_password, hash_reset_token, verify_password
from ..config import get_settings
from ..services.mailer import send_email

router = APIRouter()
RESET_TOKEN_TTL_MINUTES = 30


@router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if not user or not user.active or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=Invalid%20email%20or%20password", status_code=status.HTTP_303_SEE_OTHER)
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("access_token", create_access_token(str(user.id)), httponly=True, secure=get_settings().secure_cookies, samesite="lax")
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
    if user and user.active:
        token = generate_reset_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_reset_token(token), expires_at=datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)))
        db.commit()
        reset_link = f"{get_settings().app_base_url.rstrip('/')}/reset-password?token={token}"
        send_email(
            user.email,
            "Reset your Team Tracker password",
            f"Hi {user.display_name},\n\nUse the link below to reset your password. It expires in {RESET_TOKEN_TTL_MINUTES} minutes.\n\n{reset_link}\n\nIf you didn't request this, you can ignore this email.",
        )
    # Always respond the same way so we don't reveal whether an email is registered.
    return RedirectResponse("/forgot-password?sent=1", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return RedirectResponse(f"/reset-password?token={token}&error=Passwords%20do%20not%20match", status_code=status.HTTP_303_SEE_OTHER)
    if len(password) < 12:
        return RedirectResponse(f"/reset-password?token={token}&error=Password%20must%20be%20at%20least%2012%20characters", status_code=status.HTTP_303_SEE_OTHER)
    record = db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_reset_token(token))).scalar_one_or_none()
    expires_at = record.expires_at if record else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if not record or record.used_at is not None or expires_at < datetime.now(UTC):
        return RedirectResponse("/forgot-password?error=Reset%20link%20is%20invalid%20or%20expired", status_code=status.HTTP_303_SEE_OTHER)
    user = db.get(User, record.user_id)
    if not user or not user.active:
        return RedirectResponse("/forgot-password?error=Reset%20link%20is%20invalid%20or%20expired", status_code=status.HTTP_303_SEE_OTHER)
    user.password_hash = hash_password(password)
    record.used_at = datetime.now(UTC)
    db.commit()
    return RedirectResponse("/login?notice=Password%20updated.%20Please%20sign%20in.", status_code=status.HTTP_303_SEE_OTHER)
