# Read Capability for Categories & Articles — Design

## Motivation

The skill can currently only create articles/categories. It has no way to
read existing article content, so Claude can't use existing world lore as
context while drafting new articles. Concrete motivating case: writing a
session recap that should reference the previous recap and the
session-planning notes, both of which already exist as articles in the
user's world.

## Scope

Read-only. No new write actions, no changes to the existing
creation/confirmation flow (SKILL.md sections 1-6 unchanged in spirit).
Two new CLI scripts plus two new `wa_client.py` functions.

## `wa_client.py` additions

```python
def get_article(creds, article_id) -> Dict[str, Any]:
    # GET article?id=X&granularity=1
    # granularity 1 = "principal display object" per WA docs —
    # includes displayable content, not just an id/title/url reference.

def get_category_articles(creds, category_id) -> Dict[str, Any]:
    # GET category?id=X&granularity=2
    # granularity 2 = "detailed object, contains linking data, related
    # entity" per WA docs. Linked entities (the category's articles) are
    # returned at granularity -1 (id/title/url stub) per the same docs.
    # Returns the raw response body; callers pull out the article list.
```

**Known risk:** the exact key holding the linked-articles array inside the
granularity-2 category response is not confirmed against a live call (WA's
Boromir API is in beta; full Swagger schema wasn't reachable during design).
Mitigation: `list_category_articles.py` checks for the expected key and, if
absent, returns `{"success": false, "error": "unexpected response shape",
"raw": <body>}` instead of crashing or guessing. This surfaces the real
shape on first live use so the key name can be corrected in one line if
wrong — same "fail loud, never silent" precedent as the existing 422
`templateType` fallback in `create_article.py`.

## `scripts/get_article.py`

Fetch one full article's content.

Input (stdin): one of
```json
{"id": "..."}
```
```json
{"title": "...", "category": "..."}
```
(`category` optional — narrows the fuzzy match to that category's articles
via `get_category_articles`; if omitted, fuzzy-matches against the full
world article list via the existing `wa_client.list_articles`.)

Output (stdout):
```json
{"success": true, "id": "...", "title": "...", "content": "...",
 "templateType": "...", "tags": "...", "category": {"id": "...", "title": "..."}}
```
or
```json
{"success": false, "error": "..."}
```
If a `title` lookup finds no reasonable match, returns
`{"success": false, "error": "No article matches '<title>'."}`. This is a
harder failure than `list_categories.py`'s `match: null` convention
(rather than surfacing "no match" as a still-successful result for the
caller to branch on) because fetching a specific article by title is
already a terminal lookup, not a step in a larger resolve-then-confirm
flow — there's nothing further to do with a no-match here except report it.

## `scripts/list_category_articles.py`

Stub-list the articles inside one category, for browsing/narrowing before a
full fetch.

Input (stdin):
```json
{"category": "..."}
```

Output (stdout):
```json
{"success": true, "category": {"id": "...", "title": "..."},
 "articles": [{"id": "...", "title": "...", "url": "..."}, ...]}
```
or
```json
{"success": false, "error": "..."}
```
(including "no category match" when the fuzzy match on `category` fails —
a hard failure, since resolving a category to fetch its articles is a
terminal lookup here, not a step where a null match is itself a useful
result to hand back to the caller, the way `list_categories.py`'s
`match: null` is for its own resolve-then-confirm flow).

## SKILL.md changes

New section inserted after the existing credentials-check step (numbered
as an optional "0.5"), documenting:

- When the user references existing material in conversation ("like the
  last recap", "what we planned last session", "the NPC's existing bio"),
  Claude should gather context before drafting:
  1. Call `list_category_articles` to find the right category (fuzzy match
     on whatever category name the user implies or states).
  2. From the returned stubs, identify the right article by title (Claude's
     own judgment, same as the existing entity-linking pass judgment call).
  3. Call `get_article` (by `id` from the stub) to pull full content.
  4. Use that content as context for the new draft.
- Explicitly note this is optional, read-only context-gathering, distinct
  from the mandatory drafting/confirmation flow in sections 1-6 — no
  confirmation gate needed since nothing is written to World Anvil.

## Testing

Same style as the existing suite (`tests/`): mocked `wa_client` calls, no
live API hits.

- `tests/test_get_article.py` — success by id, success by title (world-wide
  and category-scoped), no-match case, WAApiError passthrough.
- `tests/test_list_category_articles.py` — success, no category match,
  "unexpected response shape" fallback path.

Existing 49 tests untouched. New tests follow the same mocking approach
already used in `test_search_entities.py` / `test_list_categories.py`.

## Out of scope

- Editing or deleting existing articles (still out of scope for this
  skill entirely).
- Full-text search across article bodies (only title-based fuzzy match,
  same as existing category/entity resolution).
- Any UI/formatting changes to how fetched content is presented — that's
  left to Claude's judgment in conversation, same as today.
