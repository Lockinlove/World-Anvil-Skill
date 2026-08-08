"""Tests for the get_article CLI."""
from unittest.mock import patch

from scripts import get_article

FAKE_ARTICLE = {
    "id": "a1",
    "title": "Session 12 Recap",
    "content": "Full markdown body",
    "templateType": "report",
    "tags": "recap,session12",
    "category": {"id": "c1", "title": "Recaps"},
    "url": "https://x/a1",
}

FAKE_WORLD_ARTICLES = [
    {"id": "a1", "title": "Session 12 Recap", "url": "https://x/a1"},
    {"id": "a2", "title": "Session 11 Recap", "url": "https://x/a2"},
]


@patch("scripts.get_article.wa_client.get_article")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_id(mock_load_creds, mock_get_article):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_get_article.return_value = FAKE_ARTICLE
    result = get_article.fetch({"id": "a1"})
    assert result["success"] is True
    assert result["content"] == "Full markdown body"
    mock_get_article.assert_called_once_with(
        {"application_key": "a", "auth_token": "t", "world_id": "w"}, "a1"
    )


@patch("scripts.get_article.wa_client.get_article")
@patch("scripts.get_article.wa_client.list_articles")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_title_worldwide(mock_load_creds, mock_list_articles, mock_get_article):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_WORLD_ARTICLES
    mock_get_article.return_value = FAKE_ARTICLE
    result = get_article.fetch({"title": "Session 12 Recap"})
    assert result["success"] is True
    assert result["id"] == "a1"
    mock_get_article.assert_called_once_with(
        {"application_key": "a", "auth_token": "t", "world_id": "w"}, "a1"
    )


@patch("scripts.get_article.wa_client.get_article")
@patch("scripts.get_article.list_category_articles.resolve")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_title_scoped_to_category(mock_load_creds, mock_resolve, mock_get_article):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_resolve.return_value = {
        "success": True,
        "category": {"id": "c1", "title": "Recaps"},
        "articles": FAKE_WORLD_ARTICLES,
    }
    mock_get_article.return_value = FAKE_ARTICLE
    result = get_article.fetch({"title": "Session 12 Recap", "category": "Recaps"})
    assert result["success"] is True
    assert result["id"] == "a1"
    mock_resolve.assert_called_once_with("Recaps")


@patch("scripts.get_article.list_category_articles.resolve")
@patch("scripts.get_article.credentials.load_credentials")
def test_fetch_by_title_scoped_to_category_not_found(mock_load_creds, mock_resolve):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_resolve.return_value = {"success": False, "error": "No category matches 'Bogus'."}
    result = get_article.fetch({"title": "Anything", "category": "Bogus"})
    assert result["success"] is False
    assert result["error"] == "No category matches 'Bogus'."


@patch("scripts.get_article.wa_client.list_articles")
@patch("scripts.get_article.credentials.load_credentials")
def test_no_match_by_title(mock_load_creds, mock_list_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_WORLD_ARTICLES
    result = get_article.fetch({"title": "Totally Unrelated Title"})
    assert result["success"] is False
    assert "error" in result


def test_no_id_or_title_reports_error():
    result = get_article.fetch({})
    assert result["success"] is False
    assert "error" in result


@patch("scripts.get_article.credentials.load_credentials")
def test_no_credentials_reports_error(mock_load_creds):
    mock_load_creds.return_value = None
    result = get_article.fetch({"id": "a1"})
    assert result["success"] is False
    assert "error" in result
