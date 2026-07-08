"""Tests für Document Service - strenger TDD Ansatz."""

from unittest.mock import MagicMock, patch

import pytest

from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    DocumentUnit,
    OCRJob,
)
from src.rotary_archiv.services.document_service import (
    DocumentNotFoundError,
    DocumentServiceError,
    InvalidPageError,
    create_document,
    create_document_unit,
    create_page_jobs,
    delete_document,
    delete_document_unit,
    get_composed_overview,
    get_document,
    get_document_units,
    get_unassigned_pages,
    list_documents,
    list_documents_summary,
    update_document_unit,
)


@pytest.mark.unit
class TestDocumentServiceExceptions:
    """Exception-Hierarchie."""

    def test_document_service_error_is_exception(self):
        assert issubclass(DocumentServiceError, Exception)

    def test_document_not_found_error(self):
        exc = DocumentNotFoundError(42)
        assert exc.document_id == 42
        assert "42" in str(exc)
        assert issubclass(DocumentNotFoundError, DocumentServiceError)

    def test_invalid_page_error(self):
        exc = InvalidPageError(1, 99)
        assert exc.document_id == 1
        assert exc.page_id == 99
        assert issubclass(InvalidPageError, DocumentServiceError)


@pytest.mark.unit
class TestCreateDocument:
    """Tests für create_document()."""

    @patch("src.rotary_archiv.services.document_service.save_uploaded_file")
    def test_create_document_image(self, mock_save_file, db_session):
        """Upload ohne PDF erstellt nur Document."""
        mock_save_file.return_value = "uploads/photo.jpg"

        doc = create_document(db_session, b"fake image data", "photo.jpg", "image/jpeg")

        assert doc.filename == "photo.jpg"
        assert doc.file_type == "image/jpeg"
        assert doc.status == DocumentStatus.UPLOADED

    @patch("src.rotary_archiv.services.document_service.save_uploaded_file")
    @patch("src.rotary_archiv.services.document_service.get_file_size")
    @patch("src.rotary_archiv.services.document_service.get_pdf_page_count")
    @patch("src.rotary_archiv.utils.file_handler.get_file_path")
    @patch(
        "src.rotary_archiv.services.document_service.create_pdf_native_ocr_result_for_page"
    )
    def test_create_document_pdf(
        self,
        mock_native_ocr,
        mock_get_path,
        mock_page_count,
        mock_file_size,
        mock_save_file,
        db_session,
    ):
        """Upload erstellt Document + virtuelle Pages + OCR-Jobs."""
        mock_save_file.return_value = "uploads/test.pdf"
        mock_file_size.return_value = 1024
        mock_get_path.return_value = MagicMock(exists=MagicMock(return_value=True))
        mock_page_count.return_value = 3
        mock_native_ocr.return_value = None

        doc = create_document(db_session, b"fake pdf", "test.pdf", "application/pdf")

        assert doc.filename == "test.pdf"
        pages = (
            db_session.query(DocumentPage)
            .filter(DocumentPage.document_id == doc.id)
            .all()
        )
        assert len(pages) == 3
        jobs = db_session.query(OCRJob).filter(OCRJob.document_id == doc.id).all()
        assert len(jobs) == 3

    def test_create_document_empty_file(self, db_session):
        """DocumentServiceError bei leerer Datei."""
        with pytest.raises(DocumentServiceError):
            create_document(db_session, b"", "empty.pdf", "application/pdf")


@pytest.mark.unit
class TestListDocuments:
    """Tests für list_documents()."""

    def test_list_documents_empty(self, db_session):
        """Leere Liste."""
        result = list_documents(db_session)
        assert result == []

    def test_list_documents_with_filter(self, db_session):
        """Nur Dokumente mit angegebenem Status."""
        doc1 = Document(
            filename="a.pdf",
            file_path="/a.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        doc2 = Document(
            filename="b.pdf",
            file_path="/b.pdf",
            file_type="application/pdf",
            status=DocumentStatus.OCR_DONE,
            is_composite=0,
        )
        db_session.add_all([doc1, doc2])
        db_session.commit()

        result = list_documents(db_session, status_filter=DocumentStatus.UPLOADED)
        assert len(result) == 1
        assert result[0].status == DocumentStatus.UPLOADED


@pytest.mark.unit
class TestListDocumentsSummary:
    """Tests für list_documents_summary()."""

    def test_list_documents_summary(self, db_session):
        """Leichte Liste (id, filename, title, status)."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            title="Test Doc",
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()

        result = list_documents_summary(db_session)
        assert len(result) == 1
        assert result[0]["filename"] == "test.pdf"
        assert result[0]["title"] == "Test Doc"


@pytest.mark.unit
class TestGetDocument:
    """Tests für get_document()."""

    def test_get_document_found(self, db_session):
        """Dokument wird gefunden."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        found = get_document(db_session, doc.id)
        assert found.id == doc.id

    def test_get_document_not_found(self, db_session):
        """DocumentNotFoundError bei unbekannter ID."""
        with pytest.raises(DocumentNotFoundError):
            get_document(db_session, 99999)


@pytest.mark.unit
class TestGetDocumentUnits:
    """Tests für get_document_units()."""

    def test_get_document_units(self, db_session):
        """Units werden zurückgegeben."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        unit = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            title="Test Unit",
        )
        db_session.add(unit)
        db_session.commit()

        units = get_document_units(db_session, doc.id)
        assert len(units) == 1
        assert units[0].title == "Test Unit"


@pytest.mark.unit
class TestGetUnassignedPages:
    """Tests für get_unassigned_pages()."""

    @patch("src.rotary_archiv.services.document_service.get_unit_text_in_reading_order")
    def test_get_unassigned_pages(self, mock_text, db_session):
        """Seiten ohne Unit-Zuordnung mit full_text."""
        mock_text.return_value = "Page text"
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        page1 = DocumentPage(
            document_id=doc.id, page_number=1, file_type="pdf", is_extracted=False
        )
        page2 = DocumentPage(
            document_id=doc.id, page_number=2, file_type="pdf", is_extracted=False
        )
        db_session.add_all([page1, page2])
        db_session.commit()
        db_session.refresh(page1)
        db_session.refresh(page2)

        unit = DocumentUnit(document_id=doc.id, page_ids=[page1.id])
        db_session.add(unit)
        db_session.commit()

        result = get_unassigned_pages(db_session, doc.id)
        assert len(result) == 1
        assert result[0]["page_id"] == page2.id


@pytest.mark.unit
class TestCreateDocumentUnit:
    """Tests für create_document_unit()."""

    def test_create_document_unit_success(self, db_session):
        """Unit wird erstellt."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        page = DocumentPage(
            document_id=doc.id, page_number=1, file_type="pdf", is_extracted=False
        )
        db_session.add(page)
        db_session.commit()
        db_session.refresh(page)

        from src.rotary_archiv.api.schemas import DocumentUnitCreate

        data = DocumentUnitCreate(page_ids=[page.id], title="New Unit")
        unit = create_document_unit(db_session, doc.id, data)
        assert unit.title == "New Unit"
        assert unit.page_ids == [page.id]

    def test_create_document_unit_invalid_page(self, db_session):
        """InvalidPageError bei fremder Seite."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        from src.rotary_archiv.api.schemas import DocumentUnitCreate

        data = DocumentUnitCreate(page_ids=[99999])
        with pytest.raises(InvalidPageError):
            create_document_unit(db_session, doc.id, data)


@pytest.mark.unit
class TestUpdateDocumentUnit:
    """Tests für update_document_unit()."""

    def test_update_document_unit(self, db_session):
        """Felder werden aktualisiert."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        unit = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            title="Old Title",
        )
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)

        from src.rotary_archiv.api.schemas import DocumentUnitUpdate

        data = DocumentUnitUpdate(title="New Title")
        updated = update_document_unit(db_session, doc.id, unit.id, data)
        assert updated.title == "New Title"


@pytest.mark.unit
class TestDeleteDocumentUnit:
    """Tests für delete_document_unit()."""

    def test_delete_document_unit(self, db_session):
        """Unit wird gelöscht."""
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        unit = DocumentUnit(document_id=doc.id, page_ids=[])
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)

        delete_document_unit(db_session, doc.id, unit.id)
        remaining = (
            db_session.query(DocumentUnit).filter(DocumentUnit.id == unit.id).all()
        )
        assert len(remaining) == 0


@pytest.mark.unit
class TestGetComposedOverview:
    """Tests für get_composed_overview()."""

    @patch("src.rotary_archiv.services.document_service.get_unit_text_in_reading_order")
    def test_get_composed_overview(self, mock_text, db_session):
        """Units mit Volltext (BBox Lesereihenfolge)."""
        mock_text.return_value = "Composed text"
        doc = Document(
            filename="test.pdf",
            file_path="/test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        unit = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            title="Overview Unit",
            persons=[{"name": "Hans", "role": "Vorstand"}],
        )
        db_session.add(unit)
        db_session.commit()

        result = get_composed_overview(db_session, doc.id)
        assert len(result) == 1
        assert result[0]["title"] == "Overview Unit"
        assert result[0]["full_text"] == "Composed text"


@pytest.mark.unit
class TestDeleteDocument:
    """Tests für delete_document()."""

    @patch("src.rotary_archiv.services.document_service.delete_file")
    def test_delete_document_cascade(self, mock_delete_file, db_session):
        """Pages + Files werden gelöscht."""
        mock_delete_file.return_value = None
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

        page = DocumentPage(
            document_id=doc.id,
            page_number=1,
            file_path="/uploads/test_1.png",
            file_type="image/png",
            is_extracted=True,
        )
        db_session.add(page)
        db_session.commit()

        delete_document(db_session, doc.id)

        remaining = db_session.query(Document).filter(Document.id == doc.id).all()
        assert len(remaining) == 0
        remaining_pages = (
            db_session.query(DocumentPage)
            .filter(DocumentPage.document_id == doc.id)
            .all()
        )
        assert len(remaining_pages) == 0

    def test_delete_document_not_found(self, db_session):
        """DocumentNotFoundError bei unbekannter ID."""
        with pytest.raises(DocumentNotFoundError):
            delete_document(db_session, 99999)


@pytest.mark.unit
class TestCreatePageJobs:
    """Tests für create_page_jobs()."""

    @patch("src.rotary_archiv.utils.file_handler.get_file_path")
    @patch("src.rotary_archiv.services.document_service.get_pdf_page_count")
    def test_create_page_jobs(self, mock_page_count, mock_get_path, db_session):
        """Fehlende Pages + Jobs werden erstellt."""
        mock_get_path.return_value = MagicMock(exists=MagicMock(return_value=True))
        mock_page_count.return_value = 2

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

        result = create_page_jobs(db_session, doc.id)
        assert result["total_pages"] == 2
        assert result["new_pages"] == 2
        assert result["new_jobs"] == 2
