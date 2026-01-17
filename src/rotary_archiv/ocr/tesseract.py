"""
Tesseract OCR Implementation
"""

from pathlib import Path
import time
from typing import Any

from pdf2image import convert_from_path
from PIL import Image
import pytesseract

from src.rotary_archiv.config import settings


class TesseractOCR:
    """Tesseract OCR Wrapper"""

    def __init__(self):
        """Initialisiere Tesseract OCR"""
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def extract_text(self, file_path: str, language: str = "deu+eng") -> dict[str, Any]:
        """
        Extrahiere Text aus Datei mit Tesseract

        Args:
            file_path: Pfad zur Datei
            language: Sprache (z.B. "deu+eng" für Deutsch+Englisch)

        Returns:
            Dict mit 'text', 'confidence', 'engine_version', 'confidence_details', 'processing_time_ms'
        """
        start_time = time.time()
        file_path_obj = Path(file_path)

        try:
            # Hole Tesseract-Version
            try:
                engine_version = pytesseract.get_tesseract_version()
            except Exception:
                engine_version = None

            if file_path_obj.suffix.lower() == ".pdf":
                # PDF zu Bilder konvertieren
                # Verwende benutzerdefinierten Poppler-Pfad falls konfiguriert
                convert_kwargs = {}
                if settings.poppler_path:
                    poppler_path = Path(settings.poppler_path)
                    if poppler_path.exists():
                        convert_kwargs["poppler_path"] = str(poppler_path)

                images = convert_from_path(str(file_path_obj), **convert_kwargs)
                texts = []
                confidences = []
                confidence_details_list = []

                for image in images:
                    text = pytesseract.image_to_string(image, lang=language)
                    data = pytesseract.image_to_data(
                        image, lang=language, output_type=pytesseract.Output.DICT
                    )

                    # Berechne durchschnittliche Confidence
                    confs = [int(conf) for conf in data["conf"] if conf != "-1"]
                    avg_conf = sum(confs) / len(confs) if confs else 0

                    # Detaillierte Confidence-Werte (pro Wort)
                    word_confidences = []
                    for i, word_conf in enumerate(data["conf"]):
                        if word_conf != "-1":
                            word_text = (
                                data.get("text", [""])[i]
                                if i < len(data.get("text", []))
                                else ""
                            )
                            if word_text.strip():
                                word_confidences.append(
                                    {
                                        "text": word_text,
                                        "confidence": int(word_conf)
                                        / 100.0,  # Normalisiere zu 0.0-1.0
                                        "left": data.get("left", [0])[i]
                                        if i < len(data.get("left", []))
                                        else 0,
                                        "top": data.get("top", [0])[i]
                                        if i < len(data.get("top", []))
                                        else 0,
                                    }
                                )

                    texts.append(text)
                    confidences.append(avg_conf)
                    confidence_details_list.append(word_confidences)

                full_text = "\n\n".join(texts)
                avg_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0
                ) / 100.0  # Normalisiere zu 0.0-1.0
                confidence_details = {
                    "per_page": confidence_details_list,
                    "average": avg_confidence,
                }

            else:
                # Bild-Datei direkt verarbeiten
                image = Image.open(file_path_obj)
                full_text = pytesseract.image_to_string(image, lang=language)
                data = pytesseract.image_to_data(
                    image, lang=language, output_type=pytesseract.Output.DICT
                )

                # Berechne durchschnittliche Confidence
                confs = [int(conf) for conf in data["conf"] if conf != "-1"]
                avg_confidence = sum(confs) / len(confs) if confs else 0

                # Detaillierte Confidence-Werte (pro Wort)
                word_confidences = []
                for i, word_conf in enumerate(data["conf"]):
                    if word_conf != "-1":
                        word_text = (
                            data.get("text", [""])[i]
                            if i < len(data.get("text", []))
                            else ""
                        )
                        if word_text.strip():
                            word_confidences.append(
                                {
                                    "text": word_text,
                                    "confidence": int(word_conf) / 100.0,
                                    "left": data.get("left", [0])[i]
                                    if i < len(data.get("left", []))
                                    else 0,
                                    "top": data.get("top", [0])[i]
                                    if i < len(data.get("top", []))
                                    else 0,
                                }
                            )

                avg_confidence = avg_confidence / 100.0  # Normalisiere zu 0.0-1.0
                confidence_details = {
                    "per_word": word_confidences,
                    "average": avg_confidence,
                }

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "engine": "tesseract",
                "engine_version": engine_version,
                "language": language,
                "confidence_details": confidence_details,
                "processing_time_ms": processing_time_ms,
            }

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "text": "",
                "confidence": 0,
                "engine": "tesseract",
                "error": str(e),
                "processing_time_ms": processing_time_ms,
            }
