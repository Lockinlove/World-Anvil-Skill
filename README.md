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
