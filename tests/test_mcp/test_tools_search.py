"""Tests for MCP Search Tools."""

from unittest.mock import MagicMock, patch

import pytest

from src.rotary_archiv.mcp.tools.search import (
    get_person_detail,
    list_persons,
    search_documents,
)


@pytest.fixture
def mock_db():
    return MagicMock()


class TestSearchDocuments:
    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_search_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.search.return_value = {
            "total": 1,
            "results": [{"id": 1, "title": "Test", "snippet": "Found"}],
        }

        result = search_documents(query="Rotary")

        assert result["total"] == 1
        assert len(result["results"]) == 1
        mock_service.search.assert_called_once_with(
            mock_db,
            query="Rotary",
            person_slug=None,
            year=None,
            category=None,
            limit=20,
        )

    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_search_with_filters(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.search.return_value = {"total": 0, "results": []}

        search_documents(
            query="test",
            person_slug="maxMustermann",
            year="1930",
            category="Protokoll",
            limit=5,
        )

        mock_service.search.assert_called_once_with(
            mock_db,
            query="test",
            person_slug="maxMustermann",
            year="1930",
            category="Protokoll",
            limit=5,
        )

    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_search_empty(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.search.return_value = {"total": 0, "results": []}

        result = search_documents(query="nonexistent")

        assert result["total"] == 0
        assert result["results"] == []


class TestListPersons:
    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_list_persons_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.list_persons.return_value = {
            "total": 2,
            "persons": [
                {"slug": "max-mustermann", "name": "Max Mustermann"},
                {"slug": "anna-schmidt", "name": "Anna Schmidt"},
            ],
        }

        result = list_persons(limit=10, offset=0)

        assert result["total"] == 2
        assert len(result["persons"]) == 2

    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_list_persons_empty(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.list_persons.return_value = {"total": 0, "persons": []}

        result = list_persons()

        assert result["total"] == 0


class TestGetPersonDetail:
    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_get_person_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_person.return_value = {
            "slug": "max-mustermann",
            "name": "Max Mustermann",
            "roles": ["Clubpräsident"],
            "documents": [],
        }

        result = get_person_detail(slug="max-mustermann")

        assert result["slug"] == "max-mustermann"
        assert result["name"] == "Max Mustermann"

    @patch("src.rotary_archiv.mcp.tools.search.search_service")
    @patch("src.rotary_archiv.mcp.tools.search.SessionLocal")
    def test_get_person_not_found(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_person.side_effect = Exception("Person not found")

        with pytest.raises(Exception, match="Person not found"):
            get_person_detail(slug="unknown")
