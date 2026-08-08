# World Anvil Article Creator — Claude Skill

A Claude Skill that drafts, formats, and publishes World Anvil articles via
the Boromir v2 API. Nothing is written to your World Anvil world without
your explicit confirmation in chat.

## Setup

1. Get your World Anvil credentials:
   - Application key: request one at the WA API access form (see World Anvil's
     API documentation).
   - Auth token: generate one at https://www.worldanvil.com/api/auth/key
   - World ID: the skill can look this up by world name once you give it
     your application key and auth token (see `scripts/save_credentials.py`).
2. Enable Skills in Claude:
   - Free/Pro/Max: `Settings > Capabilities` → turn on **Code execution and
     file creation** (Skills requires this — it won't appear otherwise).
   - Team/Enterprise: an org owner must enable **Code execution and file
     creation** and **Skills** in `Organization settings > Skills` first.
3. Download this repo as a ZIP (no git needed):
   - On the [repo page](https://github.com/Lockinlove/World-Anvil-Skill),
     click the green **Code** button → **Download ZIP**.
   - Extract it — this creates a folder named `World-Anvil-Skill-main`.
   - Rename that extracted folder to `world-anvil-skill` (Claude's uploader
     requires the ZIP's top-level folder name to match `SKILL.md`'s `name:`
     field exactly, which is `world-anvil-skill`).
   - Re-zip the renamed `world-anvil-skill/` folder (so the new ZIP's
     top-level entry is `world-anvil-skill/`, containing `SKILL.md`,
     `scripts/`, `reference/`, etc. directly inside it).
4. In Claude, go to `Customize > Skills` → click **+** → **+ Create skill**
   → **Upload a skill** → select your re-zipped file.
5. Toggle the skill on. It's private to your account by default.
6. In a chat, ask it to set up the World Anvil skill. It will ask for the
   application key and auth token, then store them (along with your
   resolved world ID) in `~/.worldanvil-skill/credentials.json` on the
   machine running the code-execution environment. You will not need to
   provide them again in future chats from that same environment.

Note: `requirements.txt` (`requests`) needs to be installed in whatever
Python environment the code-execution sandbox uses to run this skill's
scripts — if Claude reports it can't `import requests`, ask it to install
the dependency in that environment first.

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

## License

MIT — see [LICENSE](LICENSE).

