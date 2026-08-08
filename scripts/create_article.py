"""CLI: create a World Anvil article as a draft (isWip/isDraft remain true
by World Anvil's own default on creation — that is the "draft" mechanism
this skill relies on; see publish_article.py to flip it public).

If the API rejects the chosen templateType (HTTP 422), retries exactly once
with the generic "article" templateType and reports that a fallback
happened — never silently, never in a loop.

Reads a JSON payload from stdin:
    {"title":..., "content":..., "templateType":..., "state":"public",
     "tags":"...", "subheading":"...", "category_id":"...",
     "article_parent_id":"..."}
Writes a JSON result to stdout:
    {"success": true, "id":..., "url":..., "templateType_used":...,
     "fallback_used": bool}
or on failure:
    {"success": false, "error": "..."}
"""
import json
import sys
from typing import Any, Dict

from scripts import credentials, wa_client

GENERIC_TEMPLATE_TYPE = "article"


def create(payload: Dict[str, Any]) -> Dict[str, Any]:
    creds = credentials.load_credentials()
    if creds is None:
        return {"success": False, "error": "No stored credentials. Run save_credentials.py first."}

    fallback_used = False
    template_type = payload.get("templateType", GENERIC_TEMPLATE_TYPE)

    try:
        created = wa_client.create_article(creds, payload)
    except wa_client.WAApiError as exc:
        if exc.status_code != 422 or template_type == GENERIC_TEMPLATE_TYPE:
            return {"success": False, "error": str(exc)}
        fallback_used = True
        template_type = GENERIC_TEMPLATE_TYPE
        fallback_payload = {**payload, "templateType": GENERIC_TEMPLATE_TYPE}
        try:
            created = wa_client.create_article(creds, fallback_payload)
        except wa_client.WAApiError as retry_exc:
            return {"success": False, "error": str(retry_exc)}

    return {
        "success": True,
        "id": created["id"],
        "url": created.get("url"),
        "templateType_used": template_type,
        "fallback_used": fallback_used,
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = create(payload)
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
