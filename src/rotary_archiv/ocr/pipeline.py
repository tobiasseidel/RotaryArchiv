"""
OCR Pipeline: Vereinfacht - nur Ollama Vision
"""

import asyncio
import os
import tempfile

from sqlalchemy.orm import Session

from src.rotary_archiv.core.bbox import save_bboxes
from src.rotary_archiv.core.models import DocumentPage, OCRResult, OCRSource
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.image_utils import deskew_image, detect_skew_angle
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image


class OCRPipeline:
    """OCR Pipeline mit Ollama Vision"""

    def __init__(self):
        """Initialisiere OCR Pipeline"""
        self.ollama_vision = OllamaVisionOCR()

    async def process_page_from_pdf_with_db(
        self,
        db: Session,
        document_id: int,
        document_page_id: int,
        pdf_path: str,
        page_number: int,
        language: str = "deu+eng",
        use_correction: bool = True,  # Wird ignoriert, für Kompatibilität behalten
        extract_bbox: bool = False,  # NEU: BBox-Extraktion aktivieren
        deskew: bool = False,  # Seite vor OCR begradigen (Drehpunkt: 0,0)
    ) -> list[OCRResult]:
        """
        Verarbeite eine einzelne Seite aus einem PDF mit OCR-Pipeline und speichere Ergebnisse in DB

        Args:
            db: Datenbank-Session
            document_id: ID des Dokuments
            document_page_id: ID der DocumentPage
            pdf_path: Pfad zur PDF-Datei (relativ oder absolut)
            page_number: Seitenzahl (1-basiert)
            language: Wird ignoriert (Ollama Vision erkennt Sprache automatisch)
            use_correction: Wird ignoriert (keine Korrektur mehr)

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

        # Optional: Deskew (Drehpunkt: obere linke Ecke 0,0)
        deskew_angle_applied: float | None = None
        if deskew:
            angle = detect_skew_angle(page_image)
            if abs(angle) > 0.1:
                page_image = deskew_image(page_image, angle)
                deskew_angle_applied = angle

        # Speichere temporär als Datei für OCR-Engine
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            page_image.save(temp_file.name, "PNG")
            temp_path = temp_file.name

        ocr_results = []

        try:
            # OCR mit Ollama Vision (mit oder ohne BBox)
            if extract_bbox:
                ollama_result = await asyncio.to_thread(
                    self.ollama_vision.extract_text_with_bbox, temp_path
                )
            else:
                ollama_result = await asyncio.to_thread(
                    self.ollama_vision.extract_text, temp_path
                )

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

                # BBox-Daten extrahieren und deskew_angle an jede Box (Drehpunkt 0,0)
                bbox_list = ollama_result.get("bbox_list")
                if bbox_list:
                    for item in bbox_list:
                        item["deskew_angle"] = deskew_angle_applied
                bbox_data = bbox_list if bbox_list else None

                # DocumentPage.deskew_angle setzen
                page = (
                    db.query(DocumentPage)
                    .filter(DocumentPage.id == document_page_id)
                    .first()
                )
                if page:
                    page.deskew_angle = deskew_angle_applied

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
                    # BBox-Felder
                    bbox_data=bbox_data,
                    image_width=ollama_result.get("image_width"),
                    image_height=ollama_result.get("image_height"),
                )
            db.add(ollama_ocr_result)
            ocr_results.append(ollama_ocr_result)

            # Commit, damit die IDs verfügbar sind
            db.commit()
            db.refresh(ollama_ocr_result)

            # In neue bboxes Tabelle schreiben
            if bbox_data:
                save_bboxes(ollama_ocr_result.id, bbox_data, db, update_bbox_data=False)
                db.commit()

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
        use_correction: bool = True,  # Wird ignoriert, für Kompatibilität behalten
        document_page_id: int | None = None,
        extract_bbox: bool = False,  # NEU: BBox-Extraktion aktivieren
    ) -> list[OCRResult]:
        """
        Verarbeite Dokument mit OCR-Pipeline und speichere Ergebnisse in DB

        Args:
            db: Datenbank-Session
            document_id: ID des Dokuments
            file_path: Pfad zur Datei (relativ oder absolut)
            language: Wird ignoriert (Ollama Vision erkennt Sprache automatisch)
            use_correction: Wird ignoriert (keine Korrektur mehr)
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

        # OCR mit Ollama Vision (mit oder ohne BBox)
        if extract_bbox:
            ollama_result = await asyncio.to_thread(
                self.ollama_vision.extract_text_with_bbox, file_path_str
            )
        else:
            ollama_result = await asyncio.to_thread(
                self.ollama_vision.extract_text, file_path_str
            )

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

            # BBox-Daten extrahieren (falls vorhanden)
            bbox_list = ollama_result.get("bbox_list")
            bbox_data = bbox_list if bbox_list else None

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
                # BBox-Felder
                bbox_data=bbox_data,
                image_width=ollama_result.get("image_width"),
                image_height=ollama_result.get("image_height"),
            )
        db.add(ollama_ocr_result)
        ocr_results.append(ollama_ocr_result)

        # Commit, damit die IDs verfügbar sind
        db.commit()
        db.refresh(ollama_ocr_result)

        # In neue bboxes Tabelle schreiben
        if bbox_data:
            save_bboxes(ollama_ocr_result.id, bbox_data, db, update_bbox_data=False)
            db.commit()

        return ocr_results
