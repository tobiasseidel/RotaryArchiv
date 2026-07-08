"""
Tests für Documents API Endpoints
"""

import io
from unittest.mock import patch

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

    @patch("src.rotary_archiv.api.documents.document_service")
    def test_upload_document_success(self, mock_service):
        """Test: Erfolgreicher Dokument-Upload"""
        from datetime import datetime

        from src.rotary_archiv.core.models import Document, DocumentStatus

        mock_document = Document(
            id=1,
            filename="test.pdf",
            file_path="test/path/document.pdf",
            file_type="application/pdf",
            file_size=1024,
            status=DocumentStatus.UPLOADED,
        )
        mock_document.created_at = datetime.now()
        mock_document.updated_at = datetime.now()
        mock_service.create_document.return_value = mock_document

        # Upload Request
        file_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        response = client.post("/api/documents", files=files)

        # Prüfe Response
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "document_id" in data
