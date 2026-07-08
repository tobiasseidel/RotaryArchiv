"""Tests für Search Service - strenger TDD Ansatz."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    DocumentUnit,
)
from src.rotary_archiv.services.search_service import (
    DocumentNotFoundError,
    PersonNotFoundError,
    SearchServiceError,
    get_document,
    get_person,
    list_documents,
    list_persons,
    search,
)


@pytest.mark.unit
class TestSearchServiceExceptions:
    """Exception-Hierarchie."""

    def test_search_service_error_is_exception(self):
        assert issubclass(SearchServiceError, Exception)

    def test_person_not_found_error(self):
        exc = PersonNotFoundError("max-mustermann")
        assert exc.slug == "max-mustermann"
        assert issubclass(PersonNotFoundError, SearchServiceError)

    def test_document_not_found_error(self):
        exc = DocumentNotFoundError(42)
        assert exc.unit_id == 42
        assert issubclass(DocumentNotFoundError, SearchServiceError)


@pytest.mark.unit
class TestSearch:
    """Tests für search()."""

    def test_search_empty(self, db_session):
        """Keine Treffer bei leerer DB."""
        results = search(db_session, "anything")
        assert results == []

    def test_search_by_title(self, db_session):
        """Suche nach Dokument-Titel liefert Treffer."""
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
            title="Rotary Club Versammlung",
            is_public=True,
            persons=[],
            date=datetime(1930, 6, 15),
        )
        db_session.add(unit)
        db_session.commit()

        results = search(db_session, "Rotary")
        assert len(results) >= 1
        assert any("Rotary" in r["display_name"] for r in results)

    def test_search_by_person(self, db_session):
        """Suche nach Personenname liefert Person + Dokument."""
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
            title="Protokoll",
            is_public=True,
            persons=[{"name": "Max Mustermann", "role": "Vorstand"}],
        )
        db_session.add(unit)
        db_session.commit()

        results = search(db_session, "Max Mustermann")
        person_results = [r for r in results if r["type"] == "person"]
        assert len(person_results) >= 1
        assert person_results[0]["display_name"] == "Max Mustermann"

    @patch("src.rotary_archiv.services.search_service.get_unit_text_in_reading_order")
    def test_search_by_ocr_text(self, mock_text, db_session):
        """Suche im OCR-Text liefert Treffer mit Snippet."""
        mock_text.return_value = "Dies ist ein langer Text über Rotary International."
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

        from src.rotary_archiv.core.models import OCRResult, OCRSource

        ocr_result = OCRResult(
            document_id=doc.id,
            document_page_id=page.id,
            source=OCRSource.TESSERACT,
            text="Dies ist ein Text über Rotary International.",
        )
        db_session.add(ocr_result)
        db_session.commit()

        unit = DocumentUnit(
            document_id=doc.id,
            page_ids=[page.id],
            is_public=True,
            persons=[],
        )
        db_session.add(unit)
        db_session.commit()

        results = search(db_session, "Rotary")
        doc_results = [r for r in results if r["type"] == "document"]
        assert len(doc_results) >= 1

    def test_search_with_epoch_filter(self, db_session):
        """Nur Treffer der angegebenen Epoche."""
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

        unit_30er = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            title="30er Dokument",
            is_public=True,
            persons=[],
            date=datetime(1932, 1, 1),
        )
        unit_90er = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            title="90er Dokument",
            is_public=True,
            persons=[],
            date=datetime(1995, 1, 1),
        )
        db_session.add_all([unit_30er, unit_90er])
        db_session.commit()

        results = search(db_session, "Dokument", epoch="30er")
        assert len(results) >= 1
        assert all(r["epoch"] == "30er" for r in results)


@pytest.mark.unit
class TestListPersons:
    """Tests für list_persons()."""

    def test_list_persons(self, db_session):
        """Aggregierte Personenliste aus public Units."""
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
            is_public=True,
            persons=[
                {"name": "Hans Schmidt", "role": "Präsident"},
                {"name": "Anna Müller", "role": "Sekretärin"},
            ],
            date=datetime(1932, 3, 1),
        )
        db_session.add(unit)
        db_session.commit()

        persons = list_persons(db_session)
        assert len(persons) == 2
        names = [p["display_name"] for p in persons]
        assert "Hans Schmidt" in names
        assert "Anna Müller" in names

    def test_list_persons_by_epoch(self, db_session):
        """Gefiltert nach Epoche."""
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

        unit_30er = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            is_public=True,
            persons=[{"name": "Hans 30er", "role": "Vorstand"}],
            date=datetime(1932, 1, 1),
        )
        unit_90er = DocumentUnit(
            document_id=doc.id,
            page_ids=[],
            is_public=True,
            persons=[{"name": "Hans 90er", "role": "Vorstand"}],
            date=datetime(1995, 1, 1),
        )
        db_session.add_all([unit_30er, unit_90er])
        db_session.commit()

        persons = list_persons(db_session, epoch="30er")
        assert len(persons) == 1
        assert persons[0]["display_name"] == "Hans 30er"


@pytest.mark.unit
class TestGetPerson:
    """Tests für get_person()."""

    def test_get_person_found(self, db_session):
        """Person mit Timeline wird gefunden."""
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
            is_public=True,
            persons=[{"name": "Max Mustermann", "role": "Präsident"}],
            date=datetime(1932, 6, 15),
            summary="Max Mustermann war Präsident des Rotary Clubs.",
        )
        db_session.add(unit)
        db_session.commit()

        person = get_person(db_session, "max-mustermann")
        assert person["display_name"] == "Max Mustermann"
        assert len(person["timeline"]) >= 1

    def test_get_person_not_found(self, db_session):
        """PersonNotFoundError bei unbekanntem Slug."""
        with pytest.raises(PersonNotFoundError):
            get_person(db_session, "nonexistent-person")


@pytest.mark.unit
class TestListDocuments:
    """Tests für list_documents() (Search-Service)."""

    def test_list_documents(self, db_session):
        """Öffentliche DocumentUnits nach Datum sortiert."""
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
            title="Test Dokument",
            is_public=True,
            persons=[],
            date=datetime(1932, 1, 1),
        )
        db_session.add(unit)
        db_session.commit()

        result = list_documents(db_session)
        assert len(result) == 1
        assert result[0]["title"] == "Test Dokument"


@pytest.mark.unit
class TestGetDocument:
    """Tests für get_document() (Search-Service)."""

    @patch("src.rotary_archiv.services.search_service.get_unit_text_in_reading_order")
    def test_get_document_found(self, mock_text, db_session):
        """Document-Detail mit Transkription + Pages."""
        mock_text.return_value = "Volltext der Seite"
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
            document_id=doc.id,
            page_number=1,
            file_path="/scans/1/1.png",
            file_type="image/png",
            is_extracted=True,
        )
        db_session.add(page)
        db_session.commit()
        db_session.refresh(page)

        unit = DocumentUnit(
            document_id=doc.id,
            page_ids=[page.id],
            title="Detail Dokument",
            is_public=True,
            persons=[{"name": "Hans", "role": "Vorstand"}],
            date=datetime(1932, 1, 1),
            summary="Zusammenfassung",
            topic="Rotary",
            place="Berlin",
        )
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)

        detail = get_document(db_session, unit.id)
        assert detail["id"] == unit.id
        assert detail["title"] == "Detail Dokument"
        assert detail["transcription"] == "Volltext der Seite"
        assert len(detail["pages"]) == 1
        assert detail["pages"][0]["image_url"] == "/scans/1/1.png"

    def test_get_document_not_found(self, db_session):
        """DocumentNotFoundError bei unbekannter unit_id."""
        with pytest.raises(DocumentNotFoundError):
            get_document(db_session, 99999)
