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
    configured = bool(settings.jira_base_url and settings.jira_email and settings.jira_api_token)
    return templates.TemplateResponse(
        "jira.html",
        {"request": request, "user": user, "permissions": user_permissions(user, db), "page": "jira", "configured": configured, "project_key": settings.jira_project_key or ""},
    )


@router.get("/issues")
async def issues(user: User = Depends(get_current_user)):
    settings = get_settings()
    if not (settings.jira_base_url and settings.jira_email and settings.jira_api_token):
        raise HTTPException(status_code=503, detail="Jira is not configured")
    jql = f"project = {settings.jira_project_key} ORDER BY updated DESC" if settings.jira_project_key else "ORDER BY updated DESC"
    url = f"{settings.jira_base_url.rstrip('/')}/rest/api/3/search"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params={"jql": jql, "maxResults": 100, "fields": "summary,status,priority,assignee,updated"}, auth=(settings.jira_email, settings.jira_api_token))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Jira request failed: {exc}") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Jira returned HTTP {response.status_code}")
    data = response.json()
    return [{"key": issue["key"], "summary": issue.get("fields", {}).get("summary"), "status": (issue.get("fields", {}).get("status") or {}).get("name"), "priority": (issue.get("fields", {}).get("priority") or {}).get("name"), "assignee": (issue.get("fields", {}).get("assignee") or {}).get("displayName"), "updated": issue.get("fields", {}).get("updated")} for issue in data.get("issues", [])]