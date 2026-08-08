"""CLI: fuzzy-match a category by name, then return the stub list (id,
title, url) of every article inside it. Read-only — use get_article.py to
fetch full content once the right article is identified.

Reads a JSON payload from stdin: {"category": "NPCs"}
Writes a JSON result to stdout:
    {"success": true, "category": {...}, "articles": [{"id","title","url"}, ...]}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict, Optional

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def resolve(category_target: Optional[str]) -> Dict[str, Any]:
    if not category_target:
        return {"success": False, "error": "'category' is required."}

    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    try:
        categories = wa_client.list_categories(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    match = find_best_match(category_target, categories, key="title")
    if match is None:
        return {"success": False, "error": f"No category matches '{category_target}'."}

    try:
        detail = wa_client.get_category_articles(creds, match["id"])
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    articles = detail.get("articles")
    if not isinstance(articles, list):
        return {"success": False, "error": "unexpected response shape", "raw": detail}

    stubs = [
        {"id": a.get("id"), "title": a.get("title"), "url": a.get("url")}
        for a in articles
    ]
    return {
        "success": True,
        "category": {"id": match["id"], "title": match["title"]},
        "articles": stubs,
    }


def main() -> None:
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    result = resolve(category_target=payload.get("category"))
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
