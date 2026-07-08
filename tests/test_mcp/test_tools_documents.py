"""Tests for MCP Document Tools."""

from unittest.mock import MagicMock, patch

import pytest

from src.rotary_archiv.mcp.tools.documents import (
    delete_document,
    get_document_detail,
    get_document_units,
    list_documents_summary,
)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.id = 1
    doc.filename = "test.pdf"
    doc.status = "completed"
    doc.title = "Test Document"
    doc.description = "A test document"
    doc.created_at = "2024-01-01T00:00:00"
    doc.updated_at = "2024-01-02T00:00:00"
    return doc


class TestGetDocumentDetail:
    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_get_document_success(
        self, mock_session, mock_service, mock_db, mock_document
    ):
        mock_session.return_value = mock_db
        mock_service.get_document.return_value = mock_document

        result = get_document_detail(document_id=1)

        assert result["id"] == 1
        assert result["filename"] == "test.pdf"
        assert result["status"] == "completed"
        mock_service.get_document.assert_called_once_with(mock_db, 1)

    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_get_document_not_found(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_document.side_effect = Exception("Document not found")

        with pytest.raises(Exception, match="Document not found"):
            get_document_detail(document_id=999)

    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_db_session_closed_on_success(
        self, mock_session, mock_service, mock_db, mock_document
    ):
        mock_session.return_value = mock_db
        mock_service.get_document.return_value = mock_document

        get_document_detail(document_id=1)

        mock_db.close.assert_called_once()

    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_db_session_closed_on_error(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_document.side_effect = Exception("Error")

        with pytest.raises(Exception, match="Error"):
            get_document_detail(document_id=1)

        mock_db.close.assert_called_once()


class TestListDocumentsSummary:
    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_list_documents_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        doc1 = MagicMock()
        doc1.id = 1
        doc1.filename = "doc1.pdf"
        doc1.status = "completed"
        doc2 = MagicMock()
        doc2.id = 2
        doc2.filename = "doc2.pdf"
        doc2.status = "pending"
        mock_service.list_documents_summary.return_value = [doc1, doc2]

        result = list_documents_summary(limit=10, offset=0)

        assert result["total"] == 2
        assert len(result["documents"]) == 2
        assert result["documents"][0]["filename"] == "doc1.pdf"

    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_list_documents_empty(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.list_documents_summary.return_value = []

        result = list_documents_summary()

        assert result["total"] == 0
        assert result["documents"] == []


class TestGetDocumentUnits:
    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_get_units_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        unit = MagicMock()
        unit.id = 1
        unit.title = "Unit 1"
        mock_service.get_document_units.return_value = [unit]

        result = get_document_units(document_id=1)

        assert len(result["units"]) == 1
        assert result["units"][0]["title"] == "Unit 1"

    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_get_units_empty(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_document_units.return_value = []

        result = get_document_units(document_id=1)

        assert result["units"] == []


class TestDeleteDocument:
    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_delete_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.delete_document.return_value = None

        result = delete_document(document_id=1)

        assert result["success"] is True
        mock_service.delete_document.assert_called_once_with(mock_db, 1)

    @patch("src.rotary_archiv.mcp.tools.documents.document_service")
    @patch("src.rotary_archiv.mcp.tools.documents.SessionLocal")
    def test_delete_not_found(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.delete_document.side_effect = Exception("Document not found")

        with pytest.raises(Exception, match="Document not found"):
            delete_document(document_id=999)
