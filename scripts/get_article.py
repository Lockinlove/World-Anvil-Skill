"""CLI: fetch one article's full content, either directly by id or by
fuzzy-matching a title (optionally scoped to a category's articles first).

Reads a JSON payload from stdin, one of:
    {"id": "..."}
    {"title": "...", "category": "..."}   # category optional
Writes a JSON result to stdout:
    {"success": true, "id":..., "title":..., "content":..., "templateType":...,
     "tags":..., "category":..., "url":...}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict

from scripts import credentials, list_category_articles, wa_client
from scripts.matching import find_best_match


def fetch(payload: Dict[str, Any]) -> Dict[str, Any]:
    article_id = payload.get("id")
    title = payload.get("title")
    category = payload.get("category")

    if not article_id and not title:
        return {"success": False, "error": "Provide either 'id' or 'title'."}

    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    if not article_id:
        if category:
            cat_result = list_category_articles.resolve(category)
            if not cat_result["success"]:
                return cat_result
            candidates = cat_result["articles"]
        else:
            try:
                candidates = wa_client.list_articles(creds)
            except wa_client.WAApiError as exc:
                return {"success": False, "error": str(exc)}

        match = find_best_match(title, candidates, key="title")
        if match is None:
            return {"success": False, "error": f"No article matches '{title}'."}
        article_id = match["id"]

    try:
        article = wa_client.get_article(creds, article_id)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success": True,
        "id": article.get("id", article_id),
        "title": article.get("title"),
        "content": article.get("content"),
        "templateType": article.get("templateType"),
        "tags": article.get("tags"),
        "category": article.get("category"),
        "url": article.get("url"),
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = fetch(payload)
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
