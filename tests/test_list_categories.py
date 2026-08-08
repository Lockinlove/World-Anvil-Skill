"""Tests for the list_categories CLI's matching behavior."""
from unittest.mock import patch

from scripts import list_categories

FAKE_CATEGORIES = [
    {"id": "c1", "title": "Characters"},
    {"id": "c2", "title": "Places"},
]


@patch("scripts.list_categories.wa_client.list_categories")
@patch("scripts.list_categories.credentials.load_credentials")
def test_target_matches_existing_category(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_categories.resolve_category(target="characters")
    assert result["success"] is True
    assert result["match"] == {"id": "c1", "title": "Characters"}
    assert result["categories"] == FAKE_CATEGORIES


@patch("scripts.list_categories.wa_client.list_categories")
@patch("scripts.list_categories.credentials.load_credentials")
def test_target_with_no_match(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_categories.resolve_category(target="Completely New Folder")
    assert result["success"] is True
    assert result["match"] is None
    assert result["categories"] == FAKE_CATEGORIES


@patch("scripts.list_categories.credentials.load_credentials")
def test_no_credentials_reports_error(mock_load_creds):
    mock_load_creds.return_value = None
    result = list_categories.resolve_category(target="Characters")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.list_categories.wa_client.list_categories")
@patch("scripts.list_categories.credentials.load_credentials")
def test_no_target_lists_all(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_categories.resolve_category(target=None)
    assert result["success"] is True
    assert result["match"] is None
    assert result["categories"] == FAKE_CATEGORIES
