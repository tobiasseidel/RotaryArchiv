"""
Tests für PDF-Utils: extract_text_from_pdf_page und create_pdf_native_ocr_result_for_page
"""

from io import BytesIO

import pytest

from src.rotary_archiv.utils.pdf_utils import (
    create_pdf_native_ocr_result_for_page,
    extract_text_from_pdf_page,
)


@pytest.fixture
def pdf_with_text(tmp_path):
    """Erstelle eine minimale PDF mit extrahierbarem Text (Reportlab)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab nicht installiert")
    pdf_path = tmp_path / "with_text.pdf"
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 700, "Hello PDF Text")
    c.save()
    buffer.seek(0)
    pdf_path.write_bytes(buffer.getvalue())
    return str(pdf_path)


@pytest.fixture
def pdf_blank(tmp_path):
    """Erstelle eine PDF ohne Text (nur leere Seite)."""
    from PyPDF2 import PdfWriter

    pdf_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return str(pdf_path)


@pytest.mark.unit
class TestExtractTextFromPdfPage:
    """Tests für extract_text_from_pdf_page"""

    def test_nonexistent_returns_empty(self):
        """Nicht existierende Datei liefert leeren String."""
        assert extract_text_from_pdf_page("/nonexistent/file.pdf", 1) == ""

    def test_invalid_page_returns_empty(self, pdf_blank):
        """Ungültige Seitenzahl liefert leeren String."""
        assert extract_text_from_pdf_page(pdf_blank, 0) == ""
        assert extract_text_from_pdf_page(pdf_blank, 2) == ""

    def test_blank_page_returns_empty(self, pdf_blank):
        """PDF ohne Text liefert leeren String."""
        result = extract_text_from_pdf_page(pdf_blank, 1)
        assert result == "" or (result is not None and result.strip() == "")

    def test_pdf_with_text_returns_content(self, pdf_with_text):
        """PDF mit Text liefert extrahierten Text."""
        result = extract_text_from_pdf_page(pdf_with_text, 1)
        assert result is not None
        assert "Hello" in result or "PDF" in result or len(result.strip()) > 0


@pytest.mark.unit
class TestCreatePdfNativeOcrResultForPage:
    """Tests für create_pdf_native_ocr_result_for_page"""

    @pytest.fixture
    def db_session(self):
        """In-Memory-SQLite-Session mit allen Tabellen."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from src.rotary_archiv.core.database import Base
        from src.rotary_archiv.core.models import Document, DocumentPage, DocumentStatus

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        doc = Document(
            filename="test.pdf",
            file_path="test.pdf",
            file_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            is_composite=0,
        )
        session.add(doc)
        session.flush()
        page = DocumentPage(
            document_id=doc.id,
            page_number=1,
            file_type="pdf",
            is_extracted=False,
        )
        session.add(page)
        session.commit()
        session.refresh(doc)
        session.refresh(page)
        return session, doc.id, page.id

    def test_no_text_skips_creating_result(self, pdf_blank, db_session):
        """Bei Seite ohne Text wird kein OCRResult angelegt."""
        session, doc_id, page_id = db_session
        from src.rotary_archiv.core.models import OCRResult

        create_pdf_native_ocr_result_for_page(session, doc_id, page_id, pdf_blank, 1)
        session.commit()
        count = (
            session.query(OCRResult)
            .filter(OCRResult.document_page_id == page_id)
            .count()
        )
        assert count == 0

    def test_with_text_creates_one_result_with_box(
        self, pdf_with_text, db_session, monkeypatch
    ):
        """Bei Seite mit Text wird ein OCRResult (PDF_NATIVE) mit einer Box angelegt."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL nicht installiert")

        # Mock extract_page_as_image, damit kein Poppler nötig ist
        def fake_extract(path, page_number, dpi=200):
            return Image.new("RGB", (200, 300), color="white")

        monkeypatch.setattr(
            "src.rotary_archiv.utils.pdf_utils.extract_page_as_image",
            fake_extract,
        )

        session, doc_id, page_id = db_session
        from src.rotary_archiv.core.models import OCRResult, OCRSource

        create_pdf_native_ocr_result_for_page(
            session, doc_id, page_id, pdf_with_text, 1
        )
        session.commit()

        results = (
            session.query(OCRResult).filter(OCRResult.document_page_id == page_id).all()
        )
        assert len(results) == 1
        ocr = results[0]
        assert ocr.source == OCRSource.PDF_NATIVE
        assert ocr.text and len(ocr.text.strip()) > 0
        assert ocr.bbox_data is not None
        assert isinstance(ocr.bbox_data, list)
        assert len(ocr.bbox_data) == 1
        box = ocr.bbox_data[0]
        assert box.get("text") and len(box.get("text", "").strip()) > 0
        assert box.get("bbox") == [0.0, 0.0, 1.0, 1.0]
        assert box.get("bbox_pixel") == [0, 0, 200, 300]
        assert ocr.image_width == 200
        assert ocr.image_height == 300
