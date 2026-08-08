"""Tests for the list_category_articles CLI."""
from unittest.mock import patch

from scripts import list_category_articles

FAKE_CATEGORIES = [
    {"id": "c1", "title": "NPCs"},
    {"id": "c2", "title": "Places"},
]

FAKE_CATEGORY_DETAIL = {
    "id": "c1",
    "title": "NPCs",
    "articles": [
        {"id": "a1", "title": "Ármen", "url": "https://x/a1"},
        {"id": "a2", "title": "Velz", "url": "https://x/a2"},
    ],
}


@patch("scripts.list_category_articles.wa_client.get_category_articles")
@patch("scripts.list_category_articles.wa_client.list_categories")
@patch("scripts.list_category_articles.credentials.load_credentials")
def test_category_match_returns_stub_list(mock_load_creds, mock_list_cats, mock_get_cat_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    mock_get_cat_articles.return_value = FAKE_CATEGORY_DETAIL
    result = list_category_articles.resolve(category_target="npcs")
    assert result["success"] is True
    assert result["category"] == {"id": "c1", "title": "NPCs"}
    assert result["articles"] == [
        {"id": "a1", "title": "Ármen", "url": "https://x/a1"},
        {"id": "a2", "title": "Velz", "url": "https://x/a2"},
    ]


@patch("scripts.list_category_articles.wa_client.list_categories")
@patch("scripts.list_category_articles.credentials.load_credentials")
def test_no_category_match(mock_load_creds, mock_list_cats):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    result = list_category_articles.resolve(category_target="Completely Unrelated")
    assert result["success"] is False
    assert "error" in result


@patch("scripts.list_category_articles.wa_client.get_category_articles")
@patch("scripts.list_category_articles.wa_client.list_categories")
@patch("scripts.list_category_articles.credentials.load_credentials")
def test_unexpected_response_shape_returns_raw(mock_load_creds, mock_list_cats, mock_get_cat_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_cats.return_value = FAKE_CATEGORIES
    mock_get_cat_articles.return_value = {"id": "c1", "title": "NPCs"}  # no "articles" key
    result = list_category_articles.resolve(category_target="NPCs")
    assert result["success"] is False
    assert result["error"] == "unexpected response shape"
    assert result["raw"] == {"id": "c1", "title": "NPCs"}


@patch("scripts.list_category_articles.credentials.load_credentials")
def test_no_credentials_reports_error(mock_load_creds):
    mock_load_creds.return_value = None
    result = list_category_articles.resolve(category_target="NPCs")
    assert result["success"] is False
    assert "error" in result


def test_missing_category_target_reports_error():
    result = list_category_articles.resolve(category_target=None)
    assert result["success"] is False
    assert "error" in result
