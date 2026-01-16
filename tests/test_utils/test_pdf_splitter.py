"""
Tests für PDF Splitter
"""

from pathlib import Path

from PyPDF2 import PdfWriter
import pytest

from src.rotary_archiv.utils.pdf_splitter import PDFSplitter


@pytest.fixture
def sample_pdf(tmp_path):
    """Erstelle eine Test-PDF mit mehreren Seiten"""
    pdf_path = tmp_path / "test.pdf"

    # Erstelle PDF mit 3 Seiten
    writer = PdfWriter()
    for i in range(3):
        writer.add_blank_page(width=200, height=200)
        # Füge Text hinzu (vereinfacht)
        writer.pages[i].mediabox.lower_left = (0, 0)
        writer.pages[i].mediabox.upper_right = (200, 200)

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return str(pdf_path)


@pytest.mark.unit
@pytest.mark.slow
class TestPDFSplitter:
    """Tests für PDF Splitter"""

    def test_get_page_count(self, sample_pdf):
        """Test: Seitenanzahl wird korrekt ermittelt"""
        splitter = PDFSplitter()
        count = splitter.get_page_count(sample_pdf)
        assert count == 3

    def test_get_page_count_nonexistent(self):
        """Test: Seitenanzahl für nicht-existente PDF"""
        splitter = PDFSplitter()
        with pytest.raises(Exception, match="Fehler beim Lesen der PDF"):
            splitter.get_page_count("nonexistent.pdf")

    def test_extract_pages_pdf_format(self, sample_pdf, tmp_path, monkeypatch):
        """Test: Seiten-Extraktion als PDF"""
        monkeypatch.setattr(
            "src.rotary_archiv.utils.pdf_splitter.settings.documents_path",
            str(tmp_path / "docs"),
        )

        splitter = PDFSplitter()
        pages_info = splitter.extract_pages(sample_pdf, output_format="pdf")

        assert len(pages_info) == 3
        assert all("page_number" in page for page in pages_info)
        assert all("file_path" in page for page in pages_info)
        assert all(page["file_type"] == "application/pdf" for page in pages_info)

        # Prüfe dass Dateien existieren
        for page_info in pages_info:
            file_path = Path(page_info["file_path"])
            if file_path.is_absolute():
                assert file_path.exists()
            else:
                assert (Path.cwd() / file_path).exists()

    @pytest.mark.skipif(
        not pytest.importorskip("pdf2image", reason="pdf2image nicht verfügbar"),
        reason="pdf2image benötigt für Image-Extraktion",
    )
    def test_extract_pages_image_format(self, sample_pdf, tmp_path, monkeypatch):
        """Test: Seiten-Extraktion als Bilder (benötigt pdf2image)"""
        monkeypatch.setattr(
            "src.rotary_archiv.utils.pdf_splitter.settings.documents_path",
            str(tmp_path / "docs"),
        )

        splitter = PDFSplitter()
        pages_info = splitter.extract_pages(sample_pdf, output_format="image")

        assert len(pages_info) == 3
        assert all("page_number" in page for page in pages_info)
        assert all("file_path" in page for page in pages_info)
        assert all(
            page["file_type"] in ["image/png", "image/jpeg"] for page in pages_info
        )
