from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..security import create_access_token, verify_password

router = APIRouter()


@router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if not user or not user.active or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=Invalid%20email%20or%20password", status_code=status.HTTP_303_SEE_OTHER)
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("access_token", create_access_token(str(user.id)), httponly=True, secure=False, samesite="lax")
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response
