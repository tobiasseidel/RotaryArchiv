"""
OCR Pipeline: Parallel Tesseract + Ollama Vision, Vergleich und Korrektur
"""

import asyncio
from datetime import datetime
from typing import Any

from src.rotary_archiv.ocr.ollama_gpt import OllamaGPT
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from src.rotary_archiv.ocr.tesseract import TesseractOCR


class OCRPipeline:
    """OCR Pipeline mit paralleler Verarbeitung"""

    def __init__(self):
        """Initialisiere OCR Pipeline"""
        self.tesseract = TesseractOCR()
        self.ollama_vision = OllamaVisionOCR()
        self.ollama_gpt = OllamaGPT()

    async def process_document(
        self, file_path: str, language: str = "deu+eng", use_correction: bool = True
    ) -> dict[str, Any]:
        """
        Verarbeite Dokument mit OCR-Pipeline

        Args:
            file_path: Pfad zur Datei
            language: Sprache für Tesseract
            use_correction: Verwende GPT-Korrektur

        Returns:
            Dict mit OCR-Ergebnissen
        """
        # Parallele Ausführung von Tesseract und Ollama Vision
        tesseract_task = asyncio.to_thread(
            self.tesseract.extract_text, file_path, language
        )
        ollama_task = asyncio.to_thread(self.ollama_vision.extract_text, file_path)

        # Warte auf beide Ergebnisse
        tesseract_result, ollama_result = await asyncio.gather(
            tesseract_task, ollama_task, return_exceptions=True
        )

        # Fehlerbehandlung
        if isinstance(tesseract_result, Exception):
            tesseract_result = {
                "text": "",
                "confidence": 0,
                "engine": "tesseract",
                "error": str(tesseract_result),
            }

        if isinstance(ollama_result, Exception):
            ollama_result = {
                "text": "",
                "confidence": None,
                "engine": "ollama_vision",
                "error": str(ollama_result),
            }

        # Vergleich und Kombination
        tesseract_text = tesseract_result.get("text", "")
        ollama_text = ollama_result.get("text", "")

        if use_correction and tesseract_text and ollama_text:
            # GPT-basierte Kombination und Korrektur
            comparison_result = await asyncio.to_thread(
                self.ollama_gpt.compare_ocr_results, tesseract_text, ollama_text
            )
            final_text = comparison_result.get("combined_text", tesseract_text)
        elif tesseract_text:
            final_text = tesseract_text
        elif ollama_text:
            final_text = ollama_text
        else:
            final_text = ""

        # Optional: Zusätzliche GPT-Korrektur
        if use_correction and final_text:
            correction_result = await asyncio.to_thread(
                self.ollama_gpt.correct_ocr_errors, final_text
            )
            final_text = correction_result.get("corrected_text", final_text)

        return {
            "text": final_text,
            "tesseract": tesseract_result,
            "ollama_vision": ollama_result,
            "processed_at": datetime.now().isoformat(),
            "file_path": file_path,
        }

    def process_document_sync(
        self, file_path: str, language: str = "deu+eng", use_correction: bool = True
    ) -> dict[str, Any]:
        """
        Synchrone Version der Dokument-Verarbeitung

        Args:
            file_path: Pfad zur Datei
            language: Sprache für Tesseract
            use_correction: Verwende GPT-Korrektur

        Returns:
            Dict mit OCR-Ergebnissen
        """
        # Tesseract
        tesseract_result = self.tesseract.extract_text(file_path, language)
        tesseract_text = tesseract_result.get("text", "")

        # Ollama Vision
        ollama_result = self.ollama_vision.extract_text(file_path)
        ollama_text = ollama_result.get("text", "")

        # Vergleich und Kombination
        if use_correction and tesseract_text and ollama_text:
            comparison_result = self.ollama_gpt.compare_ocr_results(
                tesseract_text, ollama_text
            )
            final_text = comparison_result.get("combined_text", tesseract_text)
        elif tesseract_text:
            final_text = tesseract_text
        elif ollama_text:
            final_text = ollama_text
        else:
            final_text = ""

        # Optional: Zusätzliche GPT-Korrektur
        if use_correction and final_text:
            correction_result = self.ollama_gpt.correct_ocr_errors(final_text)
            final_text = correction_result.get("corrected_text", final_text)

        return {
            "text": final_text,
            "tesseract": tesseract_result,
            "ollama_vision": ollama_result,
            "processed_at": datetime.now().isoformat(),
            "file_path": file_path,
        }
