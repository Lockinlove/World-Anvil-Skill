"""Tests for credential storage. Uses a temp HOME so the real
~/.worldanvil-skill is never touched by the test suite."""
import json
import os
import stat
import sys

import pytest

from scripts import credentials


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "CRED_DIR", tmp_path / ".worldanvil-skill")
    monkeypatch.setattr(credentials, "CRED_FILE", tmp_path / ".worldanvil-skill" / "credentials.json")
    return tmp_path


def test_load_credentials_returns_none_when_missing(temp_home):
    assert credentials.load_credentials() is None


def test_save_then_load_round_trip(temp_home):
    credentials.save_credentials("app-key", "auth-token", "world-id", world_title="Alarkdum")
    loaded = credentials.load_credentials()
    assert loaded == {
        "application_key": "app-key",
        "auth_token": "auth-token",
        "world_id": "world-id",
        "world_title": "Alarkdum",
    }


def test_save_creates_directory(temp_home):
    assert not credentials.CRED_DIR.exists()
    credentials.save_credentials("app-key", "auth-token", "world-id")
    assert credentials.CRED_DIR.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file permission bits don't apply on Windows")
def test_save_restricts_file_permissions(temp_home):
    credentials.save_credentials("app-key", "auth-token", "world-id")
    mode = stat.S_IMODE(os.stat(credentials.CRED_FILE).st_mode)
    assert mode == 0o600


def test_load_returns_none_on_corrupt_file(temp_home):
    credentials.CRED_DIR.mkdir(parents=True)
    credentials.CRED_FILE.write_text("not valid json", encoding="utf-8")
    assert credentials.load_credentials() is None


def test_load_returns_none_on_missing_required_keys(temp_home):
    """Regression test: a valid-JSON-but-wrong-shaped file (e.g. hand-edited
    or partially written) must be treated as invalid, not returned as-is."""
    credentials.CRED_DIR.mkdir(parents=True)
    credentials.CRED_FILE.write_text(json.dumps({"application_key": "a"}), encoding="utf-8")
    assert credentials.load_credentials() is None


def test_load_returns_none_when_file_is_a_json_list(temp_home):
    credentials.CRED_DIR.mkdir(parents=True)
    credentials.CRED_FILE.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert credentials.load_credentials() is None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file permission bits don't apply on Windows")
def test_save_restricts_directory_permissions(temp_home):
    """Regression test for the 0d433bd security fix: the credentials
    directory itself should be locked down (0700), not just the file."""
    credentials.save_credentials("app-key", "auth-token", "world-id")
    mode = stat.S_IMODE(os.stat(credentials.CRED_DIR).st_mode)
    assert mode == 0o700


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: verifies no permissive-then-tightened window")
def test_save_never_leaves_file_world_or_group_readable(temp_home, monkeypatch):
    """Regression test for the 0d433bd security fix: the file must be
    created with restrictive permissions atomically (via os.open with an
    explicit mode), not opened permissively and chmod'd after the fact.
    We simulate a permissive umask to prove the initial creation mode itself
    is restrictive, not just the final chmod."""
    old_umask = os.umask(0o022)  # a typical permissive default umask
    try:
        credentials.save_credentials("app-key", "auth-token", "world-id")
    finally:
        os.umask(old_umask)
    mode = stat.S_IMODE(os.stat(credentials.CRED_FILE).st_mode)
    assert mode == 0o600


def test_windows_permission_failure_is_logged_not_silent(temp_home, monkeypatch, caplog):
    """Regression test for the 0d433bd security fix: on Windows, a failed
    icacls call must be logged (not silently ignored) so a broadened-
    permissions credentials file is never invisible to the user."""
    monkeypatch.setattr(credentials.sys, "platform", "win32")

    class FailedResult:
        returncode = 1

    monkeypatch.setattr(
        credentials.subprocess, "run", lambda *args, **kwargs: FailedResult()
    )
    with caplog.at_level("WARNING"):
        credentials.save_credentials("app-key", "auth-token", "world-id")
    assert any("permission" in record.message.lower() for record in caplog.records)
