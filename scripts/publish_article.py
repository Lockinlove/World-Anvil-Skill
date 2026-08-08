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
