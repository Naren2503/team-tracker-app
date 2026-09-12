from pathlib import Path
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..config import get_settings
from ..dependencies import get_current_user, user_permissions
from ..models import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/jira", tags=["jira"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def render_page(request: Request, db: Session, user: User) -> HTMLResponse:
    settings = get_settings()
    configured = bool(settings.jira_base_url and settings.jira_api_token and (settings.jira_auth_mode.casefold() == "bearer" or settings.jira_email))
    return templates.TemplateResponse(
        "jira.html",
        {"request": request, "user": user, "permissions": user_permissions(user, db), "page": "jira", "configured": configured, "project_key": settings.jira_project_key or ""},
    )


@router.get("/issues")
async def issues(user: User = Depends(get_current_user)):
    settings = get_settings()
    auth_mode = settings.jira_auth_mode.casefold()
    if not (settings.jira_base_url and settings.jira_api_token and (auth_mode == "bearer" or settings.jira_email)):
        raise HTTPException(status_code=503, detail="Jira is not configured")
    jql = f"project = {settings.jira_project_key} ORDER BY updated DESC" if settings.jira_project_key else "ORDER BY updated DESC"
    api_version = "2" if auth_mode == "bearer" else "3"
    url = f"{settings.jira_base_url.rstrip('/')}/rest/api/{api_version}/search"
    headers = {"Accept": "application/json"}
    auth = None
    if auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {settings.jira_api_token}"
    else:
        auth = (settings.jira_email, settings.jira_api_token)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params={"jql": jql, "maxResults": 100, "fields": "summary,status,priority,assignee,updated"}, headers=headers, auth=auth)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Jira request failed: {exc}") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Jira returned HTTP {response.status_code}")
    data = response.json()
    return [{"key": issue["key"], "summary": issue.get("fields", {}).get("summary"), "status": (issue.get("fields", {}).get("status") or {}).get("name"), "priority": (issue.get("fields", {}).get("priority") or {}).get("name"), "assignee": (issue.get("fields", {}).get("assignee") or {}).get("displayName"), "updated": issue.get("fields", {}).get("updated")} for issue in data.get("issues", [])]