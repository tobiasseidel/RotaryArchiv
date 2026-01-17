"""
OCR Pipeline: Parallel Tesseract + Ollama Vision, Vergleich und Korrektur
"""

import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.rotary_archiv.core.models import OCRResult, OCRSource
from src.rotary_archiv.ocr.ollama_gpt import OllamaGPT
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from src.rotary_archiv.ocr.tesseract import TesseractOCR
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image


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
            file_path: Pfad zur Datei (relativ oder absolut)
            language: Sprache für Tesseract
            use_correction: Verwende GPT-Korrektur

        Returns:
            Dict mit OCR-Ergebnissen
        """
        # Löse Pfad auf (kann relativ oder absolut sein)
        absolute_file_path = get_file_path(file_path)

        # Prüfe ob Datei existiert
        if not absolute_file_path.exists():
            raise FileNotFoundError(
                f"Datei nicht gefunden: {absolute_file_path} (ursprünglicher Pfad: {file_path})"
            )

        # Verwende absoluten Pfad für OCR
        file_path_str = str(absolute_file_path)

        # Parallele Ausführung von Tesseract und Ollama Vision
        tesseract_task = asyncio.to_thread(
            self.tesseract.extract_text, file_path_str, language
        )
        ollama_task = asyncio.to_thread(self.ollama_vision.extract_text, file_path_str)

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

    async def process_page_from_pdf_with_db(
        self,
        db: Session,
        document_id: int,
        document_page_id: int,
        pdf_path: str,
        page_number: int,
        language: str = "deu+eng",
        use_correction: bool = True,
    ) -> list[OCRResult]:
        """
        Verarbeite eine einzelne Seite aus einem PDF mit OCR-Pipeline und speichere Ergebnisse in DB

        Args:
            db: Datenbank-Session
            document_id: ID des Dokuments
            document_page_id: ID der DocumentPage
            pdf_path: Pfad zur PDF-Datei (relativ oder absolut)
            page_number: Seitenzahl (1-basiert)
            language: Sprache für Tesseract
            use_correction: Verwende GPT-Korrektur

        Returns:
            Liste der erstellten OCRResult-Objekte
        """
        # Löse Pfad auf
        absolute_pdf_path = get_file_path(pdf_path)

        # Prüfe ob PDF existiert
        if not absolute_pdf_path.exists():
            raise FileNotFoundError(
                f"PDF nicht gefunden: {absolute_pdf_path} (ursprünglicher Pfad: {pdf_path})"
            )

        # Extrahiere Seite als Bild (im Speicher)
        page_image = extract_page_as_image(str(absolute_pdf_path), page_number)

        # Speichere temporär als Datei für OCR-Engines
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            page_image.save(temp_file.name, "PNG")
            temp_path = temp_file.name

        ocr_results = []

        try:
            # Parallele Ausführung von Tesseract und Ollama Vision
            tesseract_task = asyncio.to_thread(
                self.tesseract.extract_text, temp_path, language
            )
            ollama_task = asyncio.to_thread(self.ollama_vision.extract_text, temp_path)

            # Warte auf beide Ergebnisse
            tesseract_result, ollama_result = await asyncio.gather(
                tesseract_task, ollama_task, return_exceptions=True
            )

            # Fehlerbehandlung und OCRResult-Erstellung für Tesseract
            if isinstance(tesseract_result, Exception):
                tesseract_ocr_result = OCRResult(
                    document_id=document_id,
                    document_page_id=document_page_id,
                    source=OCRSource.TESSERACT,
                    text="",
                    confidence=0.0,
                    error_message=str(tesseract_result),
                    language=language,
                    processing_time_ms=0,
                )
            else:
                error_msg = tesseract_result.get("error")
                text = tesseract_result.get("text", "")

                if error_msg:
                    import logging

                    logging.warning(
                        f"Tesseract OCR Fehler für Seite {page_number} von Dokument {document_id}: {error_msg}"
                    )

                tesseract_ocr_result = OCRResult(
                    document_id=document_id,
                    document_page_id=document_page_id,
                    source=OCRSource.TESSERACT,
                    text=text,
                    confidence=tesseract_result.get("confidence"),
                    confidence_details=tesseract_result.get("confidence_details"),
                    engine_version=tesseract_result.get("engine_version"),
                    language=tesseract_result.get("language"),
                    processing_time_ms=tesseract_result.get("processing_time_ms"),
                    error_message=error_msg,
                )
            db.add(tesseract_ocr_result)
            ocr_results.append(tesseract_ocr_result)

            # Fehlerbehandlung und OCRResult-Erstellung für Ollama Vision
            if isinstance(ollama_result, Exception):
                ollama_ocr_result = OCRResult(
                    document_id=document_id,
                    document_page_id=document_page_id,
                    source=OCRSource.OLLAMA_VISION,
                    text="",
                    confidence=None,
                    error_message=str(ollama_result),
                    processing_time_ms=0,
                )
            else:
                error_msg = ollama_result.get("error")
                text = ollama_result.get("text", "")

                if error_msg:
                    import logging

                    logging.warning(
                        f"Ollama Vision OCR Fehler für Seite {page_number} von Dokument {document_id}: {error_msg}"
                    )

                ollama_ocr_result = OCRResult(
                    document_id=document_id,
                    document_page_id=document_page_id,
                    source=OCRSource.OLLAMA_VISION,
                    text=text,
                    confidence=ollama_result.get("confidence"),
                    engine_version=ollama_result.get("engine_version"),
                    language=None,
                    processing_time_ms=ollama_result.get("processing_time_ms"),
                    error_message=error_msg,
                )
            db.add(ollama_ocr_result)
            ocr_results.append(ollama_ocr_result)

            # Commit, damit die IDs verfügbar sind
            db.commit()
            db.refresh(tesseract_ocr_result)
            db.refresh(ollama_ocr_result)

            # Vergleich und Kombination mit GPT
            tesseract_text = (
                tesseract_result.get("text", "")
                if not isinstance(tesseract_result, Exception)
                else ""
            )
            ollama_text = (
                ollama_result.get("text", "")
                if not isinstance(ollama_result, Exception)
                else ""
            )

            gpt_ocr_result = None
            if use_correction and tesseract_text and ollama_text:
                # GPT-basierte Kombination und Korrektur
                comparison_result = await asyncio.to_thread(
                    self.ollama_gpt.compare_ocr_results, tesseract_text, ollama_text
                )
                combined_text = comparison_result.get("combined_text", tesseract_text)

                # Optional: Zusätzliche GPT-Korrektur
                if combined_text:
                    correction_result = await asyncio.to_thread(
                        self.ollama_gpt.correct_ocr_errors, combined_text
                    )
                    final_text = correction_result.get("corrected_text", combined_text)
                else:
                    final_text = combined_text

                # Erstelle OCRResult für GPT-kombiniertes Ergebnis
                gpt_ocr_result = OCRResult(
                    document_id=document_id,
                    document_page_id=document_page_id,
                    source=OCRSource.COMBINED,
                    text=final_text,
                    confidence=None,
                    engine_version=self.ollama_gpt.model,
                    language=language,
                    processing_time_ms=None,
                )
                db.add(gpt_ocr_result)
                ocr_results.append(gpt_ocr_result)
                db.commit()
                db.refresh(gpt_ocr_result)

            return ocr_results
        finally:
            # Lösche temporäre Datei
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception:
                pass

    async def process_document_with_db(
        self,
        db: Session,
        document_id: int,
        file_path: str,
        language: str = "deu+eng",
        use_correction: bool = True,
        document_page_id: int | None = None,
    ) -> list[OCRResult]:
        """
        Verarbeite Dokument mit OCR-Pipeline und speichere Ergebnisse in DB

        Args:
            db: Datenbank-Session
            document_id: ID des Dokuments
            file_path: Pfad zur Datei (relativ oder absolut)
            language: Sprache für Tesseract
            use_correction: Verwende GPT-Korrektur
            document_page_id: Optional: ID der DocumentPage für Seiten-spezifische OCR

        Returns:
            Liste der erstellten OCRResult-Objekte
        """
        # Löse Pfad auf (kann relativ oder absolut sein)
        absolute_file_path = get_file_path(file_path)

        # Prüfe ob Datei existiert
        if not absolute_file_path.exists():
            raise FileNotFoundError(
                f"Datei nicht gefunden: {absolute_file_path} (ursprünglicher Pfad: {file_path})"
            )

        # Verwende absoluten Pfad für OCR
        file_path_str = str(absolute_file_path)

        ocr_results = []

        # Parallele Ausführung von Tesseract und Ollama Vision
        tesseract_task = asyncio.to_thread(
            self.tesseract.extract_text, file_path_str, language
        )
        ollama_task = asyncio.to_thread(self.ollama_vision.extract_text, file_path_str)

        # Warte auf beide Ergebnisse
        tesseract_result, ollama_result = await asyncio.gather(
            tesseract_task, ollama_task, return_exceptions=True
        )

        # Fehlerbehandlung und OCRResult-Erstellung für Tesseract
        if isinstance(tesseract_result, Exception):
            tesseract_ocr_result = OCRResult(
                document_id=document_id,
                document_page_id=document_page_id,
                source=OCRSource.TESSERACT,
                text="",
                confidence=0.0,
                error_message=str(tesseract_result),
                language=language,
                processing_time_ms=0,
            )
        else:
            # Prüfe auf Fehler im Ergebnis-Dict
            error_msg = tesseract_result.get("error")
            text = tesseract_result.get("text", "")

            # Wenn Fehler vorhanden oder Text leer, logge es
            if error_msg:
                import logging

                logging.warning(
                    f"Tesseract OCR Fehler für Dokument {document_id}: {error_msg}"
                )

            tesseract_ocr_result = OCRResult(
                document_id=document_id,
                document_page_id=document_page_id,
                source=OCRSource.TESSERACT,
                text=text,
                confidence=tesseract_result.get("confidence"),
                confidence_details=tesseract_result.get("confidence_details"),
                engine_version=tesseract_result.get("engine_version"),
                language=tesseract_result.get("language"),
                processing_time_ms=tesseract_result.get("processing_time_ms"),
                error_message=error_msg,
            )
        db.add(tesseract_ocr_result)
        ocr_results.append(tesseract_ocr_result)

        # Fehlerbehandlung und OCRResult-Erstellung für Ollama Vision
        if isinstance(ollama_result, Exception):
            ollama_ocr_result = OCRResult(
                document_id=document_id,
                document_page_id=document_page_id,
                source=OCRSource.OLLAMA_VISION,
                text="",
                confidence=None,
                error_message=str(ollama_result),
                processing_time_ms=0,
            )
        else:
            # Prüfe auf Fehler im Ergebnis-Dict
            error_msg = ollama_result.get("error")
            text = ollama_result.get("text", "")

            # Wenn Fehler vorhanden oder Text leer, logge es
            if error_msg:
                import logging

                logging.warning(
                    f"Ollama Vision OCR Fehler für Dokument {document_id}: {error_msg}"
                )

            ollama_ocr_result = OCRResult(
                document_id=document_id,
                document_page_id=document_page_id,
                source=OCRSource.OLLAMA_VISION,
                text=text,
                confidence=ollama_result.get("confidence"),
                engine_version=ollama_result.get("engine_version"),
                language=None,
                processing_time_ms=ollama_result.get("processing_time_ms"),
                error_message=error_msg,
            )
        db.add(ollama_ocr_result)
        ocr_results.append(ollama_ocr_result)

        # Commit, damit die IDs verfügbar sind
        db.commit()
        db.refresh(tesseract_ocr_result)
        db.refresh(ollama_ocr_result)

        # Vergleich und Kombination mit GPT
        tesseract_text = (
            tesseract_result.get("text", "")
            if not isinstance(tesseract_result, Exception)
            else ""
        )
        ollama_text = (
            ollama_result.get("text", "")
            if not isinstance(ollama_result, Exception)
            else ""
        )

        gpt_ocr_result = None
        if use_correction and tesseract_text and ollama_text:
            # GPT-basierte Kombination und Korrektur
            comparison_result = await asyncio.to_thread(
                self.ollama_gpt.compare_ocr_results, tesseract_text, ollama_text
            )
            combined_text = comparison_result.get("combined_text", tesseract_text)

            # Optional: Zusätzliche GPT-Korrektur
            if combined_text:
                correction_result = await asyncio.to_thread(
                    self.ollama_gpt.correct_ocr_errors, combined_text
                )
                final_text = correction_result.get("corrected_text", combined_text)
            else:
                final_text = combined_text

            # Erstelle OCRResult für GPT-kombiniertes Ergebnis
            gpt_ocr_result = OCRResult(
                document_id=document_id,
                document_page_id=document_page_id,
                source=OCRSource.COMBINED,  # Oder GPT_CORRECTED, je nach Logik
                text=final_text,
                confidence=None,  # GPT gibt keine Confidence
                engine_version=self.ollama_gpt.model,
                language=language,
                processing_time_ms=None,  # Wird später berechnet wenn nötig
            )
            db.add(gpt_ocr_result)
            ocr_results.append(gpt_ocr_result)
            db.commit()
            db.refresh(gpt_ocr_result)

        return ocr_results

    def process_document_sync(
        self, file_path: str, language: str = "deu+eng", use_correction: bool = True
    ) -> dict[str, Any]:
        """
        Synchrone Version der Dokument-Verarbeitung

        Args:
            file_path: Pfad zur Datei (relativ oder absolut)
            language: Sprache für Tesseract
            use_correction: Verwende GPT-Korrektur

        Returns:
            Dict mit OCR-Ergebnissen
        """
        # Löse Pfad auf (kann relativ oder absolut sein)
        absolute_file_path = get_file_path(file_path)

        # Prüfe ob Datei existiert
        if not absolute_file_path.exists():
            raise FileNotFoundError(
                f"Datei nicht gefunden: {absolute_file_path} (ursprünglicher Pfad: {file_path})"
            )

        # Verwende absoluten Pfad für OCR
        file_path_str = str(absolute_file_path)

        # Tesseract
        tesseract_result = self.tesseract.extract_text(file_path_str, language)
        tesseract_text = tesseract_result.get("text", "")

        # Ollama Vision
        ollama_result = self.ollama_vision.extract_text(file_path_str)
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
