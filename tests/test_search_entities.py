"""Tests for the search_entities CLI (entity-linking lookup)."""
from unittest.mock import patch

from scripts import search_entities

FAKE_ARTICLES = [
    {"id": "a1", "title": "Ármen", "url": "https://x/a1"},
    {"id": "a2", "title": "Velz", "url": "https://x/a2"},
    {"id": "a3", "title": "Dead Gods", "url": "https://x/a3"},
]


@patch("scripts.search_entities.wa_client.list_articles")
@patch("scripts.search_entities.credentials.load_credentials")
def test_search_finds_matches_and_reports_unmatched(mock_load_creds, mock_list_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_ARTICLES
    result = search_entities.search(names=["Ármen", "Some Unrelated Name"])
    assert result["success"] is True
    assert result["matches"]["Ármen"] == {"id": "a1", "title": "Ármen", "url": "https://x/a1"}
    assert result["matches"]["Some Unrelated Name"] is None


@patch("scripts.search_entities.credentials.load_credentials")
def test_search_no_credentials(mock_load_creds):
    mock_load_creds.return_value = None
    result = search_entities.search(names=["Anything"])
    assert result["success"] is False
    assert "error" in result


@patch("scripts.search_entities.wa_client.list_articles")
@patch("scripts.search_entities.credentials.load_credentials")
def test_search_empty_names_returns_empty_matches(mock_load_creds, mock_list_articles):
    mock_load_creds.return_value = {"application_key": "a", "auth_token": "t", "world_id": "w"}
    mock_list_articles.return_value = FAKE_ARTICLES
    result = search_entities.search(names=[])
    assert result["success"] is True
    assert result["matches"] == {}
