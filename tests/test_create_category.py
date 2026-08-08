"""Tests for the create_category CLI."""
from unittest.mock import patch

from scripts import create_category


@patch("scripts.create_category.wa_client.create_category")
@patch("scripts.create_category.credentials.load_credentials")
def test_create_category_success(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.return_value = {"id": "c9", "title": "New Category"}
    result = create_category.create(title="New Category")
    assert result["success"] is True
    assert result["id"] == "c9"


@patch("scripts.create_category.credentials.load_credentials")
def test_create_category_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = create_category.create(title="New Category")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.create_category.wa_client.create_category")
@patch("scripts.create_category.credentials.load_credentials")
def test_create_category_api_error(mock_load_creds, mock_create):
    from scripts.wa_client import WAApiError

    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.side_effect = WAApiError(500, "Server error")
    result = create_category.create(title="New Category")
    assert result["success"] is False
    assert "error" in result
