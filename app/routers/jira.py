import httpx
from fastapi import APIRouter, Depends, HTTPException
from ..config import get_settings
from ..dependencies import get_current_user, require_permission
from ..models import User
from ..permissions import VIEW_JIRA
from ..services import jira as jira_service

router = APIRouter(prefix="/api/jira", tags=["jira"])


@router.get("/status")
def jira_status(user: User = Depends(get_current_user)):
    return {"configured": jira_service.is_configured()}


@router.get("/search")
def jira_search(q: str | None = None, project: str | None = None, user: User = Depends(require_permission(VIEW_JIRA))):
    if not jira_service.is_configured():
        raise HTTPException(status_code=503, detail="Jira integration is not configured")
    try:
        issues = jira_service.search(q, project)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Jira request failed: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Unable to reach Jira") from exc
    return {"issues": issues, "base_url": get_settings().jira_base_url}


@router.get("/board")
def jira_board(q: str | None = None, project: str | None = None, user: User = Depends(require_permission(VIEW_JIRA))):
    if not jira_service.is_configured():
        raise HTTPException(status_code=503, detail="Jira integration is not configured")
    try:
        columns = jira_service.board_columns(q, project)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Jira request failed: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Unable to reach Jira") from exc
    return {"columns": columns, "base_url": get_settings().jira_base_url}
