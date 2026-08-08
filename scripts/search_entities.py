"""CLI: search the world's existing articles for candidate entity mentions
(for the entity-linking pass). Claude supplies the candidate names it found
in its own draft; this script only looks them up, it never decides on its
own what counts as a mention.

Reads a JSON payload from stdin: {"names": ["Ármen", "Velz"]}
Writes a JSON result to stdout:
    {"success": true, "matches": {"Ármen": {"id":..., "title":..., "url":...} or null, ...}}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict, List

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def search(names: List[str]) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        articles = wa_client.list_articles(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    matches: Dict[str, Any] = {}
    for name in names:
        match = find_best_match(name, articles, key="title")
        matches[name] = (
            {"id": match["id"], "title": match["title"], "url": match.get("url")} if match else None
        )

    return {"success": True, "matches": matches}


def main() -> None:
    payload = json.load(sys.stdin)
    result = search(names=payload.get("names", []))
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
