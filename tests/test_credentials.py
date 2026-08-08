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
