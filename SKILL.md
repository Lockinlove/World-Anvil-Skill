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
