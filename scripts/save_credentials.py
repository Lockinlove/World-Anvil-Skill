"""CLI: validate World Anvil credentials and store them locally.

Reads a JSON payload from stdin:
    {"application_key": "...", "auth_token": "...", "world_id": "..."}
or, to resolve a world by name instead of by raw UUID:
    {"application_key": "...", "auth_token": "...", "world_name": "..."}

Writes a JSON result to stdout:
    {"success": true, "world_id": "...", "world_title": "..."}
or on failure:
    {"success": false, "error": "..."}  (with "available_worlds" if relevant)
"""
import json
import sys
from typing import Any, Dict, Optional

from scripts import credentials, wa_client
from scripts.matching import find_best_match


def resolve_and_save(
    application_key: str,
    auth_token: str,
    world_id: Optional[str] = None,
    world_name: Optional[str] = None,
) -> Dict[str, Any]:
    creds = {"application_key": application_key, "auth_token": auth_token, "world_id": world_id or ""}
    try:
        identity = wa_client.get_identity(creds)
    except wa_client.WAApiError as exc:
        return {"success": False, "error": str(exc)}

    resolved_world_id = world_id
    resolved_world_title = None

    if not resolved_world_id:
        try:
            worlds = wa_client.list_user_worlds(creds, identity["id"])
        except wa_client.WAApiError as exc:
            return {"success": False, "error": str(exc)}
        match = find_best_match(world_name or "", worlds, key="title")
        if match is None:
            return {
                "success": False,
                "error": f"No world matching '{world_name}' found for this account.",
                "available_worlds": [w["title"] for w in worlds],
            }
        resolved_world_id = match["id"]
        resolved_world_title = match["title"]

    credentials.save_credentials(
        application_key, auth_token, resolved_world_id, world_title=resolved_world_title
    )
    return {"success": True, "world_id": resolved_world_id, "world_title": resolved_world_title}


def main() -> None:
    payload = json.load(sys.stdin)
    result = resolve_and_save(
        application_key=payload["application_key"],
        auth_token=payload["auth_token"],
        world_id=payload.get("world_id"),
        world_name=payload.get("world_name"),
    )
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
