"""Thin requests-only wrapper around the World Anvil Boromir v2 API.

No third-party WA library. Every function takes a `creds` dict with keys
`application_key`, `auth_token`, `world_id` (see credentials.py) and raises
`WAApiError` on any non-2xx response.
"""
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://www.worldanvil.com/api/external/boromir/"
USER_AGENT = "WorldAnvilArticleSkill (https://github.com/, 1.0)"
PAGE_LIMIT = 50


class WAApiError(Exception):
    """Raised for any non-2xx response from the Boromir API."""

    def __init__(self, status_code: int, message: str, body: Optional[Dict[str, Any]] = None):
        super().__init__(f"WA API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body or {}


def build_headers(creds: Dict[str, str], with_content_type: bool = False) -> Dict[str, str]:
    headers = {
        "x-auth-token": creds["auth_token"],
        "x-application-key": creds["application_key"],
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if with_content_type:
        headers["Content-type"] = "application/json"
    return headers


def _raise_for_error(response: requests.Response) -> Dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400 or body.get("success") is False:
        message = body.get("error", response.reason or "Unknown error")
        raise WAApiError(response.status_code, message, body)
    return body


def _get(path: str, creds: Dict[str, str], params: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(BASE_URL + path, params=params, headers=build_headers(creds))
    return _raise_for_error(response)


def _post(path: str, creds: Dict[str, str], params: Dict[str, Any], json_body: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        BASE_URL + path, params=params, json=json_body, headers=build_headers(creds, with_content_type=True)
    )
    return _raise_for_error(response)


def _put(path: str, creds: Dict[str, str], json_body: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.put(BASE_URL + path, json=json_body, headers=build_headers(creds, with_content_type=True))
    return _raise_for_error(response)


def _patch(path: str, creds: Dict[str, str], article_id: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.patch(
        BASE_URL + path,
        params={"id": article_id},
        json=json_body,
        headers=build_headers(creds, with_content_type=True),
    )
    return _raise_for_error(response)


def _scroll(path: str, creds: Dict[str, str], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """POST-list endpoints: loop offset until an empty page comes back."""
    results: List[Dict[str, Any]] = []
    offset = 0
    while True:
        body = _post(path, creds, params, {"limit": PAGE_LIMIT, "offset": offset})
        entities = body.get("entities", [])
        if not entities:
            break
        results.extend(entities)
        offset += PAGE_LIMIT
    return results


def get_identity(creds: Dict[str, str]) -> Dict[str, Any]:
    return _get("identity", creds, {})


def list_user_worlds(creds: Dict[str, str], user_id: str) -> List[Dict[str, Any]]:
    return _scroll("user/worlds", creds, {"id": user_id})


def list_categories(creds: Dict[str, str]) -> List[Dict[str, Any]]:
    return _scroll("world/categories", creds, {"id": creds["world_id"]})


def list_articles(creds: Dict[str, str]) -> List[Dict[str, Any]]:
    return _scroll("world/articles", creds, {"id": creds["world_id"]})


def create_category(creds: Dict[str, str], title: str) -> Dict[str, Any]:
    return _put("category", creds, {"title": title, "world": {"id": creds["world_id"]}})


def create_article(creds: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build and send the article-creation payload.

    `payload` accepts: title, content, templateType, tags (str), state,
    subheading, category_id (optional), article_parent_id (optional).
    """
    body: Dict[str, Any] = {
        "title": payload["title"],
        "content": payload["content"],
        "world": {"id": creds["world_id"]},
        "templateType": payload["templateType"],
        "editor": "code",
        "state": payload.get("state", "public"),
    }
    if payload.get("tags"):
        body["tags"] = payload["tags"]
    if payload.get("subheading"):
        body["subheading"] = payload["subheading"]
    if payload.get("category_id"):
        body["category"] = {"id": payload["category_id"]}
    if payload.get("article_parent_id"):
        body["articleParent"] = {"id": payload["article_parent_id"]}
    return _put("article", creds, body)


def patch_article(creds: Dict[str, str], article_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    return _patch("article", creds, article_id, fields)


def get_article(creds: Dict[str, str], article_id: str) -> Dict[str, Any]:
    """Fetch one article's full detail (granularity 1 = principal display
    object, includes content — not just an id/title/url reference)."""
    return _get("article", creds, {"id": article_id, "granularity": 1})


def get_category_articles(creds: Dict[str, str], category_id: str) -> Dict[str, Any]:
    """Fetch one category's detail (granularity 2 = detailed object with
    linking data). Returns the raw response body; callers pull out the
    linked-articles list from whatever key the API actually uses."""
    return _get("category", creds, {"id": category_id, "granularity": 2})
