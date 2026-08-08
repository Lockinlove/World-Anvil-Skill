# World Anvil Article Creator — Claude Skill

A Claude Skill that drafts, formats, and publishes World Anvil articles via
the Boromir v2 API. Nothing is written to your World Anvil world without
your explicit confirmation in chat.

## Credential persistence depends on where you run this

Credentials are saved to a plain JSON file at
`~/.worldanvil-skill/credentials.json` on **the machine actually executing
the Python code**. Whether that survives to your next chat depends entirely
on which Claude product you're using:

- **Claude Code, running on your own computer:** persists normally. `~` is
  your real home directory on disk, so credentials survive restarts, new
  chats, and skill updates. This is the environment this skill was designed
  for.
- **claude.ai web or mobile chat:** each conversation runs in a fresh,
  disposable sandbox. `~/.worldanvil-skill/credentials.json` gets created,
  gets used for the rest of that one chat, then is destroyed with the
  sandbox when the chat ends — nothing survives to your next session. You
  will be asked for your application key and auth token again every time.
  This is not a bug; there is no local disk in that product for anything to
  persist on.

If you're on claude.ai chat and want to avoid re-entering credentials each
session, the only persistent option is pasting them into **Project
Knowledge** (or uploading them as a project file) so Claude can read them at
the start of every chat in that project. Be clear about what that trades
away: Project Knowledge is stored on Anthropic's servers in plaintext,
readable by Claude on every relevant request and visible to anyone else with
access to that project. It is **not** local-only, and there's no built-in
expiry. Only do this if you've accepted that tradeoff — it is a convenience
measure, not a security best practice. Using a read-only or otherwise
scoped World Anvil token (if the API supports one) limits the blast radius
if it does.

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
   - No need to rename or repackage anything — upload the downloaded ZIP
     as-is.
4. In Claude, go to `Customize > Skills` → click **+** → **+ Create skill**
   → **Upload a skill** → select the downloaded ZIP.
5. Toggle the skill on. It's private to your account by default.
6. In a chat, ask it to set up the World Anvil skill. It will ask for the
   application key and auth token, then store them (along with your
   resolved world ID) in `~/.worldanvil-skill/credentials.json` on the
   machine running the code-execution environment. **Whether you need to
   provide them again next time depends on your environment** — see
   "Credential persistence depends on where you run this" above.

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

