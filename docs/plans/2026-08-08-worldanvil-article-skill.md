# World Anvil Article Creator Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shareable Claude Skill package that drafts, category-resolves, entity-links, and publishes World Anvil articles via the Boromir v2 API, with nothing written to World Anvil without explicit human confirmation.

**Architecture:** A `SKILL.md` instructs Claude on decision logic (templateType pick, category resolution, entity-linking, draft-then-publish). A `scripts/` package of small `requests`-only Python CLIs (each reads a JSON payload on stdin, writes a JSON result to stdout) does all actual API I/O. A `reference/template-types.md` documents the templateType decision table. Credentials live outside the package, in `~/.worldanvil-skill/credentials.json`.

**Tech Stack:** Python 3.10+, `requests` (only runtime dependency), `pytest` (dev only), stdlib `difflib` for fuzzy matching (no extra fuzzy-match dependency).

---

## Reference: confirmed Boromir v2 API facts (from live read-only calls against the real API during design)

- Base URL: `https://www.worldanvil.com/api/external/boromir/`
- Headers on every call: `x-auth-token`, `x-application-key`, `Accept: application/json`, `User-Agent: <name> (<url>, <version>)`. Add `Content-type: application/json` on PUT/POST/PATCH.
- `GET identity` -> `{"id": "<user-uuid>", "username": "...", "success": true}`
- `POST user/worlds?id=<user_id>` body `{"limit": N, "offset": N}` -> `{"success": true, "entities": [{"id":..., "title":..., "slug":..., ...}]}`
- `POST world/categories?id=<world_id>` body `{"limit": N, "offset": N}` -> `{"success": true, "entities": [{"id":..., "title":..., ...}]}`
- `POST world/articles?id=<world_id>` body `{"limit": N, "offset": N}` -> `{"success": true, "entities": [{"id":..., "title":..., "url":..., ...}]}` (reference granularity only — no `templateType`/`content`)
- `GET article?id=<id>&granularity=2` -> full article incl. `category: {"id":..., "title":...}`, `templateType`, `editor`, `content`, `world: {"id":...}`
- `PUT article` body `{"title":..., "content":..., "world": {"id":...}, "category": {"id":...}, "templateType":..., "editor": "code", "state":..., "tags":..., "subheading":..., "articleParent": {"id":...}}` -> creates article; `isWip`/`isDraft` default to `true` regardless of `state`.
- `PATCH article?id=<id>` body `{"isWip": false, "isDraft": false}` -> flips visibility to fully public.
- `PUT category` body `{"title":..., "world": {"id":...}}` -> creates a category (same CRUD pattern as article; not live-tested to avoid polluting real data, but confirmed as the same generic CRUD shape used by `article`/`world`).
- Error responses: HTTP 401/403/404/422/500, body is JSON with `"success": false` and an `"error"` field (except plain HTTP-level failures like 401/403 which may not have a JSON body — handle both).
- Pagination: all `POST` list endpoints use `{"limit": <=50, "offset": N}` in the body and return `entities`; loop increasing `offset` by `limit` until an empty `entities` list comes back.

---

## Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`
- Create: `README.md`

- [ ] **Step 1: Create the directory structure and dependency files**

`requirements.txt`:
```
requests>=2.31
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8.0
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
```

`scripts/__init__.py`: (empty file)

`tests/__init__.py`: (empty file)

`README.md`:
```markdown
# World Anvil Article Creator — Claude Skill

A Claude Skill that drafts, formats, and publishes World Anvil articles via
the Boromir v2 API. Nothing is written to your World Anvil world without
your explicit confirmation in chat.

## Setup

1. Install Python 3.10+.
2. `pip install -r requirements.txt`
3. Get your World Anvil credentials:
   - Application key: request one at the WA API access form (see World Anvil's
     API documentation).
   - Auth token: generate one at https://www.worldanvil.com/api/auth/key
   - World ID: the skill can look this up by world name once you give it
     your application key and auth token (see `scripts/save_credentials.py`).
4. In your Claude chat, ask it to set up the World Anvil skill. It will ask
   for the application key and auth token, then store them (along with your
   resolved world ID) in `~/.worldanvil-skill/credentials.json` on your
   machine. You will not need to provide them again in future chats.

## What it does

- Drafts a World Anvil article from content already agreed in your
  conversation with Claude.
- Picks a sensible `templateType` (person, settlement, item, etc.) and shows
  you the pick before writing anything.
- Resolves which category/folder the article goes in — matching an existing
  one, or asking you to confirm creating a new one.
- Scans the draft for mentions of other things in your world and proposes
  turning them into World Anvil cross-links — again, only with your
  confirmation.
- Creates the article as a draft (visible only to you), then publishes it
  only when you explicitly say so.

## Running tests

```
pip install -r requirements-dev.txt
pytest tests/ -v
```
```

- [ ] **Step 2: Verify structure**

Run: `Get-ChildItem -Recurse -Name`
Expected: shows `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `README.md`, `scripts/__init__.py`, `tests/__init__.py`, plus the existing `docs/` tree.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore README.md scripts/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure"
```

---

## Task 2: `wa_client.py` — thin requests-only Boromir API wrapper

**Files:**
- Create: `scripts/wa_client.py`
- Test: `tests/test_wa_client.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_wa_client.py`:
```python
"""Tests for the requests-only Boromir API wrapper. No live API calls."""
from unittest.mock import patch, MagicMock

import pytest

from scripts import wa_client

CREDS = {
    "application_key": "app-key-123",
    "auth_token": "auth-token-456",
    "world_id": "world-uuid-789",
}


def _mock_response(status_code=200, json_body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    return resp


def test_headers_includes_auth_and_app_key():
    headers = wa_client.build_headers(CREDS)
    assert headers["x-auth-token"] == "auth-token-456"
    assert headers["x-application-key"] == "app-key-123"
    assert "User-Agent" in headers


@patch("scripts.wa_client.requests.get")
def test_get_identity_success(mock_get):
    mock_get.return_value = _mock_response(200, {"success": True, "id": "u1", "username": "Bob"})
    result = wa_client.get_identity(CREDS)
    assert result["id"] == "u1"
    assert result["username"] == "Bob"


@patch("scripts.wa_client.requests.get")
def test_get_identity_unauthorized_raises(mock_get):
    mock_get.return_value = _mock_response(401, {})
    with pytest.raises(wa_client.WAApiError) as exc_info:
        wa_client.get_identity(CREDS)
    assert exc_info.value.status_code == 401


@patch("scripts.wa_client.requests.post")
def test_list_user_worlds_paginates_until_empty(mock_post):
    page1 = _mock_response(200, {"success": True, "entities": [{"id": "w1", "title": "First"}]})
    page2 = _mock_response(200, {"success": True, "entities": []})
    mock_post.side_effect = [page1, page2]
    worlds = wa_client.list_user_worlds(CREDS, "u1")
    assert worlds == [{"id": "w1", "title": "First"}]
    assert mock_post.call_count == 2


@patch("scripts.wa_client.requests.post")
def test_list_categories_returns_entities(mock_post):
    mock_post.side_effect = [
        _mock_response(200, {"success": True, "entities": [{"id": "c1", "title": "Places"}]}),
        _mock_response(200, {"success": True, "entities": []}),
    ]
    categories = wa_client.list_categories(CREDS)
    assert categories == [{"id": "c1", "title": "Places"}]


@patch("scripts.wa_client.requests.put")
def test_create_category(mock_put):
    mock_put.return_value = _mock_response(200, {"success": True, "id": "c9", "title": "New Cat"})
    result = wa_client.create_category(CREDS, "New Cat")
    assert result["id"] == "c9"
    sent_json = mock_put.call_args.kwargs["json"]
    assert sent_json["title"] == "New Cat"
    assert sent_json["world"] == {"id": "world-uuid-789"}


@patch("scripts.wa_client.requests.put")
def test_create_article_sends_expected_payload(mock_put):
    mock_put.return_value = _mock_response(200, {"success": True, "id": "a1", "url": "https://x/a1"})
    payload = {
        "title": "Test Article",
        "content": "Some content",
        "templateType": "person",
        "category_id": "c1",
        "tags": "npc",
        "state": "public",
    }
    result = wa_client.create_article(CREDS, payload)
    assert result["id"] == "a1"
    sent = mock_put.call_args.kwargs["json"]
    assert sent["title"] == "Test Article"
    assert sent["editor"] == "code"
    assert sent["world"] == {"id": "world-uuid-789"}
    assert sent["category"] == {"id": "c1"}
    assert sent["templateType"] == "person"


@patch("scripts.wa_client.requests.put")
def test_create_article_raises_wa_api_error_on_422(mock_put):
    mock_put.return_value = _mock_response(422, {"success": False, "error": "Invalid templateType"})
    with pytest.raises(wa_client.WAApiError) as exc_info:
        wa_client.create_article(CREDS, {"title": "T", "content": "C", "templateType": "not-a-type"})
    assert exc_info.value.status_code == 422


@patch("scripts.wa_client.requests.patch")
def test_patch_article(mock_patch):
    mock_patch.return_value = _mock_response(200, {"success": True, "id": "a1"})
    result = wa_client.patch_article(CREDS, "a1", {"isWip": False, "isDraft": False})
    assert result["id"] == "a1"
    assert mock_patch.call_args.kwargs["params"] == {"id": "a1"}


@patch("scripts.wa_client.requests.post")
def test_list_articles_paginates(mock_post):
    mock_post.side_effect = [
        _mock_response(200, {"success": True, "entities": [{"id": "a1", "title": "Foo"}]}),
        _mock_response(200, {"success": True, "entities": []}),
    ]
    articles = wa_client.list_articles(CREDS)
    assert articles == [{"id": "a1", "title": "Foo"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_wa_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.wa_client'` (or `ImportError`).

- [ ] **Step 3: Implement `scripts/wa_client.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_wa_client.py -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/wa_client.py tests/test_wa_client.py
git commit -m "feat: add requests-only Boromir API wrapper"
```

---

## Task 3: `credentials.py` — secure local credential storage

**Files:**
- Create: `scripts/credentials.py`
- Test: `tests/test_credentials.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_credentials.py`:
```python
"""Tests for credential storage. Uses a temp HOME so the real
~/.worldanvil-skill is never touched by the test suite."""
import json
import os
import stat
import sys

import pytest

from scripts import credentials


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "CRED_DIR", tmp_path / ".worldanvil-skill")
    monkeypatch.setattr(credentials, "CRED_FILE", tmp_path / ".worldanvil-skill" / "credentials.json")
    return tmp_path


def test_load_credentials_returns_none_when_missing(temp_home):
    assert credentials.load_credentials() is None


def test_save_then_load_round_trip(temp_home):
    credentials.save_credentials("app-key", "auth-token", "world-id", world_title="Alarkdum")
    loaded = credentials.load_credentials()
    assert loaded == {
        "application_key": "app-key",
        "auth_token": "auth-token",
        "world_id": "world-id",
        "world_title": "Alarkdum",
    }


def test_save_creates_directory(temp_home):
    assert not credentials.CRED_DIR.exists()
    credentials.save_credentials("app-key", "auth-token", "world-id")
    assert credentials.CRED_DIR.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file permission bits don't apply on Windows")
def test_save_restricts_file_permissions(temp_home):
    credentials.save_credentials("app-key", "auth-token", "world-id")
    mode = stat.S_IMODE(os.stat(credentials.CRED_FILE).st_mode)
    assert mode == 0o600


def test_load_returns_none_on_corrupt_file(temp_home):
    credentials.CRED_DIR.mkdir(parents=True)
    credentials.CRED_FILE.write_text("not valid json", encoding="utf-8")
    assert credentials.load_credentials() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_credentials.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.credentials'`.

- [ ] **Step 3: Implement `scripts/credentials.py`**

```python
"""Local, per-user storage of World Anvil credentials.

Stored outside the skill package directory (in the user's home folder) so
reinstalling/updating the skill never wipes stored credentials. File
permissions are locked down to the current user where the OS supports it.
"""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

CRED_DIR = Path.home() / ".worldanvil-skill"
CRED_FILE = CRED_DIR / "credentials.json"


def _restrict_permissions(path: Path) -> None:
    if sys.platform == "win32":
        # Best-effort: restrict to the current user via icacls. Failure here
        # is non-fatal (e.g. on filesystems that don't support ACLs).
        try:
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', '')}:F"],
                capture_output=True,
                check=False,
            )
        except OSError:
            pass
    else:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def load_credentials() -> Optional[Dict[str, str]]:
    if not CRED_FILE.exists():
        return None
    try:
        with open(CRED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_credentials(
    application_key: str,
    auth_token: str,
    world_id: str,
    world_title: Optional[str] = None,
) -> None:
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "application_key": application_key,
        "auth_token": auth_token,
        "world_id": world_id,
    }
    if world_title:
        data["world_title"] = world_title
    with open(CRED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    _restrict_permissions(CRED_FILE)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_credentials.py -v`
Expected: PASS (5 tests; on Windows the permission test is skipped, so 4 pass + 1 skipped).

- [ ] **Step 5: Commit**

```bash
git add scripts/credentials.py tests/test_credentials.py
git commit -m "feat: add local credential storage with restricted permissions"
```

---

## Task 4: `matching.py` — shared fuzzy-match helper

**Files:**
- Create: `scripts/matching.py`
- Test: `tests/test_matching.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_matching.py`:
```python
"""Tests for the shared fuzzy-match helper used by category resolution and
entity-linking search."""
from scripts.matching import find_best_match


def test_exact_match_case_insensitive():
    candidates = [{"id": "1", "title": "Characters"}, {"id": "2", "title": "Places"}]
    result = find_best_match("characters", candidates, key="title")
    assert result is not None
    assert result["id"] == "1"


def test_close_match_typo():
    candidates = [{"id": "1", "title": "Adventuring Guild"}, {"id": "2", "title": "Places"}]
    result = find_best_match("Adventuring Gild", candidates, key="title")
    assert result is not None
    assert result["id"] == "1"


def test_no_match_returns_none():
    candidates = [{"id": "1", "title": "Characters"}, {"id": "2", "title": "Places"}]
    result = find_best_match("Completely Unrelated Thing", candidates, key="title")
    assert result is None


def test_empty_candidates_returns_none():
    assert find_best_match("Anything", [], key="title") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_matching.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.matching'`.

- [ ] **Step 3: Implement `scripts/matching.py`**

```python
"""Fuzzy-match helper shared by category resolution and entity-linking
search. Uses stdlib difflib only — no extra dependency."""
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

CLOSE_MATCH_CUTOFF = 0.75


def find_best_match(query: str, candidates: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    """Return the candidate dict whose `key` field best matches `query`.

    Tries an exact case-insensitive match first, then falls back to the
    closest fuzzy match above CLOSE_MATCH_CUTOFF. Returns None if nothing
    clears the bar (caller must then ask the user rather than guessing).
    """
    if not candidates:
        return None

    query_lower = query.strip().lower()
    for candidate in candidates:
        if str(candidate.get(key, "")).strip().lower() == query_lower:
            return candidate

    best_candidate = None
    best_ratio = 0.0
    for candidate in candidates:
        value = str(candidate.get(key, "")).strip().lower()
        ratio = SequenceMatcher(None, query_lower, value).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = candidate

    if best_ratio >= CLOSE_MATCH_CUTOFF:
        return best_candidate
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_matching.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/matching.py tests/test_matching.py
git commit -m "feat: add shared fuzzy-match helper"
```

---

## Task 5: `save_credentials.py` CLI

**Files:**
- Create: `scripts/save_credentials.py`
- Test: `tests/test_save_credentials.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_save_credentials.py`:
```python
"""Tests for the save_credentials CLI's resolution logic (world lookup by
name). No live API calls: wa_client functions are monkeypatched."""
from unittest.mock import patch

from scripts import save_credentials


@patch("scripts.save_credentials.credentials.save_credentials")
@patch("scripts.save_credentials.wa_client.list_user_worlds")
@patch("scripts.save_credentials.wa_client.get_identity")
def test_resolve_by_world_name_success(mock_identity, mock_worlds, mock_save):
    mock_identity.return_value = {"id": "u1", "username": "Bob"}
    mock_worlds.return_value = [
        {"id": "w1", "title": "Alarkdum"},
        {"id": "w2", "title": "Other World"},
    ]
    result = save_credentials.resolve_and_save(
        application_key="app", auth_token="tok", world_name="Alarkdum"
    )
    assert result["success"] is True
    assert result["world_id"] == "w1"
    mock_save.assert_called_once_with("app", "tok", "w1", world_title="Alarkdum")


@patch("scripts.save_credentials.wa_client.list_user_worlds")
@patch("scripts.save_credentials.wa_client.get_identity")
def test_resolve_by_world_name_no_match(mock_identity, mock_worlds):
    mock_identity.return_value = {"id": "u1", "username": "Bob"}
    mock_worlds.return_value = [{"id": "w1", "title": "Alarkdum"}]
    result = save_credentials.resolve_and_save(
        application_key="app", auth_token="tok", world_name="Nonexistent"
    )
    assert result["success"] is False
    assert "available_worlds" in result


@patch("scripts.save_credentials.credentials.save_credentials")
@patch("scripts.save_credentials.wa_client.get_identity")
def test_resolve_by_world_id_skips_lookup(mock_identity, mock_save):
    mock_identity.return_value = {"id": "u1", "username": "Bob"}
    result = save_credentials.resolve_and_save(
        application_key="app", auth_token="tok", world_id="w1"
    )
    assert result["success"] is True
    assert result["world_id"] == "w1"
    mock_save.assert_called_once_with("app", "tok", "w1", world_title=None)


@patch("scripts.save_credentials.wa_client.get_identity")
def test_invalid_credentials_reports_error(mock_identity):
    from scripts.wa_client import WAApiError

    mock_identity.side_effect = WAApiError(401, "Unauthorized")
    result = save_credentials.resolve_and_save(
        application_key="bad", auth_token="bad", world_id="w1"
    )
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_save_credentials.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.save_credentials'`.

- [ ] **Step 3: Implement `scripts/save_credentials.py`**

```python
"""CLI: validate World Anvil credentials and store them locally.

Reads a JSON payload from stdin:
    {"application_key": "...", "auth_token": "...", "world_id": "..."}
or, to resolve a world by name instead of by raw UUID:
    {"application_key": "...", "auth_token": "...", "world_name": "..."}

Writes a JSON result to stdout:
    {"success": true, "world_id": "...", "world_title": "..."}
or on failure:
    {"success": false, "error": "...", "available_worlds": [...]}  (if relevant)
"""
import json
import sys
from typing import Any, Dict, Optional

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def resolve_and_save(
    application_key: str,
    auth_token: str,
    world_id: Optional[str] = None,
    world_name: Optional[str] = None,
) -> Dict[str, Any]:
    creds = {"application_key": application_key, "auth_token": auth_token, "world_id": world_id or ""}
    try:
        identity = wa_client.get_identity(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    resolved_world_id = world_id
    resolved_world_title = None

    if not resolved_world_id:
        try:
            worlds = wa_client.list_user_worlds(creds, identity["id"])
        except wa_client.WAApiError as exc:
            return {"success": False, "error": str(exc)}
        match = find_best_match(world_name or "", worlds, key="title")
        if match is None:
            return {
                "success": False,
                "error": f"No world matching '{world_name}' found for this account.",
                "available_worlds": [w["title"] for w in worlds],
            }
        resolved_world_id = match["id"]
        resolved_world_title = match["title"]

    credentials.save_credentials(
        application_key, auth_token, resolved_world_id, world_title=resolved_world_title
    )
    return {"success": True, "world_id": resolved_world_id, "world_title": resolved_world_title}


def main() -> None:
    payload = json.load(sys.stdin)
    result = resolve_and_save(
        application_key=payload["application_key"],
        auth_token=payload["auth_token"],
        world_id=payload.get("world_id"),
        world_name=payload.get("world_name"),
    )
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_save_credentials.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/save_credentials.py tests/test_save_credentials.py
git commit -m "feat: add save_credentials CLI with world name resolution"
```

---

## Task 6: `list_categories.py` CLI

**Files:**
- Create: `scripts/list_categories.py`
- Test: `tests/test_list_categories.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_list_categories.py`:
```python
"""Tests for the list_categories CLI's matching behavior."""
from unittest.mock import patch

from scripts import list_categories

FAKE_CATEGORIES = [
    {"id": "c1", "title": "Characters"},
    {"id": "c2", "title": "Places"},
]


@patch("scripts.list_categories.wa_client.list_categories")
@patch("scripts.list_categories.credentials.load_credentials")
def test_target_matches_existing_category(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_categories.resolve_category(target="characters")
    assert result["success"] is True
    assert result["match"] == {"id": "c1", "title": "Characters"}
    assert result["categories"] == FAKE_CATEGORIES


@patch("scripts.list_categories.wa_client.list_categories")
@patch("scripts.list_categories.credentials.load_credentials")
def test_target_with_no_match(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_categories.resolve_category(target="Completely New Folder")
    assert result["success"] is True
    assert result["match"] is None
    assert result["categories"] == FAKE_CATEGORIES


@patch("scripts.list_categories.credentials.load_credentials")
def test_no_credentials_reports_error(mock_load_creds):
    mock_load_creds.return_value = None
    result = list_categories.resolve_category(target="Characters")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.list_categories.wa_client.list_categories")
@patch("scripts.list_categories.credentials.load_credentials")
def test_no_target_lists_all(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_categories.resolve_category(target=None)
    assert result["success"] is True
    assert result["match"] is None
    assert result["categories"] == FAKE_CATEGORIES
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_list_categories.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.list_categories'`.

- [ ] **Step 3: Implement `scripts/list_categories.py`**

```python
"""CLI: fetch existing categories for the configured world and, if a target
name is given, find the best matching existing category.

Reads a JSON payload from stdin: {"target": "Characters"} (target optional).
Writes a JSON result to stdout:
    {"success": true, "categories": [...], "match": {...} or null}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict, Optional

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def resolve_category(target: Optional[str]) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        categories = wa_client.list_categories(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    match = find_best_match(target, categories, key="title") if target else None
    return {"success": True, "categories": categories, "match": match}


def main() -> None:
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    result = resolve_category(target=payload.get("target"))
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_list_categories.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/list_categories.py tests/test_list_categories.py
git commit -m "feat: add list_categories CLI with fuzzy category resolution"
```

---

## Task 7: `create_category.py` CLI

**Files:**
- Create: `scripts/create_category.py`
- Test: `tests/test_create_category.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_create_category.py`:
```python
"""Tests for the create_category CLI."""
from unittest.mock import patch

from scripts import create_category


@patch("scripts.create_category.wa_client.create_category")
@patch("scripts.create_category.credentials.load_credentials")
def test_create_category_success(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.return_value = {"id": "c9", "title": "New Category"}
    result = create_category.create(title="New Category")
    assert result["success"] is True
    assert result["id"] == "c9"


@patch("scripts.create_category.credentials.load_credentials")
def test_create_category_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = create_category.create(title="New Category")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.create_category.wa_client.create_category")
@patch("scripts.create_category.credentials.load_credentials")
def test_create_category_api_error(mock_load_creds, mock_create):
    from scripts.wa_client import WAApiError

    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.side_effect = WAApiError(500, "Server error")
    result = create_category.create(title="New Category")
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_create_category.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.create_category'`.

- [ ] **Step 3: Implement `scripts/create_category.py`**

```python
"""CLI: create a new World Anvil category. Only ever invoked after the user
has explicitly confirmed creating a new category (SKILL.md enforces this;
this script performs no confirmation itself, it only executes).

Reads a JSON payload from stdin: {"title": "New Category"}
Writes a JSON result to stdout:
    {"success": true, "id": "...", "title": "..."}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict

from scripts import credentials, wa_client


def create(title: str) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        created = wa_client.create_category(creds, title)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "id": created["id"], "title": created.get("title", title)}


def main() -> None:
    payload = json.load(sys.stdin)
    result = create(title=payload["title"])
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_create_category.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/create_category.py tests/test_create_category.py
git commit -m "feat: add create_category CLI"
```

---

## Task 8: `search_entities.py` CLI

**Files:**
- Create: `scripts/search_entities.py`
- Test: `tests/test_search_entities.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_search_entities.py`:
```python
"""Tests for the search_entities CLI (entity-linking lookup)."""
from unittest.mock import patch

from scripts import search_entities

FAKE_ARTICLES = [
    {"id": "a1", "title": "Ármen", "url": "https://x/a1"},
    {"id": "a2", "title": "Velz", "url": "https://x/a2"},
    {"id": "a3", "title": "Dead Gods", "url": "https://x/a3"},
]


@patch("scripts.search_entities.wa_client.list_articles")
@patch("scripts.search_entities.credentials.load_credentials")
def test_search_finds_matches_and_reports_unmatched(mock_load_creds, mock_list_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_ARTICLES
    result = search_entities.search(names=["Ármen", "Some Unrelated Name"])
    assert result["success"] is True
    assert result["matches"]["Ármen"] == {"id": "a1", "title": "Ármen", "url": "https://x/a1"}
    assert result["matches"]["Some Unrelated Name"] is None


@patch("scripts.search_entities.credentials.load_credentials")
def test_search_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = search_entities.search(names=["Anything"])
    assert result["success"] is False
    assert "error" in result


@patch("scripts.search_entities.wa_client.list_articles")
@patch("scripts.search_entities.credentials.load_credentials")
def test_search_empty_names_returns_empty_matches(mock_load_creds, mock_list_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_ARTICLES
    result = search_entities.search(names=[])
    assert result["success"] is True
    assert result["matches"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_search_entities.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.search_entities'`.

- [ ] **Step 3: Implement `scripts/search_entities.py`**

```python
"""CLI: search the world's existing articles for candidate entity mentions
(for the entity-linking pass). Claude supplies the candidate names it found
in its own draft; this script only looks them up, it never decides on its
own what counts as a mention.

Reads a JSON payload from stdin: {"names": ["Ármen", "Velz"]}
Writes a JSON result to stdout:
    {"success": true, "matches": {"Ármen": {"id":..., "title":..., "url":...} or null, ...}}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict, List

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def search(names: List[str]) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        articles = wa_client.list_articles(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    matches: Dict[str, Any] = {}
    for name in names:
        match = find_best_match(name, articles, key="title")
        matches[name] = (
            {"id": match["id"], "title": match["title"], "url": match.get("url")} if match else None
        )

    return {"success": True, "matches": matches}


def main() -> None:
    payload = json.load(sys.stdin)
    result = search(names=payload.get("names", []))
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_search_entities.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/search_entities.py tests/test_search_entities.py
git commit -m "feat: add search_entities CLI for entity-linking lookups"
```

---

## Task 9: `create_article.py` CLI (with 422 templateType fallback)

**Files:**
- Create: `scripts/create_article.py`
- Test: `tests/test_create_article.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_create_article.py`:
```python
"""Tests for the create_article CLI, including the 422 templateType
fallback behavior."""
from unittest.mock import patch

from scripts import create_article
from scripts.wa_client import WAApiError

BASE_PAYLOAD = {
    "title": "Test Article",
    "content": "Some content",
    "templateType": "person",
    "state": "public",
}


@patch("scripts.create_article.wa_client.create_article")
@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_success(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.return_value = {"id": "art1", "url": "https://x/art1"}
    result = create_article.create(BASE_PAYLOAD)
    assert result["success"] is True
    assert result["id"] == "art1"
    assert result["fallback_used"] is False
    assert mock_create.call_count == 1


@patch("scripts.create_article.wa_client.create_article")
@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_falls_back_to_generic_on_422(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.side_effect = [
        WAApiError(422, "Invalid templateType"),
        {"id": "art1", "url": "https://x/art1"},
    ]
    result = create_article.create({**BASE_PAYLOAD, "templateType": "not-a-real-type"})
    assert result["success"] is True
    assert result["fallback_used"] is True
    assert result["templateType_used"] == "article"
    assert mock_create.call_count == 2
    second_call_payload = mock_create.call_args_list[1].args[1]
    assert second_call_payload["templateType"] == "article"


@patch("scripts.create_article.wa_client.create_article")
@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_non_422_error_does_not_retry(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.side_effect = WAApiError(500, "Server error")
    result = create_article.create(BASE_PAYLOAD)
    assert result["success"] is False
    assert "error" in result
    assert mock_create.call_count == 1


@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = create_article.create(BASE_PAYLOAD)
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_create_article.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.create_article'`.

- [ ] **Step 3: Implement `scripts/create_article.py`**

```python
"""CLI: create a World Anvil article as a draft (isWip/isDraft remain true
by World Anvil's own default on creation — that is the "draft" mechanism
this skill relies on; see publish_article.py to flip it public).

If the API rejects the chosen templateType (HTTP 422), retries exactly once
with the generic "article" templateType and reports that a fallback
happened — never silently, never in a loop.

Reads a JSON payload from stdin:
    {"title":..., "content":..., "templateType":..., "state":"public",
     "tags":"...", "subheading":"...", "category_id":"...",
     "article_parent_id":"..."}
Writes a JSON result to stdout:
    {"success": true, "id":..., "url":..., "templateType_used":...,
     "fallback_used": bool}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict

from scripts import credentials, wa_client

GENERIC_TEMPLATE_TYPE = "article"


def create(payload: Dict[str, Any]) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    fallback_used = False
    template_type = payload.get("templateType", GENERIC_TEMPLATE_TYPE)

    try:
        created = wa_client.create_article(creds, payload)
    except wa_client.WAApiError as exc:
        if exc.status_code != 422 or template_type == GENERIC_TEMPLATE_TYPE:
            return {"success": False, "error": str(exc)}
        fallback_used = True
        template_type = GENERIC_TEMPLATE_TYPE
        fallback_payload = {**payload, "templateType": GENERIC_TEMPLATE_TYPE}
        try:
            created = wa_client.create_article(creds, fallback_payload)
        except wa_client.WAApiError as retry_exc:
            return {"success": False, "error": str(retry_exc)}

    return {
        "success": True,
        "id": created["id"],
        "url": created.get("url"),
        "templateType_used": template_type,
        "fallback_used": fallback_used,
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = create(payload)
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_create_article.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/create_article.py tests/test_create_article.py
git commit -m "feat: add create_article CLI with 422 templateType fallback"
```

---

## Task 10: `publish_article.py` CLI

**Files:**
- Create: `scripts/publish_article.py`
- Test: `tests/test_publish_article.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_publish_article.py`:
```python
"""Tests for the publish_article CLI."""
from unittest.mock import patch

from scripts import publish_article


@patch("scripts.publish_article.wa_client.patch_article")
@patch("scripts.publish_article.credentials.load_credentials")
def test_publish_success(mock_load_creds, mock_patch):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_patch.return_value = {"id": "art1", "url": "https://x/art1"}
    result = publish_article.publish(article_id="art1")
    assert result["success"] is True
    assert result["url"] == "https://x/art1"
    mock_patch.assert_called_once_with(
        {"application_key": "a", "auth_token": "t", "world_id": "w"},
        "art1",
        {"isWip": False, "isDraft": False},
    )


@patch("scripts.publish_article.credentials.load_credentials")
def test_publish_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = publish_article.publish(article_id="art1")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.publish_article.wa_client.patch_article")
@patch("scripts.publish_article.credentials.load_credentials")
def test_publish_api_error(mock_load_creds, mock_patch):
    from scripts.wa_client import WAApiError

    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_patch.side_effect = WAApiError(404, "Not found")
    result = publish_article.publish(article_id="does-not-exist")
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_publish_article.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.publish_article'`.

- [ ] **Step 3: Implement `scripts/publish_article.py`**

```python
"""CLI: flip an existing draft article to fully public. Only ever invoked
after the user has explicitly said to publish (SKILL.md enforces this; this
script performs no confirmation itself, it only executes).

Reads a JSON payload from stdin: {"article_id": "..."}
Writes a JSON result to stdout:
    {"success": true, "id": "...", "url": "..."}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict

from scripts import credentials, wa_client


def publish(article_id: str) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        result = wa_client.patch_article(creds, article_id, {"isWip": False, "isDraft": False})
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "id": result.get("id", article_id), "url": result.get("url")}


def main() -> None:
    payload = json.load(sys.stdin)
    result = publish(article_id=payload["article_id"])
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_publish_article.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/publish_article.py tests/test_publish_article.py
git commit -m "feat: add publish_article CLI"
```

---

## Task 11: `reference/template-types.md`

**Files:**
- Create: `reference/template-types.md`

- [ ] **Step 1: Write the reference document**

`reference/template-types.md`:
```markdown
# World Anvil `templateType` decision table

Grounded in real values already in production use across 219 articles in an
existing World Anvil world: `person` (109), `report` (91), `landmark` (19),
`plot` (19), `organization` (17), `article`/generic (15), `settlement` (13),
`location` (11), `item` (5), `species` (2), `myth` (1), `ritual` (1), `law`
(1).

## Decision table

| Article is about...                                   | `templateType`  |
|--------------------------------------------------------|-----------------|
| A person — NPC, PC, historical figure                  | `person`        |
| A town, city, or other named settlement                | `settlement`    |
| A smaller notable landmark (a single building, ruin,    | `landmark`      |
| monument, geographic feature)                           |                 |
| A general place without more specific shape             | `location`      |
| A guild, kingdom, army, faction, or other group          | `organization`  |
| A physical object (weapon, artifact, tool)               | `item`          |
| A monster, race, or creature type (not a single NPC)     | `species`       |
| A deity, creation myth, piece of folklore                | `myth`          |
| A ceremony or rite                                       | `ritual`        |
| An in-world legal rule, decree, or law                   | `law`           |
| A session summary / recap                                | `report`        |
| An overarching storyline or quest thread                 | `plot`          |
| Anything that doesn't clearly fit the above                | `article` (generic) |

World Anvil supports additional official template types beyond this
observed set — for example `condition`, `document`, `ethnicity`, `event`,
`family`, `formation`, `language`, `material`, `military-conflict`,
`natural-law`, `profession`, `prose`, `rank`, `religion`, `technology`,
`title`, `vehicle`, `vocabulary`, `diplomacy`. These may be picked when
clearly applicable, but always fall through the fallback rule below if the
API rejects them.

## Fallback rule

If `create_article.py` receives an HTTP 422 for the chosen `templateType`,
it retries exactly once with the generic `"article"` templateType, and
reports (`fallback_used: true`) that this happened. It never retries more
than once, and never fails silently — the calling conversation must tell
the user this happened.

## Content format

Articles are created with `editor: "code"`, meaning `content` is plain
Markdown, not World Anvil's structured per-type field forms. This matches
this ecosystem's established convention (see the sibling Alarkdum/Obsidian
exporter project) of keeping everything in the free-text `content` field
rather than the WA UI's structured fields (population, motto, etc.).
```

- [ ] **Step 2: Verify the file**

Run: `Get-Content reference/template-types.md | Select-Object -First 5`
Expected: shows the file's title/intro lines.

- [ ] **Step 3: Commit**

```bash
git add reference/template-types.md
git commit -m "docs: add templateType decision reference"
```

---

## Task 12: `SKILL.md`

**Files:**
- Create: `SKILL.md`

- [ ] **Step 1: Write the skill instructions**

`SKILL.md`:
```markdown
---
name: worldanvil-article-creator
description: Use when the user has agreed on an idea for a new World Anvil article and wants it drafted, formatted, and published to their World Anvil world via the Boromir API.
---

# World Anvil Article Creator

Turns an article idea already agreed in conversation into a properly
formatted World Anvil article and publishes it. Creation only — this skill
does not edit or delete existing articles.

**Golden rule: this is the user's world. Nothing gets written to World**
**Anvil — no category, no article, no link, no publish — without the**
**user explicitly confirming that specific action in this conversation.**

## 0. Credentials check

Run `python scripts/save_credentials.py` is not how this works — credentials
are checked implicitly by every other script (`credentials.load_credentials()`
returns `None` if unset). Before drafting anything:

1. Try calling `python scripts/list_categories.py` (empty stdin `{}`) as a
   cheap probe.
2. If the result has `"success": false` with an error about missing
   credentials, ask the user for:
   - Their World Anvil **application key**
   - Their World Anvil **auth token** (from https://www.worldanvil.com/api/auth/key)
   - Their **world name** (preferred) or raw world ID/UUID
3. Call `scripts/save_credentials.py` with that payload on stdin:
   ```json
   {"application_key": "...", "auth_token": "...", "world_name": "..."}
   ```
4. If it returns `"success": false` with `available_worlds`, show that list
   to the user and ask them to pick the correct one, then retry with
   `world_name` set to the exact title (or pass `world_id` directly).
5. Once successful, credentials are stored in `~/.worldanvil-skill/` and this
   step is skipped in all future conversations.

## 1. Pick a `templateType`

Read `reference/template-types.md` and pick the best-fitting `templateType`
for the drafted article. State your pick and a one-line reason as part of
step 4's confirmation — never apply it silently.

## 2. Resolve the category/folder

Ask the user which category/folder the article belongs in if they haven't
already said. Then:

1. Call `scripts/list_categories.py` with `{"target": "<what the user said>"}`.
2. If `match` is non-null: use it, but still show which existing category
   was picked in the final confirmation (step 4).
3. If `match` is null: **stop and ask** — "No existing category matches
   '<X>'. Create a new category called '<X>'?" Only call
   `scripts/create_category.py` if the user explicitly says yes. Never
   create a category on your own initiative.

## 3. Entity-linking pass

Read through the drafted content yourself and list every proper-noun
mention that plausibly refers to another thing in the user's world (a
person, place, item, faction, event, etc. — you are doing the reading, not
a script).

1. Call `scripts/search_entities.py` with `{"names": [<your list>]}`.
2. For every name with a non-null match, propose converting that mention to
   `@[Display](type:uuid)` form (using the matched `id`) — but do not apply
   it yet.
3. For every name with `null`, ask the user: leave it as plain text, or flag
   it as a candidate for a separate, explicitly-confirmed stub article
   (creating a stub article is out of scope for this skill's automatic
   flow — if the user wants one, that's a distinct, separately-confirmed
   article-creation pass through this same skill, not an automatic action).
4. Only apply the link conversions the user actually confirms.

## 4. Final confirmation (mandatory, before any write)

Show the user the fully assembled article:
- Title
- `templateType` (+ why)
- Category (existing, or "will create new: X")
- Tags
- Full content, with any confirmed `@[Display](type:uuid)` links applied

Wait for explicit go-ahead before proceeding to step 5.

## 5. Create as a draft

Call `scripts/create_article.py` with a JSON payload on stdin:
```json
{
  "title": "...",
  "content": "...",
  "templateType": "...",
  "state": "public",
  "tags": "comma,separated,tags",
  "category_id": "<id from step 2, if any>"
}
```

Report the returned `url` to the user, and mention it is only visible to
them while in draft/WIP state. If `fallback_used` is `true`, tell the user
the templateType was changed to generic `article` because World Anvil
rejected the original pick.

## 6. Publish — only when explicitly requested

Do not do this as part of the same turn as step 5 unless the user has
already said, in the same request, that they want it published immediately.
Otherwise, wait for the user to separately say to publish it. Then call
`scripts/publish_article.py` with `{"article_id": "<id from step 5>"}` and
confirm the article is now public with its URL.

## Script invocation notes

All scripts read a JSON payload from stdin and write a JSON result to
stdout — pipe the JSON in, e.g. (bash):
```bash
echo '{"target": "Characters"}' | python scripts/list_categories.py
```
Always check the `"success"` field in the result before proceeding; on
`false`, surface the `"error"` to the user rather than retrying blindly.
```

- [ ] **Step 2: Verify the file**

Run: `Get-Content SKILL.md | Select-Object -First 10`
Expected: shows the frontmatter and title.

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs: add SKILL.md workflow instructions"
```

---

## Task 13: Full test suite run and final verification

**Files:** none (verification only)

- [ ] **Step 1: Install dev dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: installs/confirms `requests` and `pytest`.

- [ ] **Step 2: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS — all tests across `test_wa_client.py`, `test_credentials.py`,
`test_matching.py`, `test_save_credentials.py`, `test_list_categories.py`,
`test_create_category.py`, `test_search_entities.py`,
`test_create_article.py`, `test_publish_article.py` (37 tests total, 1
skipped on Windows for the POSIX-only permission test).

- [ ] **Step 3: Confirm no live credentials or secrets are committed**

Run: `git log --all -p -- '*credentials*' | Select-String -Pattern "auth_token|application_key" -Context 0,0`
Expected: no output (the tests never write real credentials into the repo;
`~/.worldanvil-skill/` is outside the project directory entirely).

- [ ] **Step 4: Final commit if anything is outstanding**

```bash
git status
```
Expected: working tree clean (everything already committed task-by-task
above). If not, stage and commit remaining files with an appropriate
message.
```
