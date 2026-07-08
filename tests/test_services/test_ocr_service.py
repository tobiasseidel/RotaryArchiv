"""Tests für OCR Service - strenger TDD Ansatz (Red -> Green -> Refactor)."""

from unittest.mock import MagicMock, patch

import pytest

from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    OCRJob,
    OCRJobStatus,
    OCRResult,
    OCRSource,
)
from src.rotary_archiv.services.ocr_service import (
    DocumentNotFoundError,
    InvalidActionError,
    InvalidJobStateError,
    JobConflictError,
    JobNotFoundError,
    OCRPipelineUnavailableError,
    OCRResultNotFoundError,
    OCRServiceError,
    batch_update_jobs,
    create_ocr_job,
    get_ocr_jobs,
    get_ocr_result,
    get_ocr_results,
    get_queue_status,
    list_ocr_jobs,
    prioritize_job,
    process_document,
)


@pytest.mark.unit
class TestOCRServiceExceptions:
    """Exception-Hierarchie des OCR Services."""

    def test_ocr_service_error_is_exception(self):
        assert issubclass(OCRServiceError, Exception)

    def test_document_not_found_error(self):
        exc = DocumentNotFoundError(42)
        assert exc.document_id == 42
        assert "42" in str(exc)
        assert issubclass(DocumentNotFoundError, OCRServiceError)

    def test_ocr_result_not_found_error(self):
        exc = OCRResultNotFoundError(1, 2)
        assert exc.document_id == 1
        assert exc.result_id == 2
        assert issubclass(OCRResultNotFoundError, OCRServiceError)

    def test_job_not_found_error(self):
        exc = JobNotFoundError(99)
        assert exc.job_id == 99
        assert issubclass(JobNotFoundError, OCRServiceError)

    def test_job_conflict_error(self):
        exc = JobConflictError(5)
        assert exc.existing_job_id == 5
        assert issubclass(JobConflictError, OCRServiceError)

    def test_invalid_job_state_error(self):
        InvalidJobStateError("running", "prioritize")
        assert issubclass(InvalidJobStateError, OCRServiceError)

    def test_invalid_action_error(self):
        InvalidActionError("explode")
        assert issubclass(InvalidActionError, OCRServiceError)

    def test_ocr_pipeline_unavailable_error(self):
        OCRPipelineUnavailableError()
        assert issubclass(OCRPipelineUnavailableError, OCRServiceError)


@pytest.mark.unit
class TestProcessDocument:
    """Tests für process_document()."""

    @patch("src.rotary_archiv.services.ocr_service.OCRPipeline")
    def test_process_document_success(self, mock_pipeline_cls, db_session):
        """OCR-Pipeline wird aufgerufen, Status wird aktualisiert."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        mock_pipeline.process_document_with_db = MagicMock(return_value=[])

        result = process_document(db_session, doc.id)

        assert isinstance(result, list)
        db_session.refresh(doc)
        assert doc.status == DocumentStatus.OCR_DONE

    def test_process_document_not_found(self, db_session):
        """DocumentNotFoundError bei unbekannter document_id."""
        with pytest.raises(DocumentNotFoundError):
            process_document(db_session, 99999)

    @patch("src.rotary_archiv.services.ocr_service.OCRPipeline", None)
    @patch("src.rotary_archiv.services.ocr_service.OCR_AVAILABLE", False)
    def test_process_document_pipeline_unavailable(self, db_session):
        """OCRPipelineUnavailableError wenn Pipeline nicht da."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        with pytest.raises(OCRPipelineUnavailableError):
            process_document(db_session, doc.id)


@pytest.mark.unit
class TestGetOCRResults:
    """Tests für get_ocr_results()."""

    def test_get_ocr_results_empty(self, db_session):
        """Leere Liste bei Dokument ohne Ergebnisse."""
        doc = Document(
            filename="empty.pdf",
            file_path="/uploads/empty.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        results = get_ocr_results(db_session, doc.id)
        assert results == []

    def test_get_ocr_results_found(self, db_session):
        """Alle Ergebnisse für Dokument werden zurückgegeben."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.OCR_DONE,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        result1 = OCRResult(
            document_id=doc.id,
            source=OCRSource.TESSERACT,
            text="Hallo Welt",
        )
        result2 = OCRResult(
            document_id=doc.id,
            source=OCRSource.OLLAMA_VISION,
            text="Hallo Welt OCR",
        )
        db_session.add_all([result1, result2])
        db_session.commit()

        results = get_ocr_results(db_session, doc.id)
        assert len(results) == 2

    def test_get_ocr_results_not_found(self, db_session):
        """DocumentNotFoundError bei unbekannter document_id."""
        with pytest.raises(DocumentNotFoundError):
            get_ocr_results(db_session, 99999)


@pytest.mark.unit
class TestGetOCRResult:
    """Tests für get_ocr_result()."""

    def test_get_ocr_result_found(self, db_session):
        """Einzelnes Ergebnis wird gefunden."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.OCR_DONE,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        result = OCRResult(
            id=1,
            document_id=doc.id,
            source=OCRSource.TESSERACT,
            text="Testtext",
        )
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        found = get_ocr_result(db_session, doc.id, result.id)
        assert found.id == result.id
        assert found.text == "Testtext"

    def test_get_ocr_result_not_found(self, db_session):
        """OCRResultNotFoundError bei unbekannter result_id."""
        with pytest.raises(OCRResultNotFoundError):
            get_ocr_result(db_session, 1, 99999)


@pytest.mark.unit
class TestCreateOCRJob:
    """Tests für create_ocr_job()."""

    @patch("src.rotary_archiv.services.ocr_service.OCRPipeline")
    def test_create_ocr_job_success(self, mock_pipeline_cls, db_session):
        """Job wird erstellt mit Status PENDING."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        from src.rotary_archiv.api.schemas import OCRJobCreate

        job_data = OCRJobCreate(
            job_type="ocr", language="deu+eng", use_correction=False
        )

        job = create_ocr_job(db_session, doc.id, job_data)
        assert job.status == OCRJobStatus.PENDING
        assert job.document_id == doc.id

    @patch("src.rotary_archiv.services.ocr_service.OCRPipeline")
    def test_create_ocr_job_duplicate(self, mock_pipeline_cls, db_session):
        """JobConflictError bei bereits aktivem Job."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        existing_job = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.PENDING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        db_session.add(existing_job)
        db_session.commit()

        from src.rotary_archiv.api.schemas import OCRJobCreate

        job_data = OCRJobCreate(job_type="ocr")

        with pytest.raises(JobConflictError):
            create_ocr_job(db_session, doc.id, job_data)


@pytest.mark.unit
class TestGetOCRJobs:
    """Tests für get_ocr_jobs()."""

    def test_get_ocr_jobs_with_type_filter(self, db_session):
        """Nur Jobs des angegebenen Typs."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job1 = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.PENDING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        job2 = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.PENDING,
            job_type="bbox_review",
            language="deu+eng",
            use_correction=False,
        )
        db_session.add_all([job1, job2])
        db_session.commit()

        ocr_jobs = get_ocr_jobs(db_session, doc.id, job_type="ocr")
        assert len(ocr_jobs) == 1
        assert ocr_jobs[0].job_type == "ocr"


@pytest.mark.unit
class TestPrioritizeJob:
    """Tests für prioritize_job()."""

    def test_prioritize_job_success(self, db_session):
        """Priorität wird auf Minimum - 1 gesetzt."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.PENDING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
            priority=0,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        updated = prioritize_job(db_session, job.id)
        assert updated.priority < 0

    def test_prioritize_job_wrong_status(self, db_session):
        """InvalidJobStateError bei nicht-PENDING Status."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.RUNNING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        with pytest.raises(InvalidJobStateError):
            prioritize_job(db_session, job.id)


@pytest.mark.unit
class TestListOCRJobs:
    """Tests für list_ocr_jobs()."""

    def test_list_ocr_jobs_with_status(self, db_session):
        """Nur Jobs mit angegebenem Status."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job1 = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.PENDING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        job2 = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.COMPLETED,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        db_session.add_all([job1, job2])
        db_session.commit()

        pending_jobs = list_ocr_jobs(db_session, status=OCRJobStatus.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].status == OCRJobStatus.PENDING


@pytest.mark.unit
class TestBatchUpdateJobs:
    """Tests für batch_update_jobs()."""

    def test_batch_update_cancel(self, db_session):
        """PENDING/RUNNING/PAUSED -> CANCELLED."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.PENDING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        result = batch_update_jobs(db_session, [job.id], "cancel")
        assert result["updated"] == 1
        db_session.refresh(job)
        assert job.status == OCRJobStatus.CANCELLED

    def test_batch_update_restart(self, db_session):
        """FAILED/CANCELLED -> PENDING (Reset)."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        job = OCRJob(
            document_id=doc.id,
            status=OCRJobStatus.FAILED,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
            error_message="Some error",
            progress=50.0,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        result = batch_update_jobs(db_session, [job.id], "restart")
        assert result["updated"] == 1
        db_session.refresh(job)
        assert job.status == OCRJobStatus.PENDING
        assert job.progress == 0.0
        assert job.error_message is None

    def test_batch_update_invalid_action(self, db_session):
        """InvalidActionError bei unbekannter Aktion."""
        with pytest.raises(InvalidActionError):
            batch_update_jobs(db_session, [1], "explode")


@pytest.mark.unit
class TestGetQueueStatus:
    """Tests für get_queue_status()."""

    def test_get_queue_status_empty(self, db_session):
        """Leere Response bei keine PDF-Dokumenten."""
        result = get_queue_status(db_session)
        assert result["documents"] == []

    def test_get_queue_status_with_jobs(self, db_session):
        """Dokumente mit Jobs und page_numbers."""
        doc = Document(
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.OCR_PENDING,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        page = DocumentPage(
            document_id=doc.id,
            page_number=1,
            file_type="pdf",
            is_extracted=False,
        )
        db_session.add(page)
        db_session.commit()
        db_session.refresh(page)

        job = OCRJob(
            document_id=doc.id,
            document_page_id=page.id,
            status=OCRJobStatus.PENDING,
            job_type="ocr",
            language="deu+eng",
            use_correction=False,
        )
        db_session.add(job)
        db_session.commit()

        result = get_queue_status(db_session)
        assert len(result["documents"]) >= 1
        doc_item = result["documents"][0]
        assert doc_item["id"] == doc.id
        assert len(doc_item["jobs"]) >= 1
