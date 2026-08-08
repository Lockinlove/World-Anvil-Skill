"""Tests for the save_credentials CLI's resolution logic (world lookup by
name). No live API calls: wa_client functions are monkeypatched."""
from unittest.mock import patch

from scripts import save_credentials


@patch("scripts.save_credentials.credentials.save_credentials")
@patch("scripts.save_credentials.wa_client.list_user_worlds")
@patch("scripts.save_credentials.wa_client.get_identity")
def test_resolve_by_world_name_success(mock_identity, mock_worlds, mock_save):
    mock_identity.return_value = {"id": "u1", "username": "Bob"}
    mock_worlds.return_value = [
        {"id": "w1", "title": "Alarkdum"},
        {"id": "w2", "title": "Other World"},
    ]
    result = save_credentials.resolve_and_save(
        application_key="app", auth_token="tok", world_name="Alarkdum"
    )
    assert result["success"] is True
    assert result["world_id"] == "w1"
    assert "persistence_note" in result
    mock_save.assert_called_once_with("app", "tok", "w1", world_title="Alarkdum")


@patch("scripts.save_credentials.wa_client.list_user_worlds")
@patch("scripts.save_credentials.wa_client.get_identity")
def test_resolve_by_world_name_no_match(mock_identity, mock_worlds):
    mock_identity.return_value = {"id": "u1", "username": "Bob"}
    mock_worlds.return_value = [{"id": "w1", "title": "Alarkdum"}]
    result = save_credentials.resolve_and_save(
        application_key="app", auth_token="tok", world_name="Nonexistent"
    )
    assert result["success"] is False
    assert "available_worlds" in result


@patch("scripts.save_credentials.credentials.save_credentials")
@patch("scripts.save_credentials.wa_client.get_identity")
def test_resolve_by_world_id_skips_lookup(mock_identity, mock_save):
    mock_identity.return_value = {"id": "u1", "username": "Bob"}
    result = save_credentials.resolve_and_save(
        application_key="app", auth_token="tok", world_id="w1"
    )
    assert result["success"] is True
    assert result["world_id"] == "w1"
    assert "persistence_note" in result
    mock_save.assert_called_once_with("app", "tok", "w1", world_title=None)


@patch("scripts.save_credentials.wa_client.get_identity")
def test_invalid_credentials_reports_error(mock_identity):
    from scripts.wa_client import WAApiError

    mock_identity.side_effect = WAApiError(401, "Unauthorized")
    result = save_credentials.resolve_and_save(
        application_key="bad", auth_token="bad", world_id="w1"
    )
    assert result["success"] is False
    assert "error" in result
