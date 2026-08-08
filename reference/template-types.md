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
