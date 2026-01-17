"""
PDF-Utilities für Seiten-Extraktion im Speicher (ohne Datei-Extraktion)
"""

import logging
from pathlib import Path

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
