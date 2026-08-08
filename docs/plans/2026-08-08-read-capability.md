# Read Capability for Categories & Articles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only capability to fetch a category's article stubs and a single article's full content, so Claude can gather existing-lore context before drafting new articles.

**Architecture:** Two new `wa_client.py` functions (`get_article`, `get_category_articles`) wrapping `GET article?id=X&granularity=1` and `GET category?id=X&granularity=2`; two new CLI scripts (`list_category_articles.py`, `get_article.py`) following the exact stdin-JSON-in/stdout-JSON-out pattern already used by every other script in `scripts/`.

**Tech Stack:** Python 3.12, `requests`, `pytest` (mocked, no live API calls) — same as the rest of the repo. No new dependencies.

**Spec:** `docs/specs/2026-08-08-read-capability-design.md`

---

## Task 1: `wa_client.py` — `get_article` and `get_category_articles`

**Files:**
- Modify: `scripts/wa_client.py`
- Test: `tests/test_wa_client.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_wa_client.py`:

```python
@patch("scripts.wa_client.requests.get")
def test_get_article_returns_body(mock_get):
    mock_get.return_value = _mock_response(200, {
        "success": True, "id": "a1", "title": "Session 12 Recap",
        "content": "Full markdown body", "templateType": "report",
    })
    result = wa_client.get_article(CREDS, "a1")
    assert result["id"] == "a1"
    assert result["content"] == "Full markdown body"
    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params == {"id": "a1", "granularity": 1}


@patch("scripts.wa_client.requests.get")
def test_get_article_not_found_raises(mock_get):
    mock_get.return_value = _mock_response(404, {"success": False, "error": "Not found"})
    with pytest.raises(wa_client.WAApiError) as exc_info:
        wa_client.get_article(CREDS, "does-not-exist")
    assert exc_info.value.status_code == 404


@patch("scripts.wa_client.requests.get")
def test_get_category_articles_returns_body(mock_get):
    mock_get.return_value = _mock_response(200, {
        "success": True, "id": "c1", "title": "NPCs",
        "articles": [{"id": "a1", "title": "Ármen", "url": "https://x/a1"}],
    })
    result = wa_client.get_category_articles(CREDS, "c1")
    assert result["articles"] == [{"id": "a1", "title": "Ármen", "url": "https://x/a1"}]
    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params == {"id": "c1", "granularity": 2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_wa_client.py -k "get_article or get_category_articles" -v`
Expected: FAIL with `AttributeError: module 'scripts.wa_client' has no attribute 'get_article'` (and same for `get_category_articles`).

- [ ] **Step 3: Implement the two functions**

In `scripts/wa_client.py`, add after the existing `patch_article` function (end of file):

```python
def get_article(creds: Dict[str, str], article_id: str) -> Dict[str, Any]:
    """Fetch one article's full detail (granularity 1 = principal display
    object, includes content — not just an id/title/url reference)."""
    return _get("article", creds, {"id": article_id, "granularity": 1})


def get_category_articles(creds: Dict[str, str], category_id: str) -> Dict[str, Any]:
    """Fetch one category's detail (granularity 2 = detailed object with
    linking data). Returns the raw response body; callers pull out the
    linked-articles list from whatever key the API actually uses."""
    return _get("category", creds, {"id": category_id, "granularity": 2})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_wa_client.py -v`
Expected: all tests PASS (existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/wa_client.py tests/test_wa_client.py
git commit -m "feat: add get_article and get_category_articles to wa_client"
```

---

## Task 2: `scripts/list_category_articles.py` — stub-list articles in a category

**Files:**
- Create: `scripts/list_category_articles.py`
- Test: `tests/test_list_category_articles.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_list_category_articles.py`:

```python
"""Tests for the list_category_articles CLI."""
from unittest.mock import patch

from scripts import list_category_articles

FAKE_CATEGORIES = [
    {"id": "c1", "title": "NPCs"},
    {"id": "c2", "title": "Places"},
]

FAKE_CATEGORY_DETAIL = {
    "id": "c1",
    "title": "NPCs",
    "articles": [
        {"id": "a1", "title": "Ármen", "url": "https://x/a1"},
        {"id": "a2", "title": "Velz", "url": "https://x/a2"},
    ],
}


@patch("scripts.list_category_articles.wa_client.get_category_articles")
@patch("scripts.list_category_articles.wa_client.list_categories")
@patch("scripts.list_category_articles.credentials.load_credentials")
def test_category_match_returns_stub_list(mock_load_creds, mock_list_cats, mock_get_cat_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    mock_get_cat_articles.return_value = FAKE_CATEGORY_DETAIL
    result = list_category_articles.resolve(category_target="npcs")
    assert result["success"] is True
    assert result["category"] == {"id": "c1", "title": "NPCs"}
    assert result["articles"] == [
        {"id": "a1", "title": "Ármen", "url": "https://x/a1"},
        {"id": "a2", "title": "Velz", "url": "https://x/a2"},
    ]


@patch("scripts.list_category_articles.wa_client.list_categories")
@patch("scripts.list_category_articles.credentials.load_credentials")
def test_no_category_match(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_category_articles.resolve(category_target="Completely Unrelated")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.list_category_articles.wa_client.get_category_articles")
@patch("scripts.list_category_articles.wa_client.list_categories")
@patch("scripts.list_category_articles.credentials.load_credentials")
def test_unexpected_response_shape_returns_raw(mock_load_creds, mock_list_cats, mock_get_cat_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    mock_get_cat_articles.return_value = {"id": "c1", "title": "NPCs"}  # no "articles" key
    result = list_category_articles.resolve(category_target="NPCs")
    assert result["success"] is False
    assert result["error"] == "unexpected response shape"
    assert result["raw"] == {"id": "c1", "title": "NPCs"}


@patch("scripts.list_category_articles.credentials.load_credentials")
def test_no_credentials_reports_error(mock_load_creds):
    mock_load_creds.return_value = None
    result = list_category_articles.resolve(category_target="NPCs")
    assert result["success"] is False
    assert "error" in result


def test_missing_category_target_reports_error():
    result = list_category_articles.resolve(category_target=None)
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_list_category_articles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.list_category_articles'`.

- [ ] **Step 3: Implement the script**

Create `scripts/list_category_articles.py`:

```python
"""CLI: fuzzy-match a category by name, then return the stub list (id,
title, url) of every article inside it. Read-only — use get_article.py to
fetch full content once the right article is identified.

Reads a JSON payload from stdin: {"category": "NPCs"}
Writes a JSON result to stdout:
    {"success": true, "category": {...}, "articles": [{"id","title","url"}, ...]}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict, Optional

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def resolve(category_target: Optional[str]) -> Dict[str, Any]:
    if not category_target:
        return {"success": False, "error": "'category' is required."}

    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        categories = wa_client.list_categories(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    match = find_best_match(category_target, categories, key="title")
    if match is None:
        return {"success": False, "error": f"No category matches '{category_target}'."}

    try:
        detail = wa_client.get_category_articles(creds, match["id"])
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    articles = detail.get("articles")
    if not isinstance(articles, list):
        return {"success": False, "error": "unexpected response shape", "raw": detail}

    stubs = [
        {"id": a.get("id"), "title": a.get("title"), "url": a.get("url")}
        for a in articles
    ]
    return {
        "success": True,
        "category": {"id": match["id"], "title": match["title"]},
        "articles": stubs,
    }


def main() -> None:
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    result = resolve(category_target=payload.get("category"))
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_list_category_articles.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/list_category_articles.py tests/test_list_category_articles.py
git commit -m "feat: add list_category_articles CLI"
```

---

## Task 3: `scripts/get_article.py` — fetch one article's full content

**Files:**
- Create: `scripts/get_article.py`
- Test: `tests/test_get_article.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_get_article.py`:

```python
"""Tests for the get_article CLI."""
from unittest.mock import patch

from scripts import get_article

FAKE_ARTICLE = {
    "id": "a1",
    "title": "Session 12 Recap",
    "content": "Full markdown body",
    "templateType": "report",
    "tags": "recap,session12",
    "category": {"id": "c1", "title": "Recaps"},
    "url": "https://x/a1",
}

FAKE_WORLD_ARTICLES = [
    {"id": "a1", "title": "Session 12 Recap", "url": "https://x/a1"},
    {"id": "a2", "title": "Session 11 Recap", "url": "https://x/a2"},
]


@patch("scripts.get_article.wa_client.get_article")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_id(mock_load_creds, mock_get_article):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_get_article.return_value = FAKE_ARTICLE
    result = get_article.fetch({"id": "a1"})
    assert result["success"] is True
    assert result["content"] == "Full markdown body"
    mock_get_article.assert_called_once_with(
        {"application_key": "a", "auth_token": "t", "world_id": "w"}, "a1"
    )


@patch("scripts.get_article.wa_client.get_article")
@patch("scripts.get_article.wa_client.list_articles")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_title_worldwide(mock_load_creds, mock_list_articles, mock_get_article):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_WORLD_ARTICLES
    mock_get_article.return_value = FAKE_ARTICLE
    result = get_article.fetch({"title": "Session 12 Recap"})
    assert result["success"] is True
    assert result["id"] == "a1"
    mock_get_article.assert_called_once_with(
        {"application_key": "a", "auth_token": "t", "world_id": "w"}, "a1"
    )


@patch("scripts.get_article.wa_client.get_article")
@patch("scripts.get_article.list_category_articles.resolve")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_title_scoped_to_category(mock_load_creds, mock_resolve, mock_get_article):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_resolve.return_value = {
        "success": True,
        "category": {"id": "c1", "title": "Recaps"},
        "articles": FAKE_WORLD_ARTICLES,
    }
    mock_get_article.return_value = FAKE_ARTICLE
    result = get_article.fetch({"title": "Session 12 Recap", "category": "Recaps"})
    assert result["success"] is True
    assert result["id"] == "a1"
    mock_resolve.assert_called_once_with("Recaps")


@patch("scripts.get_article.list_category_articles.resolve")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_title_scoped_to_category_not_found(mock_load_creds, mock_resolve):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_resolve.return_value = {"success": False, "error": "No category matches 'Bogus'."}
    result = get_article.fetch({"title": "Anything", "category": "Bogus"})
    assert result["success"] is False
    assert result["error"] == "No category matches 'Bogus'."


@patch("scripts.get_article.wa_client.list_articles")
@patch("scripts.get_article.credentials.load_credentials")
def test_no_match_by_title(mock_load_creds, mock_list_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_WORLD_ARTICLES
    result = get_article.fetch({"title": "Totally Unrelated Title"})
    assert result["success"] is False
    assert "error" in result


def test_no_id_or_title_reports_error():
    result = get_article.fetch({})
    assert result["success"] is False
    assert "error" in result


@patch("scripts.get_article.credentials.load_credentials")
def test_no_credentials_reports_error(mock_load_creds):
    mock_load_creds.return_value = None
    result = get_article.fetch({"id": "a1"})
    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_get_article.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.get_article'`.

- [ ] **Step 3: Implement the script**

Create `scripts/get_article.py`:

```python
"""CLI: fetch one article's full content, either directly by id or by
fuzzy-matching a title (optionally scoped to a category's articles first).

Reads a JSON payload from stdin, one of:
    {"id": "..."}
    {"title": "...", "category": "..."}   # category optional
Writes a JSON result to stdout:
    {"success": true, "id":..., "title":..., "content":..., "templateType":...,
     "tags":..., "category":..., "url":...}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict

from scripts import credentials, list_category_articles, wa_client
from scripts.matching import find_best_match


def fetch(payload: Dict[str, Any]) -> Dict[str, Any]:
    article_id = payload.get("id")
    title = payload.get("title")
    category = payload.get("category")

    if not article_id and not title:
        return {"success": False, "error": "Provide either 'id' or 'title'."}

    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    if not article_id:
        if category:
            cat_result = list_category_articles.resolve(category)
            if not cat_result["success"]:
                return cat_result
            candidates = cat_result["articles"]
        else:
            try:
                candidates = wa_client.list_articles(creds)
            except wa_client.WAApiError as exc:
                return {"success": False, "error": str(exc)}

        match = find_best_match(title, candidates, key="title")
        if match is None:
            return {"success": False, "error": f"No article matches '{title}'."}
        article_id = match["id"]

    try:
        article = wa_client.get_article(creds, article_id)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success": True,
        "id": article.get("id", article_id),
        "title": article.get("title"),
        "content": article.get("content"),
        "templateType": article.get("templateType"),
        "tags": article.get("tags"),
        "category": article.get("category"),
        "url": article.get("url"),
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = fetch(payload)
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_get_article.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/get_article.py tests/test_get_article.py
git commit -m "feat: add get_article CLI"
```

---

## Task 4: Add both new scripts to the subprocess smoke test

**Files:**
- Modify: `tests/test_cli_invocation.py:34-40`

- [ ] **Step 1: Write the failing test update**

In `tests/test_cli_invocation.py`, modify the `SCRIPTS_AND_PAYLOADS` list to add two entries:

```python
SCRIPTS_AND_PAYLOADS = [
    ("scripts.list_categories", {}),
    ("scripts.create_category", {"title": "Anything"}),
    ("scripts.search_entities", {"names": ["Anything"]}),
    ("scripts.create_article", {"title": "T", "content": "C", "templateType": "article"}),
    ("scripts.publish_article", {"article_id": "does-not-matter"}),
    ("scripts.get_article", {"id": "does-not-matter"}),
    ("scripts.list_category_articles", {"category": "Anything"}),
]
```

- [ ] **Step 2: Run test to verify it fails first (before Task 1-3 code exists this would already fail; since Task 1-3 are done, this actually should pass immediately — run it to confirm)**

Run: `pytest tests/test_cli_invocation.py -v`
Expected: PASS (both new scripts already exist from Tasks 2-3, each correctly returns `{"success": false, "error": "No stored credentials..."}` under isolated HOME).

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli_invocation.py
git commit -m "test: add get_article and list_category_articles to CLI invocation smoke test"
```

---

## Task 5: Document the context-gathering workflow in SKILL.md

**Files:**
- Modify: `SKILL.md` (insert new section after "## 0. Credentials check", before "## 1. Pick a `templateType`")

- [ ] **Step 1: Insert the new section**

In `SKILL.md`, after the line `5. Once successful, credentials are stored in `~/.worldanvil-skill/` and this`
`   step is skipped in all future conversations.` (end of section 0) and before
`## 1. Pick a \`templateType\``, insert:

```markdown
## 0.5. Gather context before drafting (optional, read-only)

When the user references existing material in conversation — "like the
last recap", "what we planned last session", "the NPC's existing bio" —
pull that content in before drafting, so the new article stays consistent
with what already exists. This is read-only: no confirmation gate needed,
since nothing is written to World Anvil.

1. Call `python -m scripts.list_category_articles` with
   `{"category": "<the category the user implies or states>"}` to get the
   stub list (id/title/url) of articles in that category.
2. From the returned stubs, identify the right article by title yourself
   (same kind of judgment call as the entity-linking pass in step 3).
3. Call `python -m scripts.get_article` with `{"id": "<id from step 2>"}`
   (or `{"title": "...", "category": "..."}` to skip straight to a fuzzy
   title match within that category) to pull the full content.
4. Use that content as context for the new draft — quote from it, match
   its tone/structure, or reference it directly, as appropriate to what
   the user asked for.

This is separate from the mandatory drafting/confirmation flow below —
gathering context never itself writes anything to World Anvil.
```

- [ ] **Step 2: Verify the file reads correctly**

Run: `Get-Content SKILL.md | Select-String -Pattern "0.5" -Context 2,2`
Expected: shows the new section heading in place between section 0 and section 1.

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs: document optional read-context workflow in SKILL.md"
```

---

## Task 6: Full test suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `pytest -v`
Expected: all tests pass — the original 49 plus the new tests added in Tasks 1-4 (3 in test_wa_client.py, 5 in test_list_category_articles.py, 7 in test_get_article.py, plus the 2 new smoke-test parametrizations in test_cli_invocation.py).

- [ ] **Step 2: If anything fails, fix and re-run**

Do not proceed until the full suite is green.

- [ ] **Step 3: Final confirmation commit (if any stray changes remain)**

```bash
git status
```

Expected: clean working tree (everything already committed task-by-task above). If not, commit anything left over.
