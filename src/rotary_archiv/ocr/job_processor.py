"""
Background-Job-Processor für OCR-Verarbeitung
"""

from datetime import datetime
import json

from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    OCRJob,
    OCRJobStatus,
    OCRResult,
    OCRSource,
)
from src.rotary_archiv.ocr.bbox_ocr import process_bbox_ocr
from src.rotary_archiv.ocr.pipeline import OCRPipeline
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.quality_metrics import (
    compute_black_pixels_per_char,
    compute_coverage,
    compute_density,
)


async def process_ocr_job(job_id: int) -> None:
    """
    Verarbeite einen OCR-Job im Hintergrund

    Args:
        job_id: ID des OCR-Jobs
    """
    # Neue DB-Session für Background-Task
    db = SessionLocal()

    job = None
    document = None

    try:
        # Hole Job
        job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
        if not job:
            return

        # Hole Dokument
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Dokument nicht gefunden"
            db.commit()
            return

        # Update Job-Status
        job.status = OCRJobStatus.RUNNING
        job.started_at = datetime.now()
        job.progress = 0.0
        job.current_step = "Initialisierung"
        db.commit()

        # Prüfe ob es ein seitenweiser Job ist
        if job.document_page_id:
            # Seitenweiser OCR-Job
            page = (
                db.query(DocumentPage)
                .filter(DocumentPage.id == job.document_page_id)
                .first()
            )
            if not page:
                job.status = OCRJobStatus.FAILED
                job.error_message = "Seite nicht gefunden"
                db.commit()
                return

            # Update Job-Status
            job.status = OCRJobStatus.RUNNING
            job.started_at = datetime.now()
            job.progress = 0.0
            job.current_step = f"OCR für Seite {page.page_number}"
            db.commit()

            # Prüfe ob PDF existiert
            absolute_file_path = get_file_path(document.file_path)
            if not absolute_file_path.exists():
                raise FileNotFoundError(
                    f"PDF nicht gefunden: {absolute_file_path} (ursprünglicher Pfad: {document.file_path})"
                )

            # OCR Pipeline
            pipeline = OCRPipeline()

            # Verarbeite Seite
            job.current_step = f"OCR-Verarbeitung Seite {page.page_number}"
            job.progress = 10.0
            db.commit()

            await pipeline.process_page_from_pdf_with_db(
                db=db,
                document_id=job.document_id,
                document_page_id=job.document_page_id,
                pdf_path=document.file_path,
                page_number=page.page_number,
                language=job.language,
                use_correction=job.use_correction,
                extract_bbox=True,  # Aktiviere BBox-Extraktion für Seiten-Jobs
                deskew=False,  # TODO: aus job-Parameter oder API wenn vorhanden
            )

            # Abschluss
            # Prüfe ob Job während der Verarbeitung abgebrochen wurde
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                # Job wurde abgebrochen/archiviert, nicht überschreiben
                return

            job.current_step = f"Abgeschlossen - Seite {page.page_number}"
            job.progress = 100.0
            job.status = OCRJobStatus.COMPLETED
            job.completed_at = datetime.now()
            db.commit()
        else:
            # Gesamtes Dokument OCR (bestehende Logik)
            # Update Document-Status
            document.status = DocumentStatus.OCR_PENDING
            db.commit()

            # Prüfe ob Datei existiert und löse Pfad auf
            absolute_file_path = get_file_path(document.file_path)
            if not absolute_file_path.exists():
                raise FileNotFoundError(
                    f"Datei nicht gefunden: {absolute_file_path} (ursprünglicher Pfad: {document.file_path})"
                )

            # OCR Pipeline
            pipeline = OCRPipeline()

            # Schritt 3: Speichere Ergebnisse in DB (60% Fortschritt)
            job.current_step = "OCR-Verarbeitung"
            job.progress = 10.0
            db.commit()

            await pipeline.process_document_with_db(
                db=db,
                document_id=job.document_id,
                file_path=document.file_path,  # Pipeline löst Pfad intern auf
                language=job.language,
                use_correction=job.use_correction,
            )

            # Schritt 4: GPT-Korrektur (falls aktiviert) (80% Fortschritt)
            if job.use_correction:
                job.current_step = "GPT-Korrektur"
                job.progress = 70.0
                db.commit()
                # GPT-Korrektur wird bereits in process_document_with_db durchgeführt

            # Schritt 5: Abschluss (100% Fortschritt)
            # Prüfe ob Job während der Verarbeitung abgebrochen wurde
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                # Job wurde abgebrochen/archiviert, nicht überschreiben
                return

            job.current_step = "Abgeschlossen"
            job.progress = 100.0
            job.status = OCRJobStatus.COMPLETED
            job.completed_at = datetime.now()

            # Update Document-Status
            document.status = DocumentStatus.OCR_DONE
            db.commit()

    except Exception as e:
        # Fehlerbehandlung
        # Prüfe ob Job während der Verarbeitung abgebrochen wurde
        if job:
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                # Job wurde abgebrochen/archiviert, nicht überschreiben
                return

            job.status = OCRJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()

            # Rollback Document-Status
            if document:
                document.status = DocumentStatus.UPLOADED
            db.commit()

            # Log Fehler (könnte hier auch logging verwenden)
            print(f"OCR Job {job_id} fehlgeschlagen: {e}")

    finally:
        db.close()


async def process_bbox_review_job(job_id: int) -> None:
    """
    Verarbeite einen BBox-Review-Job im Hintergrund

    Verarbeitet alle Bounding Boxes einer Seite:
    - Schneidet jede BBox aus dem Original-Bild aus
    - Führt OCR mit Tesseract und Ollama durch
    - Vergleicht Ergebnisse
    - Aktualisiert bbox_data mit Review-Status

    Args:
        job_id: ID des Review-Jobs
    """
    db = SessionLocal()

    job = None
    document = None
    page = None

    try:
        # Hole Job
        job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
        if not job:
            return

        # Prüfe Job-Typ
        if job.job_type != "bbox_review":
            return

        # Prüfe ob document_page_id gesetzt ist
        if not job.document_page_id:
            job.status = OCRJobStatus.FAILED
            job.error_message = "document_page_id fehlt für Review-Job"
            db.commit()
            return

        # Hole Seite
        page = (
            db.query(DocumentPage)
            .filter(DocumentPage.id == job.document_page_id)
            .first()
        )
        if not page:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Seite nicht gefunden"
            db.commit()
            return

        # Hole Dokument
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Dokument nicht gefunden"
            db.commit()
            return

        # Update Job-Status
        job.status = OCRJobStatus.RUNNING
        job.started_at = datetime.now()
        job.progress = 0.0
        job.current_step = f"Review für Seite {page.page_number}"
        db.commit()

        # Hole OCRResult mit bbox_data für diese Seite
        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == job.document_page_id,
                OCRResult.source == OCRSource.OLLAMA_VISION,
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )

        if not ocr_result or not ocr_result.bbox_data:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Keine BBox-Daten für diese Seite gefunden"
            db.commit()
            return

        # Parse bbox_data (kann JSON-String oder Dict sein)
        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data

        if not isinstance(bbox_list, list) or len(bbox_list) == 0:
            job.status = OCRJobStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now()
            job.current_step = "Keine BBoxes zu verarbeiten"
            db.commit()
            return

        # Filtere ignorierte BBoxes heraus (diese müssen nicht gereviewt werden)
        bboxes_to_process = [
            (idx, bbox_item)
            for idx, bbox_item in enumerate(bbox_list)
            if bbox_item.get("review_status") != "ignored"
        ]

        if len(bboxes_to_process) == 0:
            job.status = OCRJobStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now()
            job.current_step = "Alle BBoxes sind ignoriert"
            db.commit()
            return

        # Berechne Fortschritt pro BBox
        total_bboxes = len(bboxes_to_process)
        progress_per_bbox = 100.0 / total_bboxes if total_bboxes > 0 else 0

        # Hole Bild-Pfad
        pdf_path = document.file_path
        page_number = page.page_number

        # Verarbeite jede BBox (nur nicht-ignorierte)
        updated_bboxes = bbox_list.copy()  # Behalte alle BBoxes, auch ignorierte
        for idx, bbox_item in bboxes_to_process:
            # Update Fortschritt
            job.progress = idx * progress_per_bbox
            job.current_step = f"Verarbeite BBox {idx + 1}/{total_bboxes}"
            db.commit()

            # Führe OCR für diese BBox durch
            ocr_results = await process_bbox_ocr(
                db=db,
                document_page_id=job.document_page_id,
                bbox_item=bbox_item,
                pdf_path=pdf_path,
                page_number=page_number,
                ocr_models=["tesseract", "ollama_vision"],
                bbox_index=idx,  # Für Debug-Dateinamen
            )

            # Aktualisiere BBox-Item mit Review-Daten (nur wenn nicht ignoriert)
            if updated_bboxes[idx].get("review_status") != "ignored":
                updated_bbox = updated_bboxes[idx].copy()

                if "error" in ocr_results:
                    updated_bbox["review_status"] = "pending"
                    updated_bbox["ocr_results"] = None
                    updated_bbox["differences"] = None
                else:
                    # Setze Review-Status basierend auf auto_confirmed
                    if ocr_results.get("auto_confirmed", False):
                        updated_bbox["review_status"] = "auto_confirmed"
                        updated_bbox["reviewed_at"] = datetime.now().isoformat()
                    else:
                        updated_bbox["review_status"] = "pending"

                    # Speichere OCR-Ergebnisse
                    updated_bbox["ocr_results"] = {
                        "tesseract": ocr_results.get("tesseract"),
                        "ollama_vision": ocr_results.get("ollama_vision"),
                    }

                    # Speichere Unterschiede
                    updated_bbox["differences"] = ocr_results.get("differences", [])

                updated_bboxes[idx] = updated_bbox

        # Aktualisiere OCRResult mit neuen BBox-Daten
        ocr_result.bbox_data = updated_bboxes
        db.commit()

        # Abschluss
        job.current_step = f"Abgeschlossen - {total_bboxes} BBoxes verarbeitet"
        job.progress = 100.0
        job.status = OCRJobStatus.COMPLETED
        job.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        # Fehlerbehandlung
        if job:
            # Prüfe ob Job während der Verarbeitung abgebrochen wurde
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                # Job wurde abgebrochen/archiviert, nicht überschreiben
                return

            job.status = OCRJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()

        # Log Fehler
        print(f"BBox Review Job {job_id} fehlgeschlagen: {e}")

    finally:
        db.close()


async def process_quality_job(job_id: int) -> None:
    """
    Verarbeite einen Quality-Job: Berechne Coverage- und Density-Metriken für eine Seite.

    Args:
        job_id: ID des Quality-Jobs
    """
    db = SessionLocal()
    job = None

    try:
        # Hole Job
        job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
        if not job:
            return

        if not job.document_page_id:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Quality-Job benötigt document_page_id"
            db.commit()
            return

        # Hole Seite
        page = (
            db.query(DocumentPage)
            .filter(DocumentPage.id == job.document_page_id)
            .first()
        )
        if not page:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Seite nicht gefunden"
            db.commit()
            return

        # Hole Dokument
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Dokument nicht gefunden"
            db.commit()
            return

        # Update Job-Status
        job.status = OCRJobStatus.RUNNING
        job.started_at = datetime.now()
        job.progress = 0.0
        job.current_step = f"Lade OCRResult für Seite {page.page_number}"
        db.commit()

        # Hole neuestes OCRResult mit bbox_data für diese Seite
        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == job.document_page_id,
                OCRResult.bbox_data.isnot(None),
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )

        if not ocr_result or not ocr_result.bbox_data:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Keine BBox-Daten für diese Seite gefunden"
            db.commit()
            return

        # Parse bbox_data
        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data

        if not isinstance(bbox_list, list):
            job.status = OCRJobStatus.FAILED
            job.error_message = "bbox_data ist keine Liste"
            db.commit()
            return

        job.progress = 20.0
        job.current_step = f"Lade Seitenbild für Seite {page.page_number}"
        db.commit()

        # Importiere Image am Anfang (außerhalb des try-Blocks)
        from PIL import Image

        from src.rotary_archiv.config import settings
        from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

        # Lade Seitenbild (ähnlich wie _load_page_as_pil, aber ohne HTTPException)
        try:
            if not page.file_path:
                # Virtuelle Seite: aus PDF extrahieren
                pdf_path = get_file_path(document.file_path)
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")
                img = extract_page_as_image(str(pdf_path), page.page_number, dpi=200)
            else:
                # Extrahierte Seite: Datei laden
                file_path = get_file_path(page.file_path)
                if not file_path.exists():
                    raise FileNotFoundError(f"Seiten-Datei nicht gefunden: {file_path}")

                is_img = (
                    page.file_type
                    and page.file_type.lower()
                    in ("image/png", "image/jpeg", "image/jpg")
                ) or str(file_path).lower().endswith((".png", ".jpg", ".jpeg"))

                if is_img:
                    img = Image.open(file_path).convert("RGB")
                else:
                    # PDF-Seite
                    from pdf2image import convert_from_path

                    convert_kwargs = {
                        "first_page": page.page_number,
                        "last_page": page.page_number,
                        "dpi": 200,
                    }
                    if settings.poppler_path:
                        from pathlib import Path

                        pp = Path(settings.poppler_path)
                        if pp.exists():
                            convert_kwargs["poppler_path"] = str(pp)
                    images = convert_from_path(str(file_path), **convert_kwargs)
                    if not images:
                        raise ValueError("PDF konnte nicht zu Bild konvertiert werden")
                    img = images[0]

            # Deskew anwenden falls gesetzt
            if page.deskew_angle is not None:
                from src.rotary_archiv.utils.image_utils import deskew_image

                img = deskew_image(img, page.deskew_angle)

            # Resize auf OCR-Bildgröße falls abweichend
            if (
                ocr_result.image_width
                and ocr_result.image_height
                and img.size
                != (
                    ocr_result.image_width,
                    ocr_result.image_height,
                )
            ):
                img = img.resize(
                    (ocr_result.image_width, ocr_result.image_height),
                    Image.Resampling.LANCZOS,
                )

        except Exception as e:
            job.status = OCRJobStatus.FAILED
            job.error_message = f"Fehler beim Laden des Seitenbilds: {e!s}"
            db.commit()
            return

        job.progress = 50.0
        job.current_step = "Berechne Coverage-Metrik"
        db.commit()

        # Berechne Coverage
        try:
            coverage_result = compute_coverage(
                img,
                bbox_list,
                image_width=ocr_result.image_width,
                image_height=ocr_result.image_height,
                dark_threshold=200,
            )
        except Exception as e:
            job.status = OCRJobStatus.FAILED
            job.error_message = f"Fehler bei Coverage-Berechnung: {e!s}"
            db.commit()
            return

        job.progress = 75.0
        job.current_step = "Berechne Density-Metrik"
        db.commit()

        # Berechne Density
        try:
            bbox_densities, density_summary = compute_density(bbox_list)
        except Exception as e:
            job.status = OCRJobStatus.FAILED
            job.error_message = f"Fehler bei Density-Berechnung: {e!s}"
            db.commit()
            return

        job.progress = 78.0
        job.current_step = "Berechne Schwarze-Pixel-pro-Zeichen-Metrik"
        db.commit()

        # Berechne Schwarze Pixel pro Zeichen (pro Box)
        try:
            bbox_black_per_char, black_per_char_summary = compute_black_pixels_per_char(
                img, bbox_list, dark_threshold=200
            )
        except Exception as e:
            job.status = OCRJobStatus.FAILED
            job.error_message = f"Fehler bei Black-Pixels-per-Char-Berechnung: {e!s}"
            db.commit()
            return

        job.progress = 90.0
        job.current_step = "Speichere Qualitätsmetriken"
        db.commit()

        # Speichere quality_metrics im OCRResult
        quality_metrics = {
            "page_id": page.id,
            "coverage": coverage_result,
            "density": {
                "bboxes": bbox_densities,
                "summary": density_summary,
            },
            "black_pixels_per_char": {
                "bboxes": bbox_black_per_char,
                "summary": black_per_char_summary,
            },
        }

        ocr_result.quality_metrics = quality_metrics
        db.commit()

        # Abschluss
        job.current_step = (
            f"Abgeschlossen - Qualitätsmetriken für Seite {page.page_number}"
        )
        job.progress = 100.0
        job.status = OCRJobStatus.COMPLETED
        job.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        # Fehlerbehandlung
        if job:
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                return

            job.status = OCRJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()

        print(f"Quality Job {job_id} fehlgeschlagen: {e}")

    finally:
        db.close()
