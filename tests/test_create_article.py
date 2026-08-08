"""Tests for the create_article CLI, including the 422 templateType
fallback behavior."""
from unittest.mock import patch

from scripts import create_article
from scripts.wa_client import WAApiError

BASE_PAYLOAD = {
    "title": "Test Article",
    "content": "Some content",
    "templateType": "person",
    "state": "public",
}


@patch("scripts.create_article.wa_client.create_article")
@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_success(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.return_value = {"id": "art1", "url": "https://x/art1"}
    result = create_article.create(BASE_PAYLOAD)
    assert result["success"] is True
    assert result["id"] == "art1"
    assert result["fallback_used"] is False
    assert mock_create.call_count == 1


@patch("scripts.create_article.wa_client.create_article")
@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_falls_back_to_generic_on_422(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.side_effect = [
        WAApiError(422, "Invalid templateType"),
        {"id": "art1", "url": "https://x/art1"},
    ]
    result = create_article.create({**BASE_PAYLOAD, "templateType": "not-a-real-type"})
    assert result["success"] is True
    assert result["fallback_used"] is True
    assert result["templateType_used"] == "article"
    assert mock_create.call_count == 2
    second_call_payload = mock_create.call_args_list[1].args[1]
    assert second_call_payload["templateType"] == "article"


@patch("scripts.create_article.wa_client.create_article")
@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_non_422_error_does_not_retry(mock_load_creds, mock_create):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_create.side_effect = WAApiError(500, "Server error")
    result = create_article.create(BASE_PAYLOAD)
    assert result["success"] is False
    assert "error" in result
    assert mock_create.call_count == 1


@patch("scripts.create_article.credentials.load_credentials")
def test_create_article_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = create_article.create(BASE_PAYLOAD)
    assert result["success"] is False
    assert "error" in result
