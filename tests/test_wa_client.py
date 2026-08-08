"""Tests for the requests-only Boromir API wrapper. No live API calls."""
from unittest.mock import patch, MagicMock

import pytest

from scripts import wa_client

CREDS = {
    "application_key": "app-key-123",
    "auth_token": "auth-token-456",
    "world_id": "world-uuid-789",
}


def _mock_response(status_code=200, json_body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    return resp


def test_headers_includes_auth_and_app_key():
    headers = wa_client.build_headers(CREDS)
    assert headers["x-auth-token"] == "auth-token-456"
    assert headers["x-application-key"] == "app-key-123"
    assert "User-Agent" in headers


@patch("scripts.wa_client.requests.get")
def test_get_identity_success(mock_get):
    mock_get.return_value = _mock_response(200, {"success": True, "id": "u1", "username": "Bob"})
    result = wa_client.get_identity(CREDS)
    assert result["id"] == "u1"
    assert result["username"] == "Bob"


@patch("scripts.wa_client.requests.get")
def test_get_identity_unauthorized_raises(mock_get):
    mock_get.return_value = _mock_response(401, {})
    with pytest.raises(wa_client.WAApiError) as exc_info:
        wa_client.get_identity(CREDS)
    assert exc_info.value.status_code == 401


@patch("scripts.wa_client.requests.post")
def test_list_user_worlds_paginates_until_empty(mock_post):
    page1 = _mock_response(200, {"success": True, "entities": [{"id": "w1", "title": "First"}]})
    page2 = _mock_response(200, {"success": True, "entities": []})
    mock_post.side_effect = [page1, page2]
    worlds = wa_client.list_user_worlds(CREDS, "u1")
    assert worlds == [{"id": "w1", "title": "First"}]
    assert mock_post.call_count == 2


@patch("scripts.wa_client.requests.post")
def test_list_categories_returns_entities(mock_post):
    mock_post.side_effect = [
        _mock_response(200, {"success": True, "entities": [{"id": "c1", "title": "Places"}]}),
        _mock_response(200, {"success": True, "entities": []}),
    ]
    categories = wa_client.list_categories(CREDS)
    assert categories == [{"id": "c1", "title": "Places"}]


@patch("scripts.wa_client.requests.put")
def test_create_category(mock_put):
    mock_put.return_value = _mock_response(200, {"success": True, "id": "c9", "title": "New Cat"})
    result = wa_client.create_category(CREDS, "New Cat")
    assert result["id"] == "c9"
    sent_json = mock_put.call_args.kwargs["json"]
    assert sent_json["title"] == "New Cat"
    assert sent_json["world"] == {"id": "world-uuid-789"}


@patch("scripts.wa_client.requests.put")
def test_create_article_sends_expected_payload(mock_put):
    mock_put.return_value = _mock_response(200, {"success": True, "id": "a1", "url": "https://x/a1"})
    payload = {
        "title": "Test Article",
        "content": "Some content",
        "templateType": "person",
        "category_id": "c1",
        "tags": "npc",
        "state": "public",
    }
    result = wa_client.create_article(CREDS, payload)
    assert result["id"] == "a1"
    sent = mock_put.call_args.kwargs["json"]
    assert sent["title"] == "Test Article"
    assert sent["editor"] == "code"
    assert sent["world"] == {"id": "world-uuid-789"}
    assert sent["category"] == {"id": "c1"}
    assert sent["templateType"] == "person"


@patch("scripts.wa_client.requests.put")
def test_create_article_raises_wa_api_error_on_422(mock_put):
    mock_put.return_value = _mock_response(422, {"success": False, "error": "Invalid templateType"})
    with pytest.raises(wa_client.WAApiError) as exc_info:
        wa_client.create_article(CREDS, {"title": "T", "content": "C", "templateType": "not-a-type"})
    assert exc_info.value.status_code == 422


@patch("scripts.wa_client.requests.patch")
def test_patch_article(mock_patch):
    mock_patch.return_value = _mock_response(200, {"success": True, "id": "a1"})
    result = wa_client.patch_article(CREDS, "a1", {"isWip": False, "isDraft": False})
    assert result["id"] == "a1"
    assert mock_patch.call_args.kwargs["params"] == {"id": "a1"}


@patch("scripts.wa_client.requests.post")
def test_list_articles_paginates(mock_post):
    mock_post.side_effect = [
        _mock_response(200, {"success": True, "entities": [{"id": "a1", "title": "Foo"}]}),
        _mock_response(200, {"success": True, "entities": []}),
    ]
    articles = wa_client.list_articles(CREDS)
    assert articles == [{"id": "a1", "title": "Foo"}]
