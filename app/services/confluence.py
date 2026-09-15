"""Fetches a Confluence page's rendered content via the Cloud REST API."""
import httpx

from ..config import Settings


def fetch_confluence_page(settings: Settings) -> dict:
    if not (settings.confluence_base_url and settings.confluence_email and settings.confluence_api_token and settings.confluence_page_id):
        return {"configured": False, "title": None, "html": None, "url": None, "error": None}

    base_url = settings.confluence_base_url.rstrip("/")
    api_url = f"{base_url}/wiki/rest/api/content/{settings.confluence_page_id}"
    page_url = f"{base_url}/wiki/pages/viewpage.action?pageId={settings.confluence_page_id}"

    try:
        response = httpx.get(
            api_url,
            params={"expand": "body.view"},
            auth=(settings.confluence_email, settings.confluence_api_token),
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "configured": True,
            "title": data.get("title"),
            "html": data.get("body", {}).get("view", {}).get("value"),
            "url": page_url,
            "error": None,
        }
    except httpx.HTTPStatusError as exc:
        return {"configured": True, "title": None, "html": None, "url": page_url, "error": f"Confluence API error: {exc.response.status_code}"}
    except httpx.HTTPError as exc:
        return {"configured": True, "title": None, "html": None, "url": page_url, "error": f"Could not reach Confluence: {exc}"}
