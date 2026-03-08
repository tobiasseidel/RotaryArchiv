"""
BBox OCR: OCR-Verarbeitung für einzelne Bounding Boxes
mit automatischer Verifikation durch mehrere OCR-Modelle
"""

import asyncio
from contextlib import suppress
import logging
from pathlib import Path
import tempfile
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from src.rotary_archiv.config import settings
from src.rotary_archiv.core.models import DocumentPage
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from src.rotary_archiv.ocr.tesseract_ocr import TesseractOCR
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.image_utils import crop_bbox_from_image, deskew_image
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalisiert Text für Vergleich (entfernt/normalisiert Leerzeichen)

    Args:
        text: Original-Text

    Returns:
        Normalisierter Text
    """
    # Entferne alle Leerzeichen (auch Tabs, Newlines, etc.)
    return "".join(text.split())


def compare_ocr_results(
    text1: str, text2: str, ignore_whitespace: bool = True
) -> dict[str, Any]:
    """
    Vergleicht zwei OCR-Ergebnisse

    Args:
        text1: Erster Text (z.B. von Ollama)
        text2: Zweiter Text (z.B. von Tesseract)
        ignore_whitespace: Leerzeichen-Unterschiede ignorieren

    Returns:
        {
            "match": True/False,
            "similarity": 0.95,  # 0-1
            "differences": [
                {"position": 5, "char1": "a", "char2": "o", "word": "Wort", "word_position": 0}
            ]
        }
    """
    if ignore_whitespace:
        normalized1 = normalize_text(text1)
        normalized2 = normalize_text(text2)
    else:
        normalized1 = text1
        normalized2 = text2

    # Exakter Match nach Normalisierung
    if normalized1 == normalized2:
        return {
            "match": True,
            "similarity": 1.0,
            "differences": [],
        }

    # Charakter-für-Charakter-Vergleich für Unterschiede
    differences = []
    min_len = min(len(normalized1), len(normalized2))
    max_len = max(len(normalized1), len(normalized2))

    # Vergleiche Zeichen für Zeichen
    for i in range(min_len):
        if normalized1[i] != normalized2[i]:
            # Finde Wort-Kontext
            word_start = max(0, i - 10)
            word_end = min(len(normalized1), i + 10)
            word_context = normalized1[word_start:word_end]

            differences.append(
                {
                    "position": i,
                    "char1": normalized1[i],
                    "char2": normalized2[i] if i < len(normalized2) else "",
                    "word_context": word_context,
                    "word_position": i - word_start,
                }
            )

    # Wenn ein Text länger ist, markiere zusätzliche Zeichen
    if len(normalized1) > len(normalized2):
        for i in range(len(normalized2), len(normalized1)):
            word_start = max(0, i - 10)
            word_end = min(len(normalized1), i + 10)
            word_context = normalized1[word_start:word_end]

            differences.append(
                {
                    "position": i,
                    "char1": normalized1[i],
                    "char2": "",
                    "word_context": word_context,
                    "word_position": i - word_start,
                }
            )
    elif len(normalized2) > len(normalized1):
        for i in range(len(normalized1), len(normalized2)):
            word_start = max(0, i - 10)
            word_end = min(len(normalized2), i + 10)
            word_context = normalized2[word_start:word_end]

            differences.append(
                {
                    "position": i,
                    "char1": "",
                    "char2": normalized2[i],
                    "word_context": word_context,
                    "word_position": i - word_start,
                }
            )

    # Berechne Ähnlichkeit (basierend auf gemeinsamen Zeichen)
    common_chars = min_len - len([d for d in differences if d["position"] < min_len])
    similarity = common_chars / max_len if max_len > 0 else 0.0

    return {
        "match": False,
        "similarity": similarity,
        "differences": differences,
    }


def box_text_matches_native(
    box_text: str,
    native_page_text: str,
    threshold: float = 0.95,
) -> bool:
    """
    Prüft, ob der Box-Text an irgendeiner Stelle im nativen Seitentext
    mit Ähnlichkeit >= threshold vorkommt (Sliding-Window).

    Args:
        box_text: Erkannter Text der Box (Ollama/Tesseract)
        native_page_text: Volltext der Seite aus PDF (ohne OCR)
        threshold: Mindest-Ähnlichkeit 0-1 (Standard 0.95)

    Returns:
        True wenn ein Fenster im nativen Text die Box mit >= threshold ähnelt.
    """
    if not box_text or not box_text.strip():
        return False
    if not native_page_text or not native_page_text.strip():
        return False
    box_norm = normalize_text(box_text)
    native_norm = normalize_text(native_page_text)
    if not box_norm:
        return False
    box_len = len(box_norm)
    if box_len > len(native_norm):
        return False
    lengths = [
        max(1, box_len - 1),
        box_len,
        min(len(native_norm), box_len + 1),
    ]
    lengths = list(dict.fromkeys(lengths))
    for start in range(0, len(native_norm) - min(lengths) + 1):
        for wlen in lengths:
            if start + wlen > len(native_norm):
                continue
            window = native_norm[start : start + wlen]
            result = compare_ocr_results(box_norm, window, ignore_whitespace=False)
            if result["similarity"] >= threshold:
                return True
    return False


async def process_bbox_ocr(
    db: Session,
    document_page_id: int,
    bbox_item: dict[str, Any],
    image_path: str | None = None,
    pdf_path: str | None = None,
    page_number: int | None = None,
    ocr_models: list[str] | None = None,
    bbox_index: int | None = None,
    native_page_text: str | None = None,
) -> dict[str, Any]:
    """
    Verarbeite OCR für einzelne Bounding Box

    Args:
        db: Datenbank-Session
        document_page_id: ID der DocumentPage
        bbox_item: BBox-Item aus bbox_data mit text, bbox_pixel, etc.
        image_path: Pfad zur Bilddatei (falls verfügbar)
        pdf_path: Pfad zur PDF-Datei (falls Bild nicht verfügbar)
        page_number: Seitenzahl (falls PDF verwendet wird)
        ocr_models: Liste der zu verwendenden OCR-Modelle
        native_page_text: Optionaler nativer Seitentext für Auto-Review (Ähnlichkeit >= 95%)

    Returns:
        {
            "tesseract": {"text": "...", "confidence": 0.95, "error": None} | None,
            "ollama_vision": {"text": "...", "confidence": 0.92, "error": None} | None,
            "auto_confirmed": True/False,
            "differences": [...]
        }
    """
    if ocr_models is None:
        ocr_models = ["tesseract", "ollama_vision"]

    results = {}
    temp_files = []

    try:
        # Hole BBox-Koordinaten
        bbox_pixel = bbox_item.get("bbox_pixel")
        if not bbox_pixel or len(bbox_pixel) != 4:
            return {
                "error": "Ungültige bbox_pixel-Koordinaten",
                "auto_confirmed": False,
            }

        # Wende den gleichen X-Skalierungsfaktor an wie in der Leaflet-Anzeige (0.7)
        # Dies korrigiert die X-Achsen-Ausrichtung für das Cropping
        bbox_pixel_adjusted = [
            int(bbox_pixel[0] * 0.7),  # x1
            bbox_pixel[1],  # y1 (unverändert)
            int(bbox_pixel[2] * 0.7),  # x2
            bbox_pixel[3],  # y2 (unverändert)
        ]

        logger.debug(
            f"BBox-Koordinaten angepasst: Original={bbox_pixel}, "
            f"Angepasst (X * 0.7)={bbox_pixel_adjusted}"
        )

        # Hole OCRResult um Bild-Dimensionen zu vergleichen (OLLAMA_VISION oder PDF_NATIVE)
        from src.rotary_archiv.utils.ocr_result_loading import (
            get_best_ocr_result_with_bbox_for_page,
        )

        ocr_result_ref = get_best_ocr_result_with_bbox_for_page(db, document_page_id)

        ocr_image_width = ocr_result_ref.image_width if ocr_result_ref else None
        ocr_image_height = ocr_result_ref.image_height if ocr_result_ref else None

        page = (
            db.query(DocumentPage).filter(DocumentPage.id == document_page_id).first()
        )

        logger.info(
            f"BBox OCR Start: Seite {document_page_id}, "
            f"bbox_pixel={bbox_pixel}, "
            f"BBox-Text: '{bbox_item.get('text', '')[:50]}', "
            f"OCR-Bild-Dimensionen (aus DB): {ocr_image_width}x{ocr_image_height}"
        )

        # Lade Bild (entweder direkt oder aus PDF extrahieren)
        if image_path:
            full_image_path = get_file_path(image_path)
            if not full_image_path.exists():
                return {
                    "error": f"Bilddatei nicht gefunden: {image_path}",
                    "auto_confirmed": False,
                }
            img = Image.open(full_image_path)
            if page is not None and page.deskew_angle is not None:
                img = deskew_image(img, page.deskew_angle)
            cropped_image = crop_bbox_from_image(img, bbox_pixel_adjusted)
        elif pdf_path and page_number:
            # Extrahiere Seite aus PDF
            full_pdf_path = get_file_path(pdf_path)
            if not full_pdf_path.exists():
                return {
                    "error": f"PDF-Datei nicht gefunden: {pdf_path}",
                    "auto_confirmed": False,
                }

            # Verwende das gleiche DPI wie beim ursprünglichen OCR
            # Standard-DPI aus Config (sollte mit OCR übereinstimmen)
            dpi = settings.pdf_extraction_dpi

            # Versuche DPI aus Bild-Dimensionen abzuleiten falls verfügbar
            if ocr_image_width and ocr_image_height:
                # Extrahiere mit Standard-DPI
                page_image = extract_page_as_image(
                    str(full_pdf_path), page_number, dpi=dpi
                )
                extracted_width, extracted_height = page_image.size

                # Toleranz für Dimensionen-Unterschiede (in Pixeln)
                # Kleine Unterschiede sind OK (Rundungsfehler, leicht unterschiedliche DPI)
                dimension_tolerance = 10  # Pixel

                width_diff = abs(extracted_width - ocr_image_width)
                height_diff = abs(extracted_height - ocr_image_height)

                # Wenn Dimensionen außerhalb der Toleranz liegen, versuche DPI anzupassen
                if (
                    width_diff > dimension_tolerance
                    or height_diff > dimension_tolerance
                ):
                    # Berechne geschätztes DPI basierend auf Verhältnis
                    width_ratio = (
                        ocr_image_width / extracted_width
                        if extracted_width > 0
                        else 1.0
                    )
                    height_ratio = (
                        ocr_image_height / extracted_height
                        if extracted_height > 0
                        else 1.0
                    )
                    estimated_dpi = int(dpi * ((width_ratio + height_ratio) / 2))

                    logger.info(
                        f"Bild-Dimensionen weichen ab (Toleranz: {dimension_tolerance}px): "
                        f"OCR-Bild: {ocr_image_width}x{ocr_image_height}, "
                        f"Extrahiertes Bild (DPI {dpi}): {extracted_width}x{extracted_height} "
                        f"(Diff: {width_diff}x{height_diff}). "
                        f"Versuche mit geschätztem DPI {estimated_dpi}..."
                    )

                    # Versuche mit geschätztem DPI
                    page_image = extract_page_as_image(
                        str(full_pdf_path), page_number, dpi=estimated_dpi
                    )
                    extracted_width, extracted_height = page_image.size

                    width_diff_after = abs(extracted_width - ocr_image_width)
                    height_diff_after = abs(extracted_height - ocr_image_height)

                    if (
                        width_diff_after > dimension_tolerance
                        or height_diff_after > dimension_tolerance
                    ):
                        logger.warning(
                            f"Bild-Dimensionen weichen auch nach DPI-Anpassung ab: "
                            f"OCR-Bild: {ocr_image_width}x{ocr_image_height}, "
                            f"Extrahiertes Bild (DPI {estimated_dpi}): {extracted_width}x{extracted_height} "
                            f"(Diff: {width_diff_after}x{height_diff_after}). "
                            f"BBox-Koordinaten sollten trotzdem funktionieren (Toleranz: {dimension_tolerance}px)."
                        )
                    else:
                        logger.debug(
                            f"Bild-Dimensionen nach DPI-Anpassung innerhalb Toleranz: "
                            f"{extracted_width}x{extracted_height} (Diff: {width_diff_after}x{height_diff_after})"
                        )
                else:
                    logger.debug(
                        f"Bild-Dimensionen innerhalb Toleranz: "
                        f"{extracted_width}x{extracted_height} (Diff: {width_diff}x{height_diff})"
                    )
            else:
                page_image = extract_page_as_image(
                    str(full_pdf_path), page_number, dpi=dpi
                )
                extracted_width, extracted_height = page_image.size

            logger.info(
                f"BBox OCR: Seite aus PDF extrahiert: {extracted_width}x{extracted_height} (DPI: {dpi}), "
                f"bbox_pixel (original)={bbox_pixel}, "
                f"bbox_pixel (angepasst, X*0.7)={bbox_pixel_adjusted}, "
                f"BBox-Bereich (angepasst): {abs(bbox_pixel_adjusted[2] - bbox_pixel_adjusted[0])}x{abs(bbox_pixel_adjusted[3] - bbox_pixel_adjusted[1])}, "
                f"OCR-Bild-Dimensionen: {ocr_image_width}x{ocr_image_height}"
            )
            if page is not None and page.deskew_angle is not None:
                page_image = deskew_image(page_image, page.deskew_angle)
            cropped_image = crop_bbox_from_image(page_image, bbox_pixel_adjusted)
        else:
            return {
                "error": "Weder image_path noch pdf_path+page_number angegeben",
                "auto_confirmed": False,
            }

        # Debug-Logging
        logger.info(
            f"BBox OCR für Seite {document_page_id}, BBox {bbox_item.get('text', '')[:30]}: "
            f"bbox_pixel (angepasst)={bbox_pixel_adjusted}, "
            f"Original-Bild: {page_image.size if 'page_image' in locals() else 'N/A'}, "
            f"Ausgeschnittenes Bild: {cropped_image.size}"
        )

        # Speichere ausgeschnittenes Bild temporär
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            cropped_image.save(temp_file.name, "PNG")
            temp_bbox_path = temp_file.name
            temp_files.append(temp_bbox_path)
            logger.debug(f"BBox-Crop gespeichert: {temp_bbox_path}")

        # Optional: Speichere auch in Debug-Verzeichnis für visuelle Prüfung
        debug_crop_path = None
        if settings.debug_save_bbox_crops:
            try:
                debug_dir = Path(settings.debug_bbox_crops_path)
                debug_dir.mkdir(
                    parents=True, exist_ok=True
                )  # Erstelle Ordner falls nicht vorhanden

                # Erstelle eindeutigen Dateinamen mit Timestamp
                import re
                import time

                timestamp = int(time.time())
                # Entferne alle ungültigen Windows-Dateinamen-Zeichen
                # Ungültig: < > : " / \ | ? *
                text = bbox_item.get("text", "unknown")[:20]
                safe_text = re.sub(r'[<>:"/\\|?*]', "_", text)
                safe_text = safe_text.replace(" ", "_")
                # Entferne auch Steuerzeichen und andere problematische Zeichen
                safe_text = "".join(
                    c for c in safe_text if c.isprintable() or c in ("_", "-", ".")
                )
                # Stelle sicher, dass der Name nicht leer ist
                if not safe_text or safe_text.strip() == "":
                    safe_text = "unknown"
                index_str = str(bbox_index) if bbox_index is not None else "x"
                debug_filename = f"page_{document_page_id}_bbox_{index_str}_{timestamp}_{safe_text}.png"
                debug_path = debug_dir / debug_filename
                cropped_image.save(debug_path)
                debug_crop_path = str(debug_path)
                logger.info(f"BBox-Crop für Debug gespeichert: {debug_path}")
            except Exception as e:
                logger.error(
                    f"Konnte BBox-Crop nicht im Debug-Verzeichnis speichern: {e}",
                    exc_info=True,
                )

        # Führe OCR mit verschiedenen Modellen durch
        if "tesseract" in ocr_models:
            tesseract_ocr = TesseractOCR()
            tesseract_result = tesseract_ocr.extract_text_from_image(temp_bbox_path)
            results["tesseract"] = tesseract_result

        if "ollama_vision" in ocr_models:
            ollama_ocr = OllamaVisionOCR()
            # Verwende extract_text (ohne BBox, da wir bereits ausgeschnitten haben)
            # extract_text ist synchron, daher verwenden wir to_thread
            try:
                ollama_result = await asyncio.to_thread(
                    ollama_ocr.extract_text, temp_bbox_path
                )
                if isinstance(ollama_result, Exception):
                    results["ollama_vision"] = {
                        "text": "",
                        "confidence": None,
                        "error": str(ollama_result),
                    }
                else:
                    results["ollama_vision"] = {
                        "text": ollama_result.get("text", ""),
                        "confidence": ollama_result.get("confidence"),
                        "error": ollama_result.get("error"),
                    }
            except Exception as e:
                results["ollama_vision"] = {
                    "text": "",
                    "confidence": None,
                    "error": str(e),
                }

        # Vergleiche Ergebnisse
        tesseract_text = results.get("tesseract", {}).get("text", "")
        ollama_text = results.get("ollama_vision", {}).get("text", "")

        comparison = None
        auto_confirmed = False

        if tesseract_text and ollama_text:
            comparison = compare_ocr_results(tesseract_text, ollama_text)
            # Automatische Bestätigung nur wenn beide identisch (nach Normalisierung)
            auto_confirmed = comparison["match"]

        # Zusätzlich: Auto-Bestätigung wenn Box-Text im nativen Seitentext mit >= 95% vorkommt
        final_text = (ollama_text or tesseract_text or "").strip()
        if (
            native_page_text
            and final_text
            and not auto_confirmed
            and box_text_matches_native(final_text, native_page_text, threshold=0.95)
        ):
            auto_confirmed = True

        return {
            "tesseract": results.get("tesseract"),
            "ollama_vision": results.get("ollama_vision"),
            "auto_confirmed": auto_confirmed,
            "differences": comparison["differences"] if comparison else [],
        }

    except asyncio.CancelledError:
        # Wird beim Shutdown abgebrochen - das ist normal, nicht als Fehler loggen
        logger.debug(
            f"BBox OCR für Seite {document_page_id} wurde abgebrochen (Shutdown)"
        )
        # Lösche temporäre Dateien auch bei Cancellation
        for temp_file in temp_files:
            with suppress(Exception):
                Path(temp_file).unlink()
        # Re-raise damit der Task korrekt abgebrochen wird
        raise
    except Exception as e:
        logger.error(
            f"Fehler bei BBox OCR für Seite {document_page_id}: {e}", exc_info=True
        )
        return {
            "error": str(e),
            "auto_confirmed": False,
        }
    finally:
        # Lösche temporäre Dateien
        for temp_file in temp_files:
            with suppress(Exception):
                Path(temp_file).unlink()
