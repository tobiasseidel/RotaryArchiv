"""
Tesseract OCR Wrapper für Text-Extraktion aus Bildern
"""

import logging
from pathlib import Path
import time

try:
    from PIL import Image
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    Image = None

from src.rotary_archiv.config import settings

logger = logging.getLogger(__name__)


class TesseractOCR:
    """Tesseract OCR Wrapper"""

    def __init__(self):
        """Initialisiere Tesseract OCR"""
        if not TESSERACT_AVAILABLE:
            logger.warning(
                "pytesseract oder PIL nicht verfügbar. Tesseract OCR wird nicht funktionieren."
            )
            return

        # Setze Tesseract-Pfad falls konfiguriert
        if settings.tesseract_cmd and settings.tesseract_cmd != "tesseract":
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def extract_text_from_image(
        self, image_path: str | Path, language: str = "deu+eng"
    ) -> dict:
        """
        Extrahiere Text aus Bild mit Tesseract OCR

        Args:
            image_path: Pfad zur Bilddatei
            language: Sprache für OCR (Standard: "deu+eng")

        Returns:
            Dict mit:
            - text: Extrahierter Text
            - confidence: Durchschnittliche Confidence (0-100)
            - processing_time_ms: Verarbeitungszeit in Millisekunden
            - error: Fehlermeldung (falls vorhanden)
        """
        if not TESSERACT_AVAILABLE:
            return {
                "text": "",
                "confidence": None,
                "processing_time_ms": 0,
                "error": "Tesseract OCR nicht verfügbar. Bitte pytesseract installieren.",
            }

        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            return {
                "text": "",
                "confidence": None,
                "processing_time_ms": 0,
                "error": f"Bilddatei nicht gefunden: {image_path}",
            }

        try:
            start_time = time.time()

            # Lade Bild
            image = Image.open(image_path_obj)

            # OCR mit Tesseract
            # Verwende --psm 6 für einheitlichen Textblock (gut für einzelne BBoxes)
            custom_config = r"--psm 6 -l " + language

            # Extrahiere Text
            text = pytesseract.image_to_string(image, config=custom_config)

            # Extrahiere Confidence-Daten
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

            # Berechne durchschnittliche Confidence
            confidences = [
                int(conf) for conf in data["conf"] if int(conf) > 0
            ]  # Ignoriere -1 (keine Confidence)
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else None
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "text": text.strip(),
                "confidence": avg_confidence / 100.0
                if avg_confidence
                else None,  # Normalisiere zu 0-1
                "processing_time_ms": processing_time_ms,
                "error": None,
            }

        except Exception as e:
            logger.error(
                f"Fehler bei Tesseract OCR für {image_path}: {e}", exc_info=True
            )
            return {
                "text": "",
                "confidence": None,
                "processing_time_ms": 0,
                "error": str(e),
            }

    def extract_text_from_image_object(
        self, image: Image.Image, language: str = "deu+eng"
    ) -> dict:
        """
        Extrahiere Text aus PIL Image-Objekt mit Tesseract OCR

        Args:
            image: PIL Image-Objekt
            language: Sprache für OCR (Standard: "deu+eng")

        Returns:
            Dict mit text, confidence, processing_time_ms, error
        """
        if not TESSERACT_AVAILABLE:
            return {
                "text": "",
                "confidence": None,
                "processing_time_ms": 0,
                "error": "Tesseract OCR nicht verfügbar. Bitte pytesseract installieren.",
            }

        try:
            start_time = time.time()

            # OCR mit Tesseract
            custom_config = r"--psm 6 -l " + language

            # Extrahiere Text
            text = pytesseract.image_to_string(image, config=custom_config)

            # Extrahiere Confidence-Daten
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

            # Berechne durchschnittliche Confidence
            confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else None
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "text": text.strip(),
                "confidence": avg_confidence / 100.0 if avg_confidence else None,
                "processing_time_ms": processing_time_ms,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Fehler bei Tesseract OCR: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": None,
                "processing_time_ms": 0,
                "error": str(e),
            }
