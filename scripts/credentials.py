"""Local, per-user storage of World Anvil credentials.

Stored outside the skill package directory (in the user's home folder) so
reinstalling/updating the skill never wipes stored credentials. File
permissions are locked down to the current user where the OS supports it.
"""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

CRED_DIR = Path.home() / ".worldanvil-skill"
CRED_FILE = CRED_DIR / "credentials.json"


def _restrict_permissions(path: Path) -> None:
    if sys.platform == "win32":
        # Best-effort: restrict to the current user via icacls. Failure here
        # is non-fatal (e.g. on filesystems that don't support ACLs).
        try:
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', '')}:F"],
                capture_output=True,
                check=False,
            )
        except OSError:
            pass
    else:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def load_credentials() -> Optional[Dict[str, str]]:
    if not CRED_FILE.exists():
        return None
    try:
        with open(CRED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_credentials(
    application_key: str,
    auth_token: str,
    world_id: str,
    world_title: Optional[str] = None,
) -> None:
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "application_key": application_key,
        "auth_token": auth_token,
        "world_id": world_id,
    }
    if world_title:
        data["world_title"] = world_title
    with open(CRED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    _restrict_permissions(CRED_FILE)
