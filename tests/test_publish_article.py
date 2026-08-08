"""Tests for the publish_article CLI."""
from unittest.mock import patch

from scripts import publish_article


@patch("scripts.publish_article.wa_client.patch_article")
@patch("scripts.publish_article.credentials.load_credentials")
def test_publish_success(mock_load_creds, mock_patch):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_patch.return_value = {"id": "art1", "url": "https://x/art1"}
    result = publish_article.publish(article_id="art1")
    assert result["success"] is True
    assert result["url"] == "https://x/art1"
    mock_patch.assert_called_once_with(
        {"application_key": "a", "auth_token": "t", "world_id": "w"},
        "art1",
        {"isWip": False, "isDraft": False},
    )


@patch("scripts.publish_article.credentials.load_credentials")
def test_publish_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = publish_article.publish(article_id="art1")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.publish_article.wa_client.patch_article")
@patch("scripts.publish_article.credentials.load_credentials")
def test_publish_api_error(mock_load_creds, mock_patch):
    from scripts.wa_client import WAApiError

    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_patch.side_effect = WAApiError(404, "Not found")
    result = publish_article.publish(article_id="does-not-exist")
    assert result["success"] is False
    assert "error" in result
