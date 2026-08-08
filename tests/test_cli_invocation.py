"""Smoke tests that actually invoke each CLI as a real subprocess, exactly
the way SKILL.md instructs (`python -m scripts.<name>` from the repo root).

This exists because unit tests that only *import* `scripts.xxx` directly
never exercise the real command-line invocation path, and would not have
caught a real bug where `python scripts/xxx.py` (as originally documented)
failed with ImportError while `python -m scripts.xxx` worked. These tests
run against a redirected HOME/USERPROFILE so the real
~/.worldanvil-skill/credentials.json on the machine running the tests is
never read or touched.

`save_credentials` is deliberately excluded from the subprocess list below:
unlike every other script, it calls the real World Anvil `identity` endpoint
unconditionally (that's its whole job — validating credentials), so it
cannot be smoke-tested this way without making a live network call. Its
logic is already covered by mocked unit tests in `test_save_credentials.py`;
here we only need to confirm it at least *imports* cleanly as a module,
which `test_save_credentials_module_imports_cleanly` below checks without
invoking `main()`.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every stdin-consuming CLI script that checks stored credentials *before*
# making any network call, paired with a minimal stdin payload that lets it
# get as far as the "no stored credentials" check without erroring on
# missing keys first.
SCRIPTS_AND_PAYLOADS = [
    ("scripts.list_categories", {}),
    ("scripts.create_category", {"title": "Anything"}),
    ("scripts.search_entities", {"names": ["Anything"]}),
    ("scripts.create_article", {"title": "T", "content": "C", "templateType": "article"}),
    ("scripts.publish_article", {"article_id": "does-not-matter"}),
    ("scripts.get_article", {"id": "does-not-matter"}),
    ("scripts.list_category_articles", {"category": "Anything"}),
]


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect HOME (POSIX) and USERPROFILE (Windows) so the subprocess
    never touches the real machine's stored credentials."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize("module_name,payload", SCRIPTS_AND_PAYLOADS)
def test_script_runs_as_module_without_import_error(module_name, payload, isolated_home):
    result = subprocess.run(
        [sys.executable, "-m", module_name],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    assert "ImportError" not in result.stderr, result.stderr
    assert "ModuleNotFoundError" not in result.stderr, result.stderr
    assert result.returncode == 0, result.stderr

    output = json.loads(result.stdout)
    assert output["success"] is False
    assert "error" in output


def test_script_run_as_direct_file_path_fails_documented_way(isolated_home):
    """Documents (and pins) the known-broken invocation so a future change
    to the package layout doesn't silently swap which form is correct
    without SKILL.md being updated to match."""
    result = subprocess.run(
        [sys.executable, "scripts/list_categories.py"],
        input="{}",
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    assert result.returncode != 0
    assert "ImportError" in result.stderr


def test_save_credentials_module_imports_cleanly(isolated_home):
    """save_credentials makes a live network call in its normal operation
    (validating credentials against the real identity endpoint), so it's
    excluded from the invocation smoke test above. This only confirms the
    module itself is importable/runnable as `python -m scripts.save_credentials`
    without an ImportError, using empty stdin so `main()` fails on a missing
    dict key (KeyError) rather than proceeding to any network call."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.save_credentials"],
        input="{}",
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    assert "ImportError" not in result.stderr, result.stderr
    assert "ModuleNotFoundError" not in result.stderr, result.stderr
