import httpx
from ..config import get_settings

STATUS_CATEGORY_ORDER = ["To Do", "In Progress", "Done"]


class JiraError(RuntimeError):
    """Raised when Jira cannot be reached or returns an unexpected response."""


def is_configured() -> bool:
    settings = get_settings()
    if not (settings.jira_base_url and settings.jira_api_token):
        return False
    if settings.jira_auth_mode == "bearer":
        return True
    return bool(settings.jira_email)


def _client() -> httpx.Client:
    settings = get_settings()
    if not is_configured():
        raise RuntimeError("Jira integration is not configured")
    headers = {"Accept": "application/json"}
    auth = None
    if settings.jira_auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {settings.jira_api_token}"
    else:
        auth = (settings.jira_email, settings.jira_api_token)
    return httpx.Client(
        base_url=settings.jira_base_url.rstrip("/"),
        auth=auth,
        timeout=15.0,
        headers=headers,
    )


def _map_issue(issue: dict) -> dict:
    fields = issue.get("fields", {}) or {}
    status = fields.get("status") or {}
    assignee = fields.get("assignee") or {}
    priority = fields.get("priority") or {}
    issuetype = fields.get("issuetype") or {}
    return {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": status.get("name"),
        "status_category": (status.get("statusCategory") or {}).get("name") or "To Do",
        "assignee": assignee.get("displayName"),
        "priority": priority.get("name"),
        "issue_type": issuetype.get("name"),
        "updated": fields.get("updated"),
    }


def search_issues(jql: str, max_results: int = 50) -> list[dict]:
    try:
        with _client() as client:
            response = client.get(
                "/rest/api/3/search",
                params={"jql": jql, "maxResults": max_results, "fields": "summary,status,assignee,priority,issuetype,updated"},
            )
    except httpx.RequestError as exc:
        raise JiraError(f"Unable to reach Jira at {get_settings().jira_base_url}: {exc}") from exc
    if response.status_code >= 400:
        raise JiraError(f"Jira returned HTTP {response.status_code}: {response.text[:200]}")
    try:
        data = response.json()
    except ValueError as exc:
        raise JiraError(
            f"Jira did not return JSON (got: {response.text[:200]!r}). "
            "This usually means the Jira base URL is not reachable from this server "
            "(e.g. an internal-only network address) or a proxy/login page was returned instead."
        ) from exc
    return [_map_issue(issue) for issue in data.get("issues", [])]


def _build_jql(query: str | None, project_key: str | None) -> str:
    clauses = []
    if project_key:
        clauses.append(f'project = "{project_key}"')
    if query:
        escaped = query.replace('"', '\\"')
        clauses.append(f'text ~ "{escaped}*"')
    jql = " AND ".join(clauses)
    return f"{jql} ORDER BY updated DESC" if jql else "ORDER BY updated DESC"


def search(query: str | None = None, project_key: str | None = None, max_results: int = 50) -> list[dict]:
    return search_issues(_build_jql(query, project_key), max_results=max_results)


def board_columns(query: str | None = None, project_key: str | None = None, max_results: int = 100) -> dict[str, list[dict]]:
    settings = get_settings()
    issues = search(query, project_key or settings.jira_project_key, max_results=max_results)
    columns: dict[str, list[dict]] = {name: [] for name in STATUS_CATEGORY_ORDER}
    for issue in issues:
        columns.setdefault(issue["status_category"], []).append(issue)
    return columns
