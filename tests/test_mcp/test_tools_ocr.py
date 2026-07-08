"""Tests for MCP OCR Tools."""

from unittest.mock import MagicMock, patch

import pytest

from src.rotary_archiv.mcp.tools.ocr import (
    get_ocr_result_detail,
    get_ocr_results,
    get_queue_status,
    list_ocr_jobs,
)


@pytest.fixture
def mock_db():
    return MagicMock()


class TestGetOcrResults:
    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_results_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        result1 = MagicMock()
        result1.id = 1
        result1.engine = "tesseract"
        result1.confidence = 0.95
        mock_service.get_ocr_results.return_value = [result1]

        result = get_ocr_results(document_id=1)

        assert len(result["results"]) == 1
        assert result["results"][0]["engine"] == "tesseract"
        mock_service.get_ocr_results.assert_called_once_with(mock_db, 1)

    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_results_empty(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_ocr_results.return_value = []

        result = get_ocr_results(document_id=1)

        assert result["results"] == []

    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_results_db_closed(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_ocr_results.return_value = []

        get_ocr_results(document_id=1)

        mock_db.close.assert_called_once()


class TestGetOcrResultDetail:
    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_result_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        result1 = MagicMock()
        result1.id = 1
        result1.document_id = 1
        result1.engine = "tesseract"
        result1.confidence = 0.95
        result1.text_content = "OCR text here"
        mock_service.get_ocr_result.return_value = result1

        result = get_ocr_result_detail(document_id=1, result_id=1)

        assert result["id"] == 1
        assert result["text_content"] == "OCR text here"

    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_result_not_found(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_ocr_result.side_effect = Exception("OCR result not found")

        with pytest.raises(Exception, match="OCR result not found"):
            get_ocr_result_detail(document_id=1, result_id=999)


class TestGetQueueStatus:
    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_status_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_queue_status.return_value = {
            "pending": 5,
            "processing": 2,
            "completed": 100,
        }

        result = get_queue_status()

        assert result["pending"] == 5
        assert result["processing"] == 2

    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_get_status_with_type(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.get_queue_status.return_value = {"pending": 3}

        get_queue_status(job_type="ocr")

        mock_service.get_queue_status.assert_called_once_with(mock_db, "ocr")


class TestListOcrJobs:
    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_list_jobs_success(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        job = MagicMock()
        job.id = 1
        job.status = "pending"
        job.priority = 1
        mock_service.list_ocr_jobs.return_value = [job]

        result = list_ocr_jobs(limit=10, offset=0)

        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["status"] == "pending"

    @patch("src.rotary_archiv.mcp.tools.ocr.ocr_service")
    @patch("src.rotary_archiv.mcp.tools.ocr.SessionLocal")
    def test_list_jobs_empty(self, mock_session, mock_service, mock_db):
        mock_session.return_value = mock_db
        mock_service.list_ocr_jobs.return_value = []

        result = list_ocr_jobs()

        assert result["jobs"] == []
