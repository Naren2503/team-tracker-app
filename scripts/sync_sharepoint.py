from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def request_json(url: str, data: bytes, headers: dict[str, str]) -> dict:
    request = Request(url, data=data, headers=headers, method="POST")
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=120) as response:
        return response.read()


def graph_access_token() -> str:
    tenant_id = require_env("MS_TENANT_ID")
    payload = urlencode({
        "client_id": require_env("MS_CLIENT_ID"),
        "client_secret": require_env("MS_CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode("utf-8")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    result = request_json(token_url, payload, {"Content-Type": "application/x-www-form-urlencoded"})
    return result["access_token"]


def download_workbook(access_token: str) -> bytes:
    site_id = require_env("SHAREPOINT_SITE_ID")
    drive_id = require_env("SHAREPOINT_DRIVE_ID")
    item_id = os.getenv("SHAREPOINT_ITEM_ID")
    headers = {"Authorization": f"Bearer {access_token}"}
    if item_id:
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
    else:
        file_path = quote(require_env("SHAREPOINT_FILE_PATH").strip("/"), safe="/")
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{file_path}:/content"
    return request_bytes(url, headers)


def upload_to_tracker(content: bytes) -> dict:
    base_url = os.getenv("TEAM_TRACKER_BASE_URL", "https://naren2503-team-tracker.onrender.com").rstrip("/")
    token = quote(require_env("TEAM_TRACKER_WEBHOOK_TOKEN"), safe="")
    mode = os.getenv("IMPORT_MODE", "replace")
    url = f"{base_url}/api/imports/webhook?token={token}&mode={mode}"
    request = Request(
        url,
        data=content,
        headers={"Content-Type": "application/vnd.ms-excel"},
        method="POST",
    )
    with urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    try:
        access_token = graph_access_token()
        content = download_workbook(access_token)
        if not content.startswith(b"PK\x03\x04"):
            raise RuntimeError("Downloaded SharePoint file is not a valid Excel workbook")
        result = upload_to_tracker(content)
        print(json.dumps(result, indent=2))
        if result.get("rejected_rows", 0):
            return 2
        return 0
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP error {exc.code}: {body}", file=sys.stderr)
        return 1
    except (RuntimeError, URLError, KeyError, json.JSONDecodeError) as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())