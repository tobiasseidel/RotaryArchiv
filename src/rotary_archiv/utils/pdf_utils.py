"""
PDF-Utilities für Seiten-Extraktion im Speicher (ohne Datei-Extraktion)
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyPDF2 import PdfReader

# Optional imports
try:
    from pdf2image import convert_from_path
    from PIL import Image

    PDF2IMAGE_AVAILABLE = True
    PIL_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    PIL_AVAILABLE = False

from src.rotary_archiv.config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_pdf_page_count(pdf_path: str | Path) -> int:
    """
    Ermittle die Anzahl der Seiten in einem PDF

    Args:
        pdf_path: Pfad zur PDF-Datei

    Returns:
        Anzahl der Seiten

    Raises:
        FileNotFoundError: Wenn PDF nicht gefunden wird
        Exception: Bei Fehlern beim Lesen der PDF
    """
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")

    try:
        reader = PdfReader(str(pdf_path_obj), strict=False)

        # Prüfe ob PDF verschlüsselt ist
        if reader.is_encrypted:
            try:
                reader.decrypt("")  # Versuche ohne Passwort
            except Exception as e:
                raise Exception(
                    "PDF ist verschlüsselt und benötigt ein Passwort"
                ) from e

        return len(reader.pages)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der PDF {pdf_path}: {e}")
        raise Exception(f"Fehler beim Lesen der PDF: {e}") from e


def extract_text_from_pdf_page(pdf_path: str | Path, page_number: int) -> str:
    """
    Lese Text von einer PDF-Seite ohne OCR (nur eingebettete Text-Objekte).

    Args:
        pdf_path: Pfad zur PDF-Datei
        page_number: Seitenzahl (1-basiert)

    Returns:
        Extrahierter Text oder leerer String wenn keine Text-Objekte oder bei Fehler.
    """
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        return ""
    try:
        reader = PdfReader(str(pdf_path_obj), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ""
        if page_number < 1 or page_number > len(reader.pages):
            return ""
        page = reader.pages[page_number - 1]
        text = page.extract_text()
        return (text or "").strip()
    except Exception as e:
        logger.debug(
            f"Native PDF-Text-Extraktion Seite {page_number} fehlgeschlagen: {e}"
        )
        return ""


def extract_page_as_image(
    pdf_path: str | Path, page_number: int, dpi: int = 200
) -> Image.Image:
    """
    Extrahiere eine einzelne Seite aus einem PDF als PIL Image (im Speicher)

    Args:
        pdf_path: Pfad zur PDF-Datei
        page_number: Seitenzahl (1-basiert)
        dpi: DPI für die Konvertierung (Standard: 200)

    Returns:
        PIL Image der Seite

    Raises:
        FileNotFoundError: Wenn PDF nicht gefunden wird
        ValueError: Wenn Seitenzahl ungültig ist
        ImportError: Wenn pdf2image nicht verfügbar ist
        Exception: Bei Fehlern bei der Konvertierung
    """
    if not PDF2IMAGE_AVAILABLE:
        raise ImportError(
            "pdf2image ist nicht installiert. Bitte installieren: pip install pdf2image"
        )

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")

    # Prüfe Seitenzahl
    total_pages = get_pdf_page_count(pdf_path)
    if page_number < 1 or page_number > total_pages:
        raise ValueError(
            f"Seitenzahl {page_number} ist ungültig. PDF hat {total_pages} Seiten."
        )

    try:
        # Verwende benutzerdefinierten Poppler-Pfad falls konfiguriert
        convert_kwargs = {
            "first_page": page_number,
            "last_page": page_number,
            "dpi": dpi,
        }
        if settings.poppler_path:
            poppler_path = Path(settings.poppler_path)
            if poppler_path.exists():
                convert_kwargs["poppler_path"] = str(poppler_path)

        images = convert_from_path(str(pdf_path_obj), **convert_kwargs)

        if not images:
            raise Exception(f"Konnte Seite {page_number} nicht konvertieren")

        return images[0]
    except Exception as e:
        logger.error(
            f"Fehler beim Extrahieren von Seite {page_number} aus {pdf_path}: {e}"
        )
        raise Exception(f"Fehler beim Extrahieren der Seite: {e}") from e


def create_page_thumbnail(
    image: Image.Image, size: tuple[int, int] = (200, 200)
) -> Image.Image:
    """
    Erstelle ein Thumbnail aus einem PIL Image

    Args:
        image: PIL Image
        size: Zielgröße als (width, height) Tupel (Standard: 200x200px)

    Returns:
        Thumbnail als PIL Image

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")

    # Erstelle Kopie um Original nicht zu verändern
    thumbnail = image.copy()
    thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
    return thumbnail


def create_pdf_native_ocr_result_for_page(
    db: "Session",
    document_id: int,
    document_page_id: int,
    pdf_path: str | Path,
    page_number: int,
) -> None:
    """
    Wenn auf der PDF-Seite Text ohne OCR auslesbar ist, ein OCRResult mit
    einer Vollseiten-Box (source=PDF_NATIVE) anlegen. Kein Commit - Caller
    übernimmt die Transaktion.
    """
    from src.rotary_archiv.core.models import OCRResult, OCRSource
    from src.rotary_archiv.utils.file_handler import get_file_path

    text = extract_text_from_pdf_page(pdf_path, page_number)
    if not text:
        return
    absolute_pdf_path = get_file_path(str(pdf_path))
    if not absolute_pdf_path.exists():
        logger.warning(f"PDF nicht gefunden für Native-Text: {absolute_pdf_path}")
        return
    try:
        page_image = extract_page_as_image(str(absolute_pdf_path), page_number, dpi=200)
    except Exception as e:
        logger.warning(
            f"Seitenbild für PDF-Native-Box nicht erzeugbar (Seite {page_number}): {e}"
        )
        return
    width, height = page_image.size
    bbox_item = {
        "text": text,
        "bbox": [0.0, 0.0, 1.0, 1.0],
        "bbox_pixel": [0, 0, width, height],
        "box_type": "ocr",
    }
    ocr_result = OCRResult(
        document_id=document_id,
        document_page_id=document_page_id,
        source=OCRSource.PDF_NATIVE,
        text=text,
        bbox_data=[bbox_item],
        image_width=width,
        image_height=height,
    )
    db.add(ocr_result)
