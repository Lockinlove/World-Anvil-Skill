"""Local, per-user storage of World Anvil credentials.

Stored outside the skill package directory (in the user's home folder) so
reinstalling/updating the skill never wipes stored credentials. File
permissions are locked down to the current user where the OS supports it.
"""
import json
import logging
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

CRED_DIR = Path.home() / ".worldanvil-skill"
CRED_FILE = CRED_DIR / "credentials.json"


def _restrict_permissions(path: Path) -> None:
    if sys.platform == "win32":
        # Best-effort: restrict to the current user via icacls. Failure here
        # is non-fatal (e.g. on filesystems that don't support ACLs), but is
        # logged (never logging file contents) so it isn't silently invisible.
        try:
            result = subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', '')}:F"],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                logger.warning(
                    "Could not restrict permissions on %s (icacls exited %d). "
                    "The credentials file may be readable by other local users.",
                    path,
                    result.returncode,
                )
        except OSError:
            logger.warning(
                "Could not restrict permissions on %s (icacls unavailable). "
                "The credentials file may be readable by other local users.",
                path,
            )
    else:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600


REQUIRED_KEYS = ("application_key", "auth_token", "world_id")


def load_credentials() -> Optional[Dict[str, str]]:
    if not CRED_FILE.exists():
        return None
    try:
        with open(CRED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or not all(key in data for key in REQUIRED_KEYS):
        return None
    return data


def save_credentials(
    application_key: str,
    auth_token: str,
    world_id: str,
    world_title: Optional[str] = None,
) -> None:
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        os.chmod(CRED_DIR, stat.S_IRWXU)  # 0o700, defense-in-depth on the directory
    data = {
        "application_key": application_key,
        "auth_token": auth_token,
        "world_id": world_id,
    }
    if world_title is not None:
        data["world_title"] = world_title

    # Create the file with restrictive permissions atomically on POSIX (avoids
    # a window where a default-umask, more-permissive file briefly exists
    # before being chmod'd). On Windows, permissions are tightened afterward
    # via _restrict_permissions since os.open's mode argument is ignored there.
    if sys.platform == "win32":
        with open(CRED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    else:
        fd = os.open(CRED_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    _restrict_permissions(CRED_FILE)
