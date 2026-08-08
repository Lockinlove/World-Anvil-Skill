"""CLI: fetch existing categories for the configured world and, if a target
name is given, find the best matching existing category.

Reads a JSON payload from stdin: {"target": "Characters"} (target optional).
Writes a JSON result to stdout:
    {"success": true, "categories": [...], "match": {...} or null}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict, Optional

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def resolve_category(target: Optional[str]) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        categories = wa_client.list_categories(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    match = find_best_match(target, categories, key="title") if target else None
    return {"success": True, "categories": categories, "match": match}


def main() -> None:
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    result = resolve_category(target=payload.get("target"))
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
