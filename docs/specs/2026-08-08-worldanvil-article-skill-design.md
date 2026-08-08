# World Anvil Article Creator — Claude Skill Design

Date: 2026-08-08
Status: Approved

## Purpose

A shareable Claude Skill (Claude Desktop / claude.ai Skills feature) that turns an
already-agreed article idea (discussed in chat) into a properly formatted World
Anvil article and publishes it, via the Boromir v2 API. Usable by anyone with
their own World Anvil API key — not tied to any specific campaign/world.

v1 scope is **creation only**. Editing/updating existing articles is a future
addition, out of scope here.

## Non-goals (v1)

- Editing or deleting existing articles.
- Managing anything other than articles (no maps, timelines, images, etc.).
- Any action that writes to World Anvil without an explicit human confirmation
  in the same conversation (category creation, entity links, publishing).

## Package layout

New standalone project at `D:\OpenCode\worldanvil-article-skill\`, its own git
repo, independent of the DnD/Alarkdum exporter project.

```
worldanvil-article-skill/
├── SKILL.md                    # Claude-facing instructions & decision logic
├── reference/
│   └── template-types.md       # templateType decision table + fallback rule
├── scripts/
│   ├── wa_client.py            # thin requests-only wrapper (Boromir v2 API)
│   ├── credentials.py          # load/save creds, permission handling
│   ├── save_credentials.py     # CLI: store app key / auth token / world id
│   ├── list_categories.py      # CLI: fetch categories for fuzzy-match
│   ├── search_entities.py      # CLI: search world articles by name
│   ├── create_article.py       # CLI: PUT article (draft)
│   └── publish_article.py      # CLI: PATCH isWip/isDraft -> false
├── tests/
│   └── test_wa_client.py       # pytest, mocked requests, no live API calls
├── requirements.txt             # just `requests`
└── README.md                    # human-facing install/usage notes
```

No third-party WA library (no `pywaclient`). All API access is direct
`requests` calls against `https://www.worldanvil.com/api/external/boromir/`,
matching the documented Boromir v2 header auth scheme
(`x-application-key`, `x-auth-token`, `Content-type: application/json`,
`User-Agent`).

## Credential storage

- File: `~/.worldanvil-skill/credentials.json` (via Python `Path.home()`),
  **outside** the skill package directory so re-installing/updating the skill
  never wipes stored credentials.
- Contents: `application_key`, `auth_token`, `world_id` (resolved once from a
  world slug/name if the user provides that instead of a raw UUID).
- Permissions: `chmod 600` on POSIX; best-effort ACL lockdown via `icacls` on
  Windows (restrict to current user). Never printed to chat, never logged.
- `credentials.py` exposes `load_credentials()` / `save_credentials(...)`.
  `save_credentials.py` is the CLI entrypoint Claude calls after collecting
  values from the user in chat.
- SKILL.md instructs Claude: on first use in a conversation, attempt
  `load_credentials()`; if missing/invalid, ask the user for the three values
  in chat, then call `save_credentials.py` to persist them for all future
  sessions.

## Core workflow (encoded in SKILL.md)

1. **Credentials check** — load or prompt+save (above).
2. **Draft the article** — content is whatever was already agreed in the
   conversation before the skill was invoked; the skill formats it, it does
   not invent the underlying idea.
3. **Pick `templateType`** — via the decision table in
   `reference/template-types.md` (see below). The pick is stated to the user
   as part of the confirmation step in point 6, never applied silently.
4. **Resolve category** — the user states a target folder/category name.
   `list_categories.py` fetches existing categories for the world; match
   logic:
   - Exact match (case-insensitive) → use it.
   - Close/fuzzy match (e.g. minor typo, singular/plural) → use it, but
     surface which category was picked in the final confirmation.
   - No reasonable match → **stop and ask**: "No existing category matches
     'X' — create a new category called 'X'?" Only create on explicit yes.
     Never auto-create.
5. **Entity-linking pass** — scan the drafted content for proper-noun
   mentions (people, places, items, factions, etc.). For each, call
   `search_entities.py` against the world's existing articles (by title/name
   match via the API). Build a proposed set of `@[Display](type:uuid)`
   conversions. Present to the user:
   - Matched mentions → proposed link, awaiting confirmation.
   - Unmatched mentions → ask the user to choose: leave as plain text, or
     flag for a separate, explicitly-confirmed stub-article creation (which
     is itself a distinct confirmed action, not automatic).
   Apply only what the user confirms.
6. **Final confirmation** — before any write to World Anvil, show the fully
   assembled article: title, templateType, category (existing or
   to-be-created), tags, and content with resolved links. Wait for explicit
   go-ahead.
7. **Create as draft** — `create_article.py` PUTs the article via
   `article.put`-equivalent direct HTTP call with `editor: "code"` (raw
   markdown content, matching this world's established convention — no
   structured per-type field forms). `state` is set to the user's intended
   final state, but World Anvil's own default behavior leaves
   `isDraft`/`isWip` as `true` on creation regardless — this is relied upon
   as the "draft" mechanism. The created article's WA URL is reported back
   to the user (visible only to the owner while in draft/WIP state).
8. **Publish on request only** — the user must explicitly say to publish.
   Only then does `publish_article.py` PATCH the article's `isWip` and
   `isDraft` flags to `false`, making it publicly visible.

## `templateType` decision table (`reference/template-types.md`)

Grounded in real values already in production use in an existing World Anvil
world (sampled from 219 articles): `person` (109), `report` (91), `landmark`
(19), `plot` (19), `organization` (17), `article`/generic (15), `settlement`
(13), `location` (11), `item` (5), `species` (2), `myth` (1), `ritual` (1),
`law` (1).

The reference file documents:
- A mapping of "what the article is about" → recommended `templateType`
  (person/NPC/PC → `person`; town/city/named place → `settlement`;
  smaller notable landmark → `landmark`; general place without more
  specificity → `location`; guild/kingdom/group → `organization`; physical
  object → `item`; monster/race/creature type → `species`; deity/creation
  myth/folklore → `myth`; ceremony/rite → `ritual`; in-world legal
  rule/decree → `law`; session summary → `report`; overarching storyline/
  quest thread → `plot`; anything that doesn't clearly fit → generic
  `article`).
- Note that World Anvil supports additional official template types beyond
  this world's observed set (e.g. `condition`, `document`, `ethnicity`,
  `event`, `family`, `formation`, `language`, `material`,
  `military-conflict`, `natural-law`, `profession`, `prose`, `rank`,
  `religion`, `technology`, `title`, `vehicle`, `vocabulary`, `diplomacy`).
  These may be offered as a best-guess pick when clearly applicable, but the
  fallback safety net (below) covers the case where the guess is wrong.
- **Fallback rule**: if the API rejects the chosen `templateType` (HTTP 422),
  retry once automatically with generic `"article"`, and tell the user this
  fallback happened — never fail silently, never loop retries.

## Error handling

- Any Boromir API error (401/403/404/422/500) surfaces to the user verbatim;
  no silent retries except the single 422 `templateType` fallback above.
- Partial failures (e.g. a new category is created but the subsequent article
  PUT fails) are explicitly reported so nothing is silently orphaned.
- Nothing is ever deleted or overwritten in v1 — creation-only.
- Network/timeout errors are reported and the workflow stops; no partial
  writes are retried blindly.

## Testing

- `pytest` unit tests in `tests/test_wa_client.py`, mocking `requests` (no
  live API calls in the test suite):
  - Article payload construction (fields, `editor: "code"`, draft flags).
  - Category fuzzy-match logic (exact / case-insensitive / close match / no
    match).
  - Credential file round-trip and permission enforcement.
  - 422 fallback-to-`article` retry logic.
- Matches this ecosystem's existing convention of a `tests/` pytest suite
  (as used in the sibling DnD/Alarkdum exporter project).

## Open items for the implementation plan

- Exact fuzzy-match algorithm/threshold for category names (e.g. simple
  normalized string distance vs. a library like `rapidfuzz`).
- Exact heuristics for "proper noun mention" detection in the entity-linking
  scan (regex/capitalization heuristic vs. asking the model to just read the
  draft and list candidates itself — likely the latter, since Claude is doing
  the drafting anyway).
- `SKILL.md` exact prose/wording of the decision logic and confirmation
  prompts.
