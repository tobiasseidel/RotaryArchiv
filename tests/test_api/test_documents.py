"""
Tests für Documents API Endpoints
"""

import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from src.rotary_archiv.main import app

client = TestClient(app)


@pytest.mark.api
@pytest.mark.unit
class TestDocumentsAPI:
    """Tests für Documents API"""

    def test_list_documents_empty(self):
        """Test: Liste leerer Dokumente"""
        response = client.get("/api/documents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_upload_document_invalid(self):
        """Test: Upload ohne Datei schlägt fehl"""
        response = client.post("/api/documents")
        assert response.status_code == 422  # Validation Error

    def test_get_document_not_found(self):
        """Test: Abruf nicht-existenter Dokument-ID"""
        response = client.get("/api/documents/99999")
        assert response.status_code == 404

    def test_delete_document_not_found(self):
        """Test: Löschen nicht-existenter Dokument-ID"""
        response = client.delete("/api/documents/99999")
        assert response.status_code == 404

    @patch("src.rotary_archiv.api.documents.save_uploaded_file")
    @patch("src.rotary_archiv.api.documents.get_db")
    def test_upload_document_success(self, mock_db, mock_save_file):
        """Test: Erfolgreicher Dokument-Upload"""
        # Mock Setup
        mock_save_file.return_value = "test/path/document.pdf"
        mock_session = MagicMock()
        mock_document = MagicMock()
        mock_document.id = 1
        mock_document.filename = "test.pdf"
        mock_document.file_path = "test/path/document.pdf"
        mock_document.file_type = "application/pdf"
        mock_document.status = "uploaded"
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        mock_db.return_value.__enter__.return_value = mock_session
        mock_db.return_value.__exit__.return_value = None

        # Mock Document Model
        with patch("src.rotary_archiv.api.documents.Document") as mock_doc_model:
            mock_doc_model.return_value = mock_document

            # Upload Request
            file_content = b"fake pdf content"
            files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
            response = client.post("/api/documents", files=files)

            # Prüfe Response
            assert response.status_code in [200, 201]
            data = response.json()
            assert "id" in data or "document_id" in data
