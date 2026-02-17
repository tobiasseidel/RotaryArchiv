"""
Background-Job-Processor für OCR-Verarbeitung
"""

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path

from sqlalchemy.orm.attributes import flag_modified

from src.rotary_archiv.api.settings import get_ocr_sight_settings_for_job
from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    DocumentUnit,
    OCRJob,
    OCRJobStatus,
    OCRResult,
    OCRSource,
)
from src.rotary_archiv.ocr.bbox_ocr import process_bbox_ocr
from src.rotary_archiv.ocr.content_analysis_llm import call_ollama_content_analysis
from src.rotary_archiv.ocr.llm_sight import (
    call_ollama_sight,
    should_auto_confirm,
)
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from src.rotary_archiv.ocr.pipeline import OCRPipeline
from src.rotary_archiv.utils.bbox_reading_order import (
    get_reading_order_indices,
    get_text_in_reading_order,
)
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.quality_metrics import (
    compute_black_pixels_per_char,
    compute_coverage,
    compute_density,
    compute_region_coverage_and_black_pixels,
)

logger = logging.getLogger(__name__)


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
                deskew=True,  # Seite vor OCR begradigen (gleiche Logik wie Unskew-Vorschau)
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

        # Verarbeite nur OCR-BBoxes mit review_status == "new" (z.B. nach "OCR verwerfen")
        # Ignorierte BBoxes sowie ignore_region- und note-Boxen überspringen
        bboxes_to_process = [
            (idx, bbox_item)
            for idx, bbox_item in enumerate(bbox_list)
            if bbox_item.get("review_status") == "new"
            and (
                bbox_item.get("box_type") is None or bbox_item.get("box_type") == "ocr"
            )
        ]

        if len(bboxes_to_process) == 0:
            job.status = OCRJobStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now()
            job.current_step = "Keine neuen BBoxes zu verarbeiten"
            db.commit()
            return

        # Berechne Fortschritt pro BBox
        total_bboxes = len(bboxes_to_process)
        progress_per_bbox = 100.0 / total_bboxes if total_bboxes > 0 else 0

        # Hole Bild-Pfad
        pdf_path = document.file_path
        page_number = page.page_number

        # Verarbeite jede BBox (nur "new" BBoxes)
        updated_bboxes = bbox_list.copy()  # Behalte alle BBoxes, auch ignorierte
        multibox_indices_to_remove = []  # Indizes von multibox_region Boxen, die entfernt werden sollen
        multibox_new_boxes_count = 0  # Anzahl der neuen Boxen aus Multibox-Regionen

        for processed_idx, (idx, bbox_item) in enumerate(bboxes_to_process):
            # Update Fortschritt (processed_idx ist der Index in der gefilterten Liste)
            job.progress = processed_idx * progress_per_bbox
            job.current_step = f"Verarbeite BBox {processed_idx + 1}/{total_bboxes}"
            db.commit()

            # Prüfe ob dies eine multibox_region Box ist (+X wieder aktiv für weiteren Versuch)
            if bbox_item.get("multibox_region") is True:
                is_persistent = bbox_item.get("persistent_multibox_region") is True
                # Spezielle Verarbeitung für Multibox-Regionen
                logger.debug(
                    f"Multibox-Region BBox {idx} auf Seite {job.document_page_id}"
                    + (" (persistent)" if is_persistent else "")
                )
                try:
                    new_bboxes = await process_multibox_region(
                        db=db,
                        document_page_id=job.document_page_id,
                        bbox_item=bbox_item,
                        ocr_result=ocr_result,
                        page=page,
                    )
                    if new_bboxes:
                        if not is_persistent:
                            multibox_indices_to_remove.append(idx)
                        else:
                            # Persistente Region: Box behalten, Status ocr_done setzen
                            updated_bboxes[idx] = updated_bboxes[idx].copy()
                            updated_bboxes[idx]["review_status"] = "ocr_done"
                            updated_bboxes[idx]["text"] = "[Region - OCR abgeschlossen]"
                            updated_bboxes[idx].pop("multibox_crop_path", None)
                            logger.info(
                                f"Persistente Multibox-Region {idx}: Box behalten, "
                                f"{len(new_bboxes)} Unterboxen hinzugefügt"
                            )
                        for new_bbox in new_bboxes:
                            updated_bboxes.append(new_bbox)
                        multibox_new_boxes_count += len(new_bboxes)
                        if not is_persistent:
                            logger.info(
                                f"Multibox-Region: {len(new_bboxes)} Boxen hinzugefügt"
                            )
                    else:
                        if not is_persistent:
                            multibox_indices_to_remove.append(idx)
                            logger.warning(
                                f"Multibox-Region {idx}: Keine Boxen erkannt, entferne temporäre Box"
                            )
                        else:
                            # Persistente Region: Box behalten, ocr_done (keine Unterboxen)
                            updated_bboxes[idx] = updated_bboxes[idx].copy()
                            updated_bboxes[idx]["review_status"] = "ocr_done"
                            updated_bboxes[idx][
                                "text"
                            ] = "[Region - keine Unterboxen erkannt]"
                            updated_bboxes[idx].pop("multibox_crop_path", None)
                            logger.warning(
                                f"Persistente Multibox-Region {idx}: Keine Boxen erkannt, Box bleibt"
                            )
                except Exception as e:
                    logger.error(
                        f"Fehler bei Multibox-Region-Verarbeitung für BBox {idx}: {e}",
                        exc_info=True,
                    )
                    if not is_persistent:
                        multibox_indices_to_remove.append(idx)
                    else:
                        # Persistente Region: Box behalten, Status pending (Fehler)
                        updated_bboxes[idx] = updated_bboxes[idx].copy()
                        updated_bboxes[idx]["review_status"] = "pending"
                        updated_bboxes[idx]["text"] = "[Region - Fehler bei Erkennung]"
                        updated_bboxes[idx].pop("multibox_crop_path", None)
                continue  # Überspringe normale OCR-Verarbeitung

            # Normale BBox-Verarbeitung
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

            # Aktualisiere BBox-Item mit Review-Daten (sollte "new" sein, da wir bereits gefiltert haben)
            if updated_bboxes[idx].get("review_status") == "new":
                updated_bbox = updated_bboxes[idx].copy()

                # Prüfe auf Fehler in OCR-Ergebnissen
                ollama_result = ocr_results.get("ollama_vision")
                tesseract_result = ocr_results.get("tesseract")

                logger.debug(
                    f"BBox {idx}: ollama={ollama_result is not None}, tesseract={tesseract_result is not None}"
                )

                # Prüfe auf Fehler: Ollama muss vorhanden sein und keinen Fehler haben
                has_error = (
                    not ollama_result
                    or (ollama_result and ollama_result.get("error"))
                    or (tesseract_result and tesseract_result.get("error"))
                )

                if has_error:
                    updated_bbox["review_status"] = "pending"
                    updated_bbox["ocr_results"] = None
                    updated_bbox["differences"] = None
                    updated_bbox["text"] = ""  # Leer bei Fehler
                    logger.warning(
                        f"OCR-Fehler für BBox {idx} auf Seite {job.document_page_id}: "
                        f"ollama_result={ollama_result is not None}, "
                        f"ollama_error={ollama_result.get('error') if ollama_result else 'None'}"
                    )
                else:
                    # Setze Text aus Ollama Vision (primärer OCR-Engine)
                    # Falls Ollama leer ist, verwende Tesseract als Fallback
                    ollama_text = (
                        ollama_result.get("text", "").strip() if ollama_result else ""
                    )
                    tesseract_text = (
                        tesseract_result.get("text", "").strip()
                        if tesseract_result
                        else ""
                    )

                    if ollama_text:
                        final_text = ollama_text
                        logger.info(
                            f"BBox {idx} Text von Ollama: '{final_text[:50]}...' (Länge: {len(final_text)})"
                        )
                    elif tesseract_text:
                        final_text = tesseract_text
                        logger.info(
                            f"BBox {idx} Text von Tesseract (Ollama war leer): '{final_text[:50]}...' (Länge: {len(final_text)})"
                        )
                    else:
                        final_text = ""
                        logger.warning(
                            f"BBox {idx} beide OCR-Engines haben leeren Text zurückgegeben"
                        )

                    updated_bbox["text"] = final_text

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
                logger.debug(
                    f"BBox {idx} aktualisiert, review_status={updated_bbox.get('review_status')}"
                )

        # Entferne temporäre multibox_region Boxen (in umgekehrter Reihenfolge, um Indizes stabil zu halten)
        if multibox_indices_to_remove:
            for idx in sorted(multibox_indices_to_remove, reverse=True):
                if idx < len(updated_bboxes):
                    updated_bboxes.pop(idx)
                    logger.debug(f"Multibox-Region Box {idx} entfernt")

        # Aktualisiere OCRResult mit neuen BBox-Daten
        ocr_result.bbox_data = updated_bboxes
        flag_modified(ocr_result, "bbox_data")
        logger.debug(
            f"Seite {job.document_page_id}: {len(updated_bboxes)} BBoxen, {multibox_new_boxes_count} aus Multibox"
        )
        db.commit()

        # Wenn neue Boxen aus Multibox-Regionen hinzugefügt wurden, erstelle einen neuen Review-Job
        # für diese Boxen (falls noch keiner existiert)
        if multibox_new_boxes_count > 0:
            from sqlalchemy import func

            existing_review_job = (
                db.query(OCRJob)
                .filter(
                    OCRJob.document_page_id == job.document_page_id,
                    OCRJob.job_type == "bbox_review",
                    OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
                )
                .first()
            )
            if not existing_review_job:
                min_priority = (
                    db.query(func.min(OCRJob.priority))
                    .filter(OCRJob.status == OCRJobStatus.PENDING)
                    .scalar()
                ) or 0
                new_review_job = OCRJob(
                    document_id=job.document_id,
                    document_page_id=job.document_page_id,
                    job_type="bbox_review",
                    status=OCRJobStatus.PENDING,
                    language="deu+eng",
                    use_correction=False,
                    priority=min_priority - 1,  # Höchste Priorität
                )
                db.add(new_review_job)
                db.commit()
                logger.debug(
                    f"Neuer Review-Job für {multibox_new_boxes_count} Boxen (ID: {new_review_job.id})"
                )

        # Abschluss
        job.current_step = f"Abgeschlossen - {total_bboxes} BBoxes verarbeitet"
        job.progress = 100.0
        job.status = OCRJobStatus.COMPLETED
        job.completed_at = datetime.now()
        db.commit()

        # Erstelle Quality-Job für diese Seite, um Metriken neu zu berechnen
        existing_quality_job = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_page_id == job.document_page_id,
                OCRJob.job_type == "quality",
                OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
            )
            .first()
        )
        if not existing_quality_job:
            quality_job = OCRJob(
                document_id=job.document_id,
                document_page_id=job.document_page_id,
                job_type="quality",
                status=OCRJobStatus.PENDING,
                language="deu+eng",
                use_correction=False,
                priority=0,
            )
            db.add(quality_job)
            db.commit()
            logger.info(
                f"Quality-Job für Seite {job.document_page_id} erstellt (Job-ID: {quality_job.id})"
            )

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

        # Log Fehler mit Details
        logger.error(
            f"BBox Review Job {job_id} fehlgeschlagen: {e}",
            exc_info=True,
        )

    finally:
        db.close()


async def process_llm_sight_job(job_id: int) -> None:
    """
    Verarbeite einen LLM-Sicht-Job: Für ausgewählte BBoxen einer Seite
    Metrik- und Text-Score berechnen, LLM aufrufen, bei ausreichendem Score
    auto_confirmed setzen und korrigierten Text speichern.
    """
    db = SessionLocal()
    job = None

    try:
        job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
        if not job:
            return
        if job.job_type != "llm_sight":
            job.status = OCRJobStatus.FAILED
            job.error_message = "Ungültiger Job-Typ (erwartet: llm_sight)"
            db.commit()
            return
        if not job.document_page_id:
            job.status = OCRJobStatus.FAILED
            job.error_message = "llm_sight-Job benötigt document_page_id"
            db.commit()
            return

        params = job.job_params or {}
        bbox_indices = params.get("bbox_indices")
        if not bbox_indices:
            job.status = OCRJobStatus.FAILED
            job.error_message = "llm_sight-Job benötigt job_params.bbox_indices"
            db.commit()
            return

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
            job.error_message = "Keine BBox-Daten für diese Seite"
            db.commit()
            return

        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = list(ocr_result.bbox_data)

        quality_metrics = ocr_result.quality_metrics or {}
        if isinstance(quality_metrics, str):
            quality_metrics = json.loads(quality_metrics)
        black_pc_bboxes = {
            b["index"]: b
            for b in (quality_metrics.get("black_pixels_per_char") or {}).get(
                "bboxes", []
            )
        }

        sight_settings = get_ocr_sight_settings_for_job(db)
        time_period = sight_settings.get("time_period") or ""
        language_style = sight_settings.get("language_style") or ""
        expected_names = sight_settings.get("expected_names") or ""
        typical_phrases = sight_settings.get("typical_phrases") or ""
        review_notes = sight_settings.get("review_notes") or ""
        sight_context = (
            sight_settings.get("sight_context") or "none"
        ).strip() or "none"
        black_pc_min = sight_settings.get("black_pc_min")
        black_pc_max = sight_settings.get("black_pc_max")
        score_threshold = sight_settings.get("score_threshold", 0.85)
        auto_sight_enabled = sight_settings.get("auto_sight_enabled", True)

        if black_pc_min is None:
            black_pc_min = 18.0
        if black_pc_max is None:
            black_pc_max = 35.0

        reading_order_indices = get_reading_order_indices(bbox_list)

        job.status = OCRJobStatus.RUNNING
        job.current_step = "LLM-Sichtung"
        db.commit()

        processed = 0
        auto_confirmed_count = 0
        for idx in bbox_indices:
            if idx < 0 or idx >= len(bbox_list):
                continue
            bbox = bbox_list[idx]
            text = (bbox.get("reviewed_text") or bbox.get("text") or "").strip()

            # OCR-Varianten aus ocr_results sammeln (Tesseract, Ollama Vision); Duplikate entfernen
            variants = None
            ocr_results = bbox.get("ocr_results") or {}
            for source in ("ollama_vision", "tesseract"):
                r = ocr_results.get(source)
                if r and isinstance(r, dict):
                    t = (r.get("text") or "").strip()
                    if t and (variants is None or t not in variants):
                        if variants is None:
                            variants = []
                        variants.append(t)
            if variants and len(variants) < 2:
                variants = None
            if not text and variants:
                text = variants[0]

            if not text:
                continue

            # Kontext (Nachbarboxen oder ganze Seite) in Lesereihenfolge
            context_before = ""
            context_after = ""
            if (
                sight_context in ("neighbours", "full_page")
                and idx in reading_order_indices
            ):
                pos = reading_order_indices.index(idx)
                # Nachbarboxen: zuerst 2 vorher/nachher; wenn Kontext < 100 Zeichen, auf 4 erweitern
                n_before = 2 if sight_context == "neighbours" else pos
                n_after = (
                    2
                    if sight_context == "neighbours"
                    else len(reading_order_indices) - pos - 1
                )
                before_indices = reading_order_indices[max(0, pos - n_before) : pos]
                after_indices = reading_order_indices[pos + 1 : pos + 1 + n_after]
                context_before = "\n".join(
                    (
                        bbox_list[i].get("reviewed_text")
                        or bbox_list[i].get("text")
                        or ""
                    ).strip()
                    for i in before_indices
                    if (
                        bbox_list[i].get("reviewed_text")
                        or bbox_list[i].get("text")
                        or ""
                    ).strip()
                )
                context_after = "\n".join(
                    (
                        bbox_list[i].get("reviewed_text")
                        or bbox_list[i].get("text")
                        or ""
                    ).strip()
                    for i in after_indices
                    if (
                        bbox_list[i].get("reviewed_text")
                        or bbox_list[i].get("text")
                        or ""
                    ).strip()
                )
                if (
                    sight_context == "neighbours"
                    and len(context_before + context_after) < 100
                ):
                    n_before = 4
                    n_after = 4
                    before_indices = reading_order_indices[max(0, pos - n_before) : pos]
                    after_indices = reading_order_indices[pos + 1 : pos + 1 + n_after]
                    context_before = "\n".join(
                        (
                            bbox_list[i].get("reviewed_text")
                            or bbox_list[i].get("text")
                            or ""
                        ).strip()
                        for i in before_indices
                        if (
                            bbox_list[i].get("reviewed_text")
                            or bbox_list[i].get("text")
                            or ""
                        ).strip()
                    )
                    context_after = "\n".join(
                        (
                            bbox_list[i].get("reviewed_text")
                            or bbox_list[i].get("text")
                            or ""
                        ).strip()
                        for i in after_indices
                        if (
                            bbox_list[i].get("reviewed_text")
                            or bbox_list[i].get("text")
                            or ""
                        ).strip()
                    )

            bp_entry = black_pc_bboxes.get(idx)
            black_pc = (
                float(bp_entry["black_pixels_per_char"])
                if bp_entry and bp_entry.get("black_pixels_per_char") is not None
                else None
            )

            llm_result = call_ollama_sight(
                text,
                time_period=time_period,
                language_style=language_style,
                black_pixels_per_char=black_pc,
                expected_names=expected_names,
                typical_phrases=typical_phrases,
                review_notes=review_notes,
                variants=variants,
                context_before=context_before,
                context_after=context_after,
            )

            llm_confidence = llm_result.get("confidence", 0.0)
            do_confirm = auto_sight_enabled and should_auto_confirm(
                llm_confidence,
                score_threshold,
                llm_result.get("auto_confirm", False),
                black_pixels_per_char=black_pc,
                black_pc_min=black_pc_min,
                black_pc_max=black_pc_max,
            )

            corrected = (llm_result.get("corrected_text") or text).strip()
            reason = (llm_result.get("reason") or "").strip()
            # Dokumentation der KI-Änderung: Jede Prüfung schreibt einen Eintrag (nachvollziehbar im Bearbeiten-Dialog)
            changes_summary = reason or (
                "Text bereinigt/korrigiert durch KI-Review."
                if corrected != text
                else "Keine Änderung (KI bestätigt Original)."
            )
            if ocr_results_llm := bbox.get("ocr_results"):
                ocr_results_llm = dict(ocr_results_llm)
            else:
                ocr_results_llm = {}
            # Eintrag für diese Prüfung (immer setzen, damit im Bearbeiten-Fenster sichtbar)
            llm_sight_entry = {
                "at": datetime.now().isoformat(),
                "original_text": text,
                "corrected_text": corrected,
                "changes_summary": changes_summary,
                "confidence": llm_result.get("confidence"),
                "auto_confirm": llm_result.get("auto_confirm"),
                "reason": reason,
                "outcome": "auto_confirmed" if do_confirm else "reviewed",
            }
            ocr_results_llm["llm_sight"] = llm_sight_entry
            # Historie: Liste aller KI-Prüfungen (jede Prüfung = ein Eintrag)
            reviews_list = list(bbox.get("llm_sight_reviews") or [])
            reviews_list.append(llm_sight_entry)
            bbox["llm_sight_reviews"] = reviews_list
            bbox["ocr_results"] = ocr_results_llm
            bbox["text"] = corrected
            bbox["reviewed_text"] = corrected
            if do_confirm:
                bbox["review_status"] = "auto_confirmed"
                bbox["reviewed_at"] = datetime.now().isoformat()
                bbox["reviewed_by"] = None
                auto_confirmed_count += 1
            processed += 1

            job.progress = min(
                99.0, 70.0 + (processed / max(1, len(bbox_indices))) * 25.0
            )
            db.commit()

        ocr_result.bbox_data = bbox_list
        flag_modified(ocr_result, "bbox_data")
        job.progress = 100.0
        job.current_step = (
            f"Abgeschlossen - {processed} BBoxen, {auto_confirmed_count} auto-bestätigt"
        )
        job.status = OCRJobStatus.COMPLETED
        job.completed_at = datetime.now()
        db.commit()

        # Quality-Job für diese Seite anlegen
        existing_quality = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_page_id == job.document_page_id,
                OCRJob.job_type == "quality",
                OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
            )
            .first()
        )
        if not existing_quality:
            quality_job = OCRJob(
                document_id=job.document_id,
                document_page_id=job.document_page_id,
                job_type="quality",
                status=OCRJobStatus.PENDING,
                language="deu+eng",
                use_correction=False,
                priority=0,
            )
            db.add(quality_job)
            db.commit()
            logger.info(
                f"Quality-Job für Seite {job.document_page_id} nach LLM-Sicht erstellt"
            )

    except Exception as e:
        if job:
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                return
            job.status = OCRJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
        logger.exception("LLM-Sight Job %s fehlgeschlagen", job_id)
    finally:
        db.close()


def _get_pages_with_all_boxes_confirmed(db, document_id: int) -> list[DocumentPage]:
    """
    Liefert alle Seiten des Dokuments, sortiert nach page_number, bei denen
    jede BBox review_status in ('confirmed', 'auto_confirmed') hat.
    """
    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )
    result = []
    for page in pages:
        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == page.id,
                OCRResult.bbox_data.isnot(None),
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )
        if not ocr_result or not ocr_result.bbox_data:
            continue
        bbox_list = (
            json.loads(ocr_result.bbox_data)
            if isinstance(ocr_result.bbox_data, str)
            else list(ocr_result.bbox_data)
        )
        if not bbox_list:
            continue
        allowed = {"confirmed", "auto_confirmed"}
        if all((b.get("review_status") or "").strip() in allowed for b in bbox_list):
            result.append(page)
    return result


def _get_page_text_in_reading_order(db, page_id: int) -> str:
    """Holt BBox-Text der Seite in Lesereihenfolge (reviewed_text or text)."""
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.bbox_data.isnot(None),
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )
    if not ocr_result or not ocr_result.bbox_data:
        return ""
    bbox_list = (
        json.loads(ocr_result.bbox_data)
        if isinstance(ocr_result.bbox_data, str)
        else list(ocr_result.bbox_data)
    )
    return get_text_in_reading_order(bbox_list, separator="\n")


async def process_content_analysis_job(job_id: int) -> None:
    """
    Content-Analyse pro Dokument: Seiten mit voll bestätigten Boxen durchgehen,
    jeweils aktuell + nächste Seite an LLM (Zusammengehörigkeit, Zusammenfassung,
    Personen, Thema, Ort/Datum, Floskeln/Namen), Ergebnis in document_units speichern.
    """
    db = SessionLocal()
    job = None

    try:
        job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
        if not job:
            return
        if job.job_type != "content_analysis":
            job.status = OCRJobStatus.FAILED
            job.error_message = "Ungültiger Job-Typ (erwartet: content_analysis)"
            db.commit()
            return
        if not job.document_id:
            job.status = OCRJobStatus.FAILED
            job.error_message = "content_analysis-Job benötigt document_id"
            db.commit()
            return
        if job.document_page_id:
            job.status = OCRJobStatus.FAILED
            job.error_message = "content_analysis-Job darf kein document_page_id haben"
            db.commit()
            return

        document = db.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Dokument nicht gefunden"
            db.commit()
            return

        pages_confirmed = _get_pages_with_all_boxes_confirmed(db, job.document_id)
        if not pages_confirmed:
            job.status = OCRJobStatus.COMPLETED
            job.current_step = "Keine Seiten mit vollständig bestätigten Boxen"
            job.completed_at = datetime.now()
            db.commit()
            return

        job.status = OCRJobStatus.RUNNING
        job.current_step = "Content-Analyse"
        db.commit()

        i = 0
        units_created = 0
        while i < len(pages_confirmed):
            page_a = pages_confirmed[i]
            page_b = pages_confirmed[i + 1] if i + 1 < len(pages_confirmed) else None

            job.current_step = f"Analysiere Seite {page_a.page_number}"
            db.commit()

            text_a = _get_page_text_in_reading_order(db, page_a.id)
            text_b = _get_page_text_in_reading_order(db, page_b.id) if page_b else None

            llm_result = call_ollama_content_analysis(text_a, text_b)

            if not llm_result.get("success"):
                job.status = OCRJobStatus.FAILED
                job.error_message = (
                    llm_result.get("error") or "LLM-Aufruf fehlgeschlagen"
                )
                job.completed_at = datetime.now()
                db.commit()
                return

            belongs_with_next = llm_result.get("belongs_with_next", False)
            page_ids = [page_a.id]
            if belongs_with_next and page_b:
                page_ids.append(page_b.id)
                i += 2
            else:
                i += 1

            unit = DocumentUnit(
                document_id=job.document_id,
                page_ids=page_ids,
                belongs_with_next=belongs_with_next,
                summary=llm_result.get("summary"),
                persons=llm_result.get("persons") or [],
                topic=llm_result.get("topic"),
                place=llm_result.get("place"),
                event_date=llm_result.get("event_date"),
                extracted_phrases=llm_result.get("extracted_phrases") or [],
                extracted_names=llm_result.get("extracted_names") or [],
            )
            db.add(unit)
            units_created += 1

        job.status = OCRJobStatus.COMPLETED
        job.current_step = f"Abgeschlossen - {units_created} Einheit(en)"
        job.completed_at = datetime.now()
        db.commit()
        logger.info(
            "Content-Analyse Job %s: %s Einheiten für Dokument %s",
            job_id,
            units_created,
            job.document_id,
        )

    except Exception as e:
        if job:
            db.refresh(job)
            if job.status in [OCRJobStatus.CANCELLED, OCRJobStatus.ARCHIVED]:
                return
            job.status = OCRJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
        logger.exception("Content-Analyse Job %s fehlgeschlagen", job_id)
    finally:
        db.close()


def _multibox_fallback_region_box(
    x1_region: int,
    y1_region: int,
    x2_region: int,
    y2_region: int,
    ocr_image_width: int,
    ocr_image_height: int,
) -> list[dict]:
    """
    Erzeugt eine einzelne Fallback-Box für die ganze Region, wenn das OCR-LLM
    keine Unterboxen liefert. So hat der Nutzer wenigstens eine Box und kann
    manuell weiterarbeiten.
    """
    if ocr_image_width <= 0 or ocr_image_height <= 0:
        return []
    bbox_normalized = [
        x1_region / ocr_image_width,
        y1_region / ocr_image_height,
        x2_region / ocr_image_width,
        y2_region / ocr_image_height,
    ]
    return [
        {
            "text": "[Bitte manuell prüfen - keine Unterboxen erkannt]",
            "bbox": bbox_normalized,
            "bbox_pixel": [x1_region, y1_region, x2_region, y2_region],
            "review_status": "new",
            "reviewed_at": None,
            "reviewed_by": None,
            "ocr_results": None,
            "differences": [],
        }
    ]


async def process_multibox_region(
    db,
    document_page_id: int,
    bbox_item: dict,
    ocr_result: OCRResult,
    page: DocumentPage,
) -> list[dict]:
    """
    Verarbeite eine Multibox-Region: Erkenne mehrere Boxen in einem gecroppten Bereich.
    (+X aktuell wieder aktiv für weiteren Versuch.)

    Args:
        db: Datenbank-Session
        document_page_id: ID der DocumentPage
        bbox_item: Die temporäre multibox_region Box
        ocr_result: OCRResult mit Bild-Dimensionen
        page: DocumentPage-Objekt

    Returns:
        Liste von neuen BBox-Dicts, die auf der Original-Seite projiziert wurden
    """
    try:
        # Hole multibox_crop_path
        crop_path = bbox_item.get("multibox_crop_path")
        if not crop_path:
            logger.error(
                f"multibox_crop_path fehlt für BBox {bbox_item.get('bbox_pixel')}"
            )
            return []

        crop_path_obj = Path(crop_path)
        if not crop_path_obj.exists():
            logger.error(f"Gecropptes Bild nicht gefunden: {crop_path}")
            return []

        # Hole Region-Koordinaten (Original-Koordinaten auf der Seite)
        region_bbox_pixel = bbox_item.get("bbox_pixel")
        if not region_bbox_pixel or len(region_bbox_pixel) != 4:
            logger.error(
                f"Ungültige bbox_pixel für Multibox-Region: {region_bbox_pixel}"
            )
            return []

        x1_region, y1_region, x2_region, y2_region = region_bbox_pixel
        region_width = x2_region - x1_region
        region_height = y2_region - y1_region

        logger.debug(
            f"Multibox-Region: Region=[{x1_region},{y1_region},{x2_region},{y2_region}], Crop={crop_path}"
        )

        # Hole OCR-Bild-Dimensionen
        ocr_image_width = ocr_result.image_width
        ocr_image_height = ocr_result.image_height

        if not ocr_image_width or not ocr_image_height:
            logger.error(
                f"OCR-Bild-Dimensionen nicht verfügbar: {ocr_image_width}x{ocr_image_height}"
            )
            return []

        # Führe OCR mit BBox-Extraktion auf dem gecroppten Bild durch
        # Logge Crop-Bild-Größe vor OCR und hole Bildgröße für Prompt
        from PIL import Image as PILImage

        crop_img_size = None
        crop_img_width_for_prompt = None
        crop_img_height_for_prompt = None
        try:
            crop_img_check = PILImage.open(crop_path_obj)
            crop_img_size = crop_img_check.size
            crop_img_width_for_prompt = crop_img_size[0]
            crop_img_height_for_prompt = crop_img_size[1]
            logger.debug(
                f"[Multibox-Region] Crop-Bild-Größe (PIL): {crop_img_width_for_prompt}x{crop_img_height_for_prompt} px"
            )
        except Exception as e:
            logger.warning(
                f"[Multibox-Region] Konnte Crop-Bild-Größe nicht prüfen: {e}"
            )

        # Verwende Standard-Prompt (wie ursprüngliche OCR)
        # WICHTIG: Keine Prompt-Änderungen - der ursprüngliche Prompt funktioniert
        # Das Problem liegt in der Transformation, nicht im Prompt

        ollama_ocr = OllamaVisionOCR()
        ocr_result_data = await asyncio.to_thread(
            ollama_ocr.extract_text_with_bbox, str(crop_path_obj)
        )

        if isinstance(ocr_result_data, Exception) or ocr_result_data.get("error"):
            error_msg = (
                str(ocr_result_data)
                if isinstance(ocr_result_data, Exception)
                else ocr_result_data.get("error", "Unbekannter Fehler")
            )
            logger.error(f"OCR-Fehler für Multibox-Region: {error_msg}")
            return []

        # Parse erkannte Boxen
        detected_bboxes = ocr_result_data.get("bbox_list")
        if not detected_bboxes:
            logger.warning(
                f"Keine Boxen in Multibox-Region erkannt (Crop-Pfad: {crop_path}). "
                "Fallback: Eine Box für die ganze Region."
            )
            # Fallback: Eine Box für die ganze Region, damit der Nutzer nicht leer dasteht
            return _multibox_fallback_region_box(
                x1_region,
                y1_region,
                x2_region,
                y2_region,
                ocr_image_width,
                ocr_image_height,
            )

        crop_image_width = ocr_result_data.get("image_width", 0)
        crop_image_height = ocr_result_data.get("image_height", 0)

        logger.debug(
            f"[Multibox-Region] OCR-LLM Bildgröße: {crop_image_width}x{crop_image_height} px"
        )
        logger.info(f"Multibox-Region: {len(detected_bboxes)} Boxen vom OCR erkannt")

        # Transformiere erkannte Boxen zurück auf Original-Seite
        new_bboxes = []
        _boxes_filtered_outside = 0
        boxes_filtered_invalid = 0
        boxes_filtered_empty_text = 0

        for idx, detected_bbox in enumerate(detected_bboxes):
            # Hole Koordinaten aus erkannten Box (normalized 0-1)
            bbox_normalized = detected_bbox.get("bbox")
            detected_text = detected_bbox.get("text", "").strip()

            if not bbox_normalized or len(bbox_normalized) != 4:
                boxes_filtered_invalid += 1
                logger.warning(
                    f"Box {idx}: Ungültige bbox-Koordinaten (erwartet 4 Werte, erhalten: {bbox_normalized}), "
                    f"Text: '{detected_text[:50]}', Gesamte Box: {detected_bbox}"
                )
                continue

            x1_crop_norm, y1_crop_norm, x2_crop_norm, y2_crop_norm = bbox_normalized

            # WICHTIG: Begrenze normalisierte Koordinaten NICHT auf 1.0!
            # Bestehende Boxen können Werte bis 145% haben, was bedeutet, dass Werte > 1.0
            # gültig sind und die Box über den Rand des Crop-Bildes hinausgeht.
            # Wir verwenden die originalen normalisierten Werte direkt.

            # Stelle sicher, dass x2 > x1 und y2 > y1 (mindestens)
            if x2_crop_norm <= x1_crop_norm:
                logger.warning(
                    f"Box {idx}: Ungültige X-Koordinaten: "
                    f"x1_norm={x1_crop_norm}, x2_norm={x2_crop_norm}, überspringe Box"
                )
                boxes_filtered_invalid += 1
                continue
            if y2_crop_norm <= y1_crop_norm:
                logger.warning(
                    f"Box {idx}: Ungültige Y-Koordinaten: "
                    f"y1_norm={y1_crop_norm}, y2_norm={y2_crop_norm}, überspringe Box"
                )
                boxes_filtered_invalid += 1
                continue

            # Konvertiere normalized Koordinaten zu Pixel-Koordinaten im Crop
            # Erlaube Werte > crop_image_width/height, da normalisierte Werte > 1.0 erlaubt sind
            x1_crop_pixel = int(x1_crop_norm * crop_image_width)
            y1_crop_pixel = int(y1_crop_norm * crop_image_height)
            x2_crop_pixel = int(x2_crop_norm * crop_image_width)
            y2_crop_pixel = int(y2_crop_norm * crop_image_height)

            # Begrenze nur negative Werte (nicht positive Werte > crop_image_width/height)
            x1_crop_pixel = max(0, x1_crop_pixel)
            y1_crop_pixel = max(0, y1_crop_pixel)
            x2_crop_pixel = max(
                x1_crop_pixel + 1, x2_crop_pixel
            )  # Stelle sicher, dass x2 > x1
            y2_crop_pixel = max(
                y1_crop_pixel + 1, y2_crop_pixel
            )  # Stelle sicher, dass y2 > y1

            logger.debug(
                f"Box {idx}: norm=[{x1_crop_norm:.2f},{y1_crop_norm:.2f},{x2_crop_norm:.2f},{y2_crop_norm:.2f}] "
                f"→ crop_px=[{x1_crop_pixel},{y1_crop_pixel},{x2_crop_pixel},{y2_crop_pixel}]"
            )

            # Transformiere erkannte Boxen zurück auf Original-Seite
            # Die erkannten Boxen sind relativ zum Crop-Bild (normalized 0-1)
            # Die Region-Box wurde mit originalen Koordinaten gespeichert
            # Wir skalieren die erkannten Boxen relativ zur Region-Größe und positionieren sie relativ zur Region

            if (
                crop_image_width > 0
                and crop_image_height > 0
                and region_width > 0
                and region_height > 0
            ):
                # WICHTIG: Das Crop-Bild wurde mit * 0.7 für X-Koordinaten erstellt (wie in bbox_ocr.py)
                # Die Region-Box-Koordinaten sind die originalen OCR-Koordinaten
                # Das Crop-Bild ist daher: crop_width = region_width * 0.7
                #
                # Die normalisierten Koordinaten sind relativ zum Crop-Bild (0.0 = Anfang, 1.0 = Ende)
                # Werte > 1.0 bedeuten, dass die Box über den Rand des Crop-Bildes hinausgeht
                #
                # Um zurück zu transformieren:
                # - Die normalisierten Koordinaten skalieren wir direkt auf die Region-Größe
                # - x_original = x1_region + (x_crop_norm * region_width)
                # - Da crop_width = region_width * 0.7, ist das äquivalent zu: x_original = x1_region + (x_crop_pixel / 0.7)
                # - ABER: Wenn x_crop_norm > 1.0, dann ist x_crop_pixel > crop_width, und wir müssen direkt mit norm arbeiten
                #
                # Y-Koordinaten bleiben unverändert (keine Skalierung beim Cropping)

                # Transformiere von normalisierten Crop-Koordinaten zurück zu originalen OCR-Koordinaten
                # WICHTIG: Die normalisierten Koordinaten sind relativ zum Crop-Bild
                # Das Crop-Bild wurde mit * 0.7 für X-Koordinaten erstellt
                # WICHTIG: OCR kann Koordinaten zurückgeben, die größer sind als das Crop-Bild
                # Begrenze daher die Pixel-Koordinaten auf die Crop-Bild-Größe vor Transformation

                # Rücktransformation: Crop-Pixel → OCR-Koordinaten.
                # Crop (0,0) entspricht Region-Start (x1_region, y1_region). Crop-Breite = region_width*0.7.
                # Daher: x_original = x1_region + (crop_pixel_x / 0.7)
                #
                # --- ENTSCHEIDENDE KORREKTUR FÜR MULTIBOX (+X): ---
                # DeepSeek-OCR liefert BBox-Koordinaten in 0-1000-Skala, nicht in Crop-Pixel.
                # Ohne diese Heuristik würden Werte > crop_dim stumpf gekappt (z. B. 956→566)
                # und die Box käme falsch/zu klein an. Wenn x2 oder y2 die Crop-Größe übersteigt,
                # alle vier Koordinaten als 0-1000 interpretieren: crop_pixel = (raw/1000)*crop_dim.
                # ---
                x1_crop_pixel_raw = x1_crop_norm * crop_image_width
                x2_crop_pixel_raw = x2_crop_norm * crop_image_width
                y1_crop_pixel_raw = y1_crop_norm * crop_image_height
                y2_crop_pixel_raw = y2_crop_norm * crop_image_height
                use_1000_scale = (
                    (
                        x2_crop_pixel_raw > crop_image_width
                        or y2_crop_pixel_raw > crop_image_height
                    )
                    and crop_image_width > 0
                    and crop_image_height > 0
                )
                if use_1000_scale:
                    logger.debug(
                        f"Box {idx}: LLM-Koordinaten > Crop-Größe → 0-1000-Skala"
                    )
                    x1_crop_pixel = int(
                        max(
                            0,
                            min(
                                (x1_crop_pixel_raw / 1000.0) * crop_image_width,
                                crop_image_width,
                            ),
                        )
                    )
                    x2_crop_pixel = int(
                        max(
                            0,
                            min(
                                (x2_crop_pixel_raw / 1000.0) * crop_image_width,
                                crop_image_width,
                            ),
                        )
                    )
                    y1_crop_pixel = int(
                        max(
                            0,
                            min(
                                (y1_crop_pixel_raw / 1000.0) * crop_image_height,
                                crop_image_height,
                            ),
                        )
                    )
                    y2_crop_pixel = int(
                        max(
                            0,
                            min(
                                (y2_crop_pixel_raw / 1000.0) * crop_image_height,
                                crop_image_height,
                            ),
                        )
                    )
                else:
                    x1_crop_pixel = int(
                        max(0, min(x1_crop_pixel_raw, crop_image_width))
                    )
                    x2_crop_pixel = int(
                        max(x1_crop_pixel + 1, min(x2_crop_pixel_raw, crop_image_width))
                    )
                    y1_crop_pixel = int(
                        max(0, min(y1_crop_pixel_raw, crop_image_height))
                    )
                    y2_crop_pixel = int(
                        max(
                            y1_crop_pixel + 1, min(y2_crop_pixel_raw, crop_image_height)
                        )
                    )
                x1_original = int(x1_region + (x1_crop_pixel / 0.7))
                x2_original = int(x1_region + (x2_crop_pixel / 0.7))
                y1_original = y1_region + y1_crop_pixel
                y2_original = y1_region + y2_crop_pixel

                logger.debug(
                    f"Box {idx}: → bbox_pixel=[{x1_original},{y1_original},{x2_original},{y2_original}]"
                )
            else:
                boxes_filtered_invalid += 1
                logger.warning(
                    f"Box {idx}: Ungültige Dimensionen: Region={region_width}x{region_height}, "
                    f"Crop-Bild={crop_image_width}x{crop_image_height}, Text: '{detected_text[:50]}'"
                )
                continue

            # Begrenze Box auf Region-Grenzen (statt zu filtern)
            # WICHTIG: Da normalisierte Koordinaten > 1.0 erlaubt sind, können Boxen über den Rand hinausgehen
            # Wir begrenzen sie auf die Region-Grenzen, damit sie nicht verloren gehen
            x1_before_clip = x1_original
            y1_before_clip = y1_original
            x2_before_clip = x2_original
            y2_before_clip = y2_original

            # Begrenze auf Region-Grenzen
            x1_original = max(x1_region, x1_original)
            y1_original = max(y1_region, y1_original)
            x2_original = min(x2_region, x2_original)
            y2_original = min(y2_region, y2_original)

            # Stelle sicher, dass x2 > x1 und y2 > y1
            if x2_original <= x1_original or y2_original <= y1_original:
                boxes_filtered_invalid += 1
                logger.warning(
                    f"Box {idx}: Ungültige Koordinaten nach Begrenzung auf Region: "
                    f"Vorher=[{x1_before_clip}, {y1_before_clip}, {x2_before_clip}, {y2_before_clip}], "
                    f"Nachher=[{x1_original}, {y1_original}, {x2_original}, {y2_original}], "
                    f"Region=[{x1_region}, {y1_region}, {x2_region}, {y2_region}], "
                    f"Text: '{detected_text[:50]}'"
                )
                continue

            if (
                x1_before_clip != x1_original
                or y1_before_clip != y1_original
                or x2_before_clip != x2_original
                or y2_before_clip != y2_original
            ):
                logger.debug(
                    f"Box {idx}: auf Region-Grenzen begrenzt → [{x1_original},{y1_original},{x2_original},{y2_original}]"
                )

            # Kein Clipping auf Bildgrenzen: Box darf über Seitenrand hinausgehen (Viewer/Crop-Preview zeigen außerhalb grau)
            x2_original = max(x1_original + 1, x2_original)
            y2_original = max(y1_original + 1, y2_original)

            # Berechne relative Koordinaten für die neue Box
            bbox_normalized_new = [
                x1_original / ocr_image_width,
                y1_original / ocr_image_height,
                x2_original / ocr_image_width,
                y2_original / ocr_image_height,
            ]

            # Erstelle neue Box
            if not detected_text:
                boxes_filtered_empty_text += 1
                logger.warning(
                    f"Box {idx}: Leerer Text, überspringe Box: "
                    f"Koordinaten=[{x1_original}, {y1_original}, {x2_original}, {y2_original}]"
                )
                continue

            new_bbox = {
                "text": detected_text,
                "bbox": bbox_normalized_new,
                "bbox_pixel": [x1_original, y1_original, x2_original, y2_original],
                "review_status": "new",
                "reviewed_at": None,
                "reviewed_by": None,
                "ocr_results": {
                    "ollama_vision": {
                        "text": detected_text,
                        "confidence": detected_bbox.get("confidence"),
                        "error": None,
                    }
                },
                "differences": [],
            }

            new_bboxes.append(new_bbox)
            logger.debug(
                f"Box {idx}: erstellt bbox_pixel=[{x1_original},{y1_original},{x2_original},{y2_original}]"
            )

        # Fallback: Wenn alle Boxen rausgefiltert wurden, eine Box für die ganze Region
        if not new_bboxes:
            logger.warning(
                f"Alle {len(detected_bboxes)} erkannten Boxen wurden gefiltert. "
                "Fallback: Eine Box für die ganze Region."
            )
            new_bboxes = _multibox_fallback_region_box(
                x1_region,
                y1_region,
                x2_region,
                y2_region,
                ocr_image_width,
                ocr_image_height,
            )

        logger.info(
            f"Multibox-Region: {len(new_bboxes)} Boxen übernommen"
            + (
                f", {boxes_filtered_invalid} ungültig, {boxes_filtered_empty_text} leer"
                if (boxes_filtered_invalid or boxes_filtered_empty_text)
                else ""
            )
        )

        # Lösche temporäre Crop-Datei
        try:
            if crop_path_obj.exists():
                crop_path_obj.unlink()
                logger.debug(f"Temporäre Crop-Datei gelöscht: {crop_path}")
        except Exception as e:
            logger.warning(
                f"Fehler beim Löschen temporärer Crop-Datei {crop_path}: {e}"
            )

        return new_bboxes

    except Exception as e:
        logger.error(
            f"Fehler bei Multibox-Region-Verarbeitung: {e}",
            exc_info=True,
        )
        return []


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


def _bbox_inside_region(child_pixel: list, region_pixel: list) -> bool:
    """Prüft ob child_pixel [x1,y1,x2,y2] vollständig innerhalb region_pixel liegt."""
    if (
        not child_pixel
        or len(child_pixel) != 4
        or not region_pixel
        or len(region_pixel) != 4
    ):
        return False
    cx1, cy1, cx2, cy2 = child_pixel
    rx1, ry1, rx2, ry2 = region_pixel
    return cx1 >= rx1 and cy1 >= ry1 and cx2 <= rx2 and cy2 <= ry2


async def process_persistent_region_quality_job(job_id: int) -> None:
    """
    Verarbeite einen Persistent-Region-Quality-Job: Pro persistente Multibox-Region
    auf der Seite Coverage und schwarze Pixel (gecropptes Bild, Kind-Boxen) berechnen.
    """
    db = SessionLocal()
    job = None

    try:
        job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
        if not job:
            return

        if not job.document_page_id:
            job.status = OCRJobStatus.FAILED
            job.error_message = (
                "Persistent-Region-Quality-Job benötigt document_page_id"
            )
            db.commit()
            return

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

        document = db.query(Document).filter(Document.id == page.document_id).first()
        if not document:
            job.status = OCRJobStatus.FAILED
            job.error_message = "Dokument nicht gefunden"
            db.commit()
            return

        job.status = OCRJobStatus.RUNNING
        job.started_at = datetime.now()
        job.progress = 0.0
        job.current_step = f"Lade OCRResult für Seite {page.page_number}"
        db.commit()

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

        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = list(ocr_result.bbox_data)

        if not isinstance(bbox_list, list):
            job.status = OCRJobStatus.FAILED
            job.error_message = "bbox_data ist keine Liste"
            db.commit()
            return

        job.progress = 15.0
        job.current_step = f"Lade Seitenbild für Seite {page.page_number}"
        db.commit()

        from PIL import Image

        from src.rotary_archiv.config import settings
        from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

        try:
            if not page.file_path:
                pdf_path = get_file_path(document.file_path)
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")
                img = extract_page_as_image(str(pdf_path), page.page_number, dpi=200)
            else:
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
                    from pdf2image import convert_from_path

                    convert_kwargs = {
                        "first_page": page.page_number,
                        "last_page": page.page_number,
                        "dpi": 200,
                    }
                    if settings.poppler_path:
                        pp = Path(settings.poppler_path)
                        if pp.exists():
                            convert_kwargs["poppler_path"] = str(pp)
                    images = convert_from_path(str(file_path), **convert_kwargs)
                    if not images:
                        raise ValueError("PDF konnte nicht zu Bild konvertiert werden")
                    img = images[0]

            if page.deskew_angle is not None:
                from src.rotary_archiv.utils.image_utils import deskew_image

                img = deskew_image(img, page.deskew_angle)

            if (
                ocr_result.image_width
                and ocr_result.image_height
                and img.size != (ocr_result.image_width, ocr_result.image_height)
            ):
                img = img.resize(
                    (
                        ocr_result.image_width,
                        ocr_result.image_height,
                    ),
                    Image.Resampling.LANCZOS,
                )
        except Exception as e:
            job.status = OCRJobStatus.FAILED
            job.error_message = f"Fehler beim Laden des Seitenbilds: {e!s}"
            db.commit()
            return

        regions = [
            (idx, b)
            for idx, b in enumerate(bbox_list)
            if b.get("persistent_multibox_region") is True
            and b.get("bbox_pixel")
            and len(b.get("bbox_pixel", [])) == 4
        ]

        if not regions:
            job.progress = 100.0
            job.status = OCRJobStatus.COMPLETED
            job.current_step = "Keine persistente Region auf dieser Seite"
            job.completed_at = datetime.now()
            quality_metrics = ocr_result.quality_metrics or {}
            if isinstance(quality_metrics, str):
                quality_metrics = json.loads(quality_metrics)
            quality_metrics = dict(quality_metrics)
            quality_metrics["persistent_region_metrics"] = []
            ocr_result.quality_metrics = quality_metrics
            flag_modified(ocr_result, "quality_metrics")
            db.commit()
            return

        persistent_region_metrics = []
        total_regions = len(regions)
        for region_idx, (r_idx, r_item) in enumerate(regions):
            job.progress = 30.0 + (60.0 * region_idx / total_regions)
            job.current_step = (
                f"Berechne Region {region_idx + 1}/{total_regions} (BBox {r_idx})"
            )
            db.commit()

            region_pixel = r_item.get("bbox_pixel")

            children: list[dict] = []
            for idx, b in enumerate(bbox_list):
                if idx == r_idx:
                    continue
                if b.get("box_type") in ("ignore_region", "note"):
                    continue
                if b.get("persistent_multibox_region") is True:
                    continue
                bp = b.get("bbox_pixel")
                if not bp or len(bp) != 4:
                    continue
                if not _bbox_inside_region(bp, region_pixel):
                    continue
                children.append(
                    {
                        "index": idx,
                        "bbox_pixel": bp,
                        "text": b.get("text") or "",
                        "reviewed_text": b.get("reviewed_text"),
                    }
                )

            try:
                result = compute_region_coverage_and_black_pixels(
                    img,
                    region_pixel,
                    children,
                    dark_threshold=200,
                )
            except Exception as e:
                logger.warning(
                    "Fehler bei Region %s (BBox %s): %s", region_idx, r_idx, e
                )
                persistent_region_metrics.append(
                    {
                        "region_bbox_index": r_idx,
                        "coverage_ratio": None,
                        "uncovered_ratio": None,
                        "total_dark_pixels_region": None,
                        "child_count": len(children),
                        "children": [],
                        "error": str(e),
                    }
                )
                continue

            cov = result.get("coverage", {})
            persistent_region_metrics.append(
                {
                    "region_bbox_index": r_idx,
                    "coverage_ratio": cov.get("coverage_ratio"),
                    "uncovered_ratio": cov.get("uncovered_ratio"),
                    "total_dark_pixels_region": result.get("total_dark_pixels_region"),
                    "child_count": len(children),
                    "children": result.get("children", []),
                }
            )

        job.progress = 92.0
        job.current_step = "Speichere Qualitätsmetriken"
        db.commit()

        quality_metrics = ocr_result.quality_metrics or {}
        if isinstance(quality_metrics, str):
            quality_metrics = json.loads(quality_metrics)
        quality_metrics = dict(quality_metrics)
        quality_metrics["persistent_region_metrics"] = persistent_region_metrics
        ocr_result.quality_metrics = quality_metrics
        flag_modified(ocr_result, "quality_metrics")
        db.commit()

        job.current_step = f"Abgeschlossen - {len(persistent_region_metrics)} Regionen"
        job.progress = 100.0
        job.status = OCRJobStatus.COMPLETED
        job.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        if job:
            db.refresh(job)
            if job.status not in [
                OCRJobStatus.CANCELLED,
                OCRJobStatus.ARCHIVED,
            ]:
                job.status = OCRJobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now()
                db.commit()
        logger.exception("Persistent-Region-Quality Job %s fehlgeschlagen", job_id)

    finally:
        db.close()
