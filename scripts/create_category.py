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
