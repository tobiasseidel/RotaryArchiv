"""
API Endpoints für Qualitätsmetriken
"""

import copy
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from src.rotary_archiv.config import settings
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    OCRJob,
    OCRJobStatus,
    OCRResult,
)
from src.rotary_archiv.utils.ocr_result_loading import (
    get_best_ocr_result_with_bbox_for_page,
)

router = APIRouter(prefix="/api/quality", tags=["quality"])

logger = logging.getLogger(__name__)


class QualityJobCreateResponse(BaseModel):
    """Response für Quality-Job-Erstellung"""

    job_id: int
    message: str


class BatchCreateJobsResponse(BaseModel):
    """Response für Batch-Job-Erstellung"""

    created: int
    job_ids: list[int]


class ReRecognizeSingleRequest(BaseModel):
    """Request für Re-OCR einer einzelnen persistente Region"""

    region_bbox_index: int


class ReRecognizeBatchItem(BaseModel):
    """Ein Eintrag für Batch Re-OCR"""

    page_id: int
    region_bbox_index: int


class ReRecognizeBatchRequest(BaseModel):
    """Request für Re-OCR mehrerer persistente Regionen"""

    items: list[ReRecognizeBatchItem]


@router.get("/config")
def get_quality_config():
    """
    Gibt die konfigurierten Schwellenwerte für Dichte-Farben zurück.
    """
    return {
        "density_green_min": settings.density_green_min,
        "density_green_max": settings.density_green_max,
        "density_orange_min": settings.density_orange_min,
        "density_orange_max": settings.density_orange_max,
    }


@router.get("/debug/stats")
def get_quality_stats(db: Session = Depends(get_db)):
    """
    Debug-Endpoint: Zeigt Statistiken zu Qualitätsmetriken.

    Returns:
        Statistiken: Seiten mit bbox_data, mit/ohne quality_metrics, Job-Status
    """
    from sqlalchemy import func

    # Zähle Seiten mit bbox_data
    pages_with_bbox = (
        db.query(func.count(func.distinct(OCRResult.document_page_id)))
        .filter(OCRResult.bbox_data.isnot(None))
        .scalar()
    ) or 0

    # Zähle Seiten mit quality_metrics
    pages_with_metrics = (
        db.query(func.count(func.distinct(OCRResult.document_page_id)))
        .filter(OCRResult.quality_metrics.isnot(None))
        .scalar()
    ) or 0

    # Zähle Quality-Jobs nach Status
    jobs_pending = (
        db.query(func.count(OCRJob.id))
        .filter(
            OCRJob.job_type == "quality",
            OCRJob.status == OCRJobStatus.PENDING,
        )
        .scalar()
    ) or 0

    jobs_running = (
        db.query(func.count(OCRJob.id))
        .filter(
            OCRJob.job_type == "quality",
            OCRJob.status == OCRJobStatus.RUNNING,
        )
        .scalar()
    ) or 0

    jobs_completed = (
        db.query(func.count(OCRJob.id))
        .filter(
            OCRJob.job_type == "quality",
            OCRJob.status == OCRJobStatus.COMPLETED,
        )
        .scalar()
    ) or 0

    jobs_failed = (
        db.query(func.count(OCRJob.id))
        .filter(
            OCRJob.job_type == "quality",
            OCRJob.status == OCRJobStatus.FAILED,
        )
        .scalar()
    ) or 0

    # Finde fehlgeschlagene Jobs mit Fehlermeldungen
    failed_jobs = (
        db.query(OCRJob)
        .filter(
            OCRJob.job_type == "quality",
            OCRJob.status == OCRJobStatus.FAILED,
        )
        .order_by(OCRJob.created_at.desc())
        .limit(10)
        .all()
    )

    failed_job_details = [
        {
            "job_id": job.id,
            "document_page_id": job.document_page_id,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in failed_jobs
    ]

    return {
        "pages_with_bbox": pages_with_bbox,
        "pages_with_quality_metrics": pages_with_metrics,
        "pages_without_quality_metrics": pages_with_bbox - pages_with_metrics,
        "jobs": {
            "pending": jobs_pending,
            "running": jobs_running,
            "completed": jobs_completed,
            "failed": jobs_failed,
            "total": jobs_pending + jobs_running + jobs_completed + jobs_failed,
        },
        "recent_failed_jobs": failed_job_details,
    }


@router.get("/pages")
def get_quality_pages(
    document_id: int | None = Query(
        None, description="Optional: Filter nach Dokument-ID"
    ),
    min_coverage: float | None = Query(
        None, description="Optional: Mindest-Coverage-Ratio (0.0-1.0)"
    ),
    max_coverage: float | None = Query(
        None, description="Optional: Maximal-Coverage-Ratio (0.0-1.0)"
    ),
    min_uncovered_ratio: float | None = Query(
        None, description="Optional: Mindest-Anteil unbedeckter dunkler Pixel (0.0-1.0)"
    ),
    max_uncovered_ratio: float | None = Query(
        None, description="Optional: Maximal-Anteil unbedeckter dunkler Pixel (0.0-1.0)"
    ),
    include_bboxes: bool = Query(
        True,
        description="Bei False nur Zusammenfassung pro Seite (keine bbox_densities), für schnelle Listen-Ansicht",
    ),
    db: Session = Depends(get_db),
):
    """
    Hole alle Seiten mit Qualitätsmetriken (filterbar).
    Eine Anfrage liefert das Datenpaket für die Tabelle; BBox-Daten pro Zeile
    können separat beim Aufklappen abgerufen werden (GET /pages/{page_id}).

    Args:
        document_id: Optional: nur Seiten dieses Dokuments
        min_coverage: Optional: Mindest-Coverage-Ratio
        max_coverage: Optional: Maximal-Coverage-Ratio
        include_bboxes: Bei False nur Summary (keine bbox_densities), kleineres Payload

    Returns:
        Liste von Seiten mit Qualitätsmetriken
    """

    try:
        # Eine Abfrage: neuestes OCRResult pro Seite mit DocumentPage + Document
        # Subquery: (document_page_id, max(created_at)) für OCRResults mit quality_metrics
        latest_ocr_subq = (
            db.query(
                OCRResult.document_page_id,
                sqlfunc.max(OCRResult.created_at).label("max_created_at"),
            )
            .filter(OCRResult.quality_metrics.isnot(None))
            .group_by(OCRResult.document_page_id)
        ).subquery("latest_ocr")

        # Join: OCRResult (nur neueste pro Seite) + DocumentPage + Document
        query = (
            db.query(OCRResult, DocumentPage, Document)
            .join(
                latest_ocr_subq,
                (OCRResult.document_page_id == latest_ocr_subq.c.document_page_id)
                & (OCRResult.created_at == latest_ocr_subq.c.max_created_at),
            )
            .join(DocumentPage, DocumentPage.id == OCRResult.document_page_id)
            .join(Document, Document.id == DocumentPage.document_id)
        )

        if document_id:
            query = query.filter(DocumentPage.document_id == document_id)

        rows = query.order_by(DocumentPage.created_at.desc()).all()

        result = []
        for ocr_result, page, document in rows:
            if not ocr_result.quality_metrics:
                continue

            quality_metrics = ocr_result.quality_metrics
            coverage = quality_metrics.get("coverage", {})
            density = quality_metrics.get("density", {})
            density_summary = density.get("summary", {})
            black_pc = quality_metrics.get("black_pixels_per_char", {})
            black_pc_summary = black_pc.get("summary", {})

            coverage_ratio = coverage.get("coverage_ratio", 0.0)
            uncovered_ratio = coverage.get(
                "uncovered_ratio",
                1.0 - coverage_ratio if coverage_ratio <= 1.0 else 0.0,
            )
            if min_coverage is not None and coverage_ratio < min_coverage:
                continue
            if max_coverage is not None and coverage_ratio > max_coverage:
                continue
            if (
                min_uncovered_ratio is not None
                and uncovered_ratio < min_uncovered_ratio
            ):
                continue
            if (
                max_uncovered_ratio is not None
                and uncovered_ratio > max_uncovered_ratio
            ):
                continue

            document_title = (
                document.title or document.filename or f"Dokument #{page.document_id}"
            )

            # Review-Status aus bbox_data: Anteil geprüfter BBoxen (confirmed/rejected/auto_confirmed)
            bbox_data_list = ocr_result.bbox_data
            if isinstance(bbox_data_list, str):
                try:
                    bbox_data_list = (
                        json.loads(bbox_data_list) if bbox_data_list else []
                    )
                except json.JSONDecodeError:
                    bbox_data_list = []
            bbox_data_list = bbox_data_list if isinstance(bbox_data_list, list) else []
            # Nur OCR- und Ignore-Boxen für Review-Statistik (Notizen ausnehmen)
            review_bboxes = [b for b in bbox_data_list if b.get("box_type") != "note"]
            total_bboxes = len(review_bboxes)
            reviewed_count = sum(
                1
                for b in review_bboxes
                if b.get("review_status") in ("confirmed", "rejected", "auto_confirmed")
            )
            reviewed_pct = (
                round(reviewed_count / total_bboxes * 100.0, 1) if total_bboxes else 0.0
            )

            if include_bboxes:
                bbox_densities = list(density.get("bboxes", []))
                bbox_black_pc = {b["index"]: b for b in black_pc.get("bboxes", [])}
                for bbox in bbox_densities:
                    idx = bbox.get("index")
                    if idx in bbox_black_pc:
                        bp = bbox_black_pc[idx]
                        bbox["black_pixels"] = bp.get("black_pixels")
                        bbox["black_pixels_per_char"] = bp.get("black_pixels_per_char")
                    if idx < len(bbox_data_list):
                        bd = bbox_data_list[idx]
                        bbox["review_status"] = bd.get("review_status", "pending")
                        bbox["reviewed_at"] = bd.get("reviewed_at")
                        bbox["reviewed_by"] = bd.get("reviewed_by")
            else:
                bbox_densities = []

            result.append(
                {
                    "page_id": page.id,
                    "document_id": page.document_id,
                    "document_title": document_title,
                    "page_number": page.page_number,
                    "coverage_ratio": coverage_ratio,
                    "uncovered_ratio": uncovered_ratio,
                    "uncovered_dark_pixels": coverage.get("uncovered_dark_pixels", 0),
                    "total_dark_pixels": coverage.get("total_dark_pixels", 0),
                    "min_chars_per_1k_px": density_summary.get(
                        "min_chars_per_1k_px", 0.0
                    ),
                    "max_chars_per_1k_px": density_summary.get(
                        "max_chars_per_1k_px", 0.0
                    ),
                    "min_black_pixels_per_char": black_pc_summary.get(
                        "min_black_pixels_per_char"
                    ),
                    "max_black_pixels_per_char": black_pc_summary.get(
                        "max_black_pixels_per_char"
                    ),
                    "bbox_count": density_summary.get("bbox_count", 0),
                    "reviewed_pct": reviewed_pct,
                    "bbox_densities": bbox_densities,
                    "computed_at": ocr_result.created_at.isoformat()
                    if ocr_result.created_at
                    else None,
                }
            )

        logger.info(f"Quality-Endpoint: {len(result)} Seiten mit Metriken gefunden")
        return {"pages": result}

    except Exception as e:
        logger.error(f"Fehler im Quality-List-Endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Qualitäts-Seiten: {e!s}",
        ) from None


def _iter_matching_bboxes(
    rows,
    min_chars_per_1k_px,
    max_chars_per_1k_px,
    min_black_pixels_per_char,
    max_black_pixels_per_char,
    min_black_pixels,
    max_black_pixels,
    text_search=None,
    min_char_count=None,
    max_char_count=None,
    review_status_filter=None,
    max_left_pct=None,
    min_right_pct=None,
    min_width_pct=None,
    max_width_pct=None,
    box_type_filter=None,
):
    """Iteriert über alle BBoxen mit Qualitätsmetriken, gefiltert nach Optionen."""
    for ocr_result, page, document in rows:
        if not ocr_result.quality_metrics:
            continue
        quality_metrics = ocr_result.quality_metrics
        density = quality_metrics.get("density", {})
        black_pc = quality_metrics.get("black_pixels_per_char", {})
        bbox_densities = list(density.get("bboxes", []))
        bbox_black_pc = {b["index"]: b for b in black_pc.get("bboxes", [])}
        bbox_data_list = ocr_result.bbox_data
        if isinstance(bbox_data_list, str):
            try:
                bbox_data_list = json.loads(bbox_data_list) if bbox_data_list else []
            except json.JSONDecodeError:
                bbox_data_list = []
        bbox_data_list = bbox_data_list if isinstance(bbox_data_list, list) else []
        document_title = (
            document.title or document.filename or f"Dokument #{page.document_id}"
        )
        # Seitenbreite für Prozentberechnung
        page_width = ocr_result.image_width
        if not page_width or page_width <= 0:
            # Fallback: versuche aus bbox_pixel zu schätzen
            max_x = 0
            for bd in bbox_data_list:
                bbox_pixel = bd.get("bbox_pixel")
                if isinstance(bbox_pixel, (list, tuple)) and len(bbox_pixel) >= 4:
                    max_x = max(max_x, bbox_pixel[2])  # x2 ist die rechte Kante
            page_width = max_x if max_x > 0 else None

        for bbox in bbox_densities:
            idx = bbox.get("index")

            # WICHTIG: Validiere, dass der Index noch in bbox_data_list existiert
            # Dies verhindert, dass veraltete quality_metrics zu nicht-existierenden BBoxen führen
            if (
                idx is None
                or not isinstance(idx, int)
                or idx < 0
                or idx >= len(bbox_data_list)
            ):
                logger.debug(
                    f"Überspringe BBox mit veraltetem Index {idx} für Seite {page.id} "
                    f"(bbox_data_list hat {len(bbox_data_list)} Einträge)"
                )
                continue

            chars_per_1k = bbox.get("chars_per_1k_px")
            if chars_per_1k is None:
                continue

            # Berechne char_count aus aktuellen bbox_data_list, nicht aus quality_metrics
            # (quality_metrics können veraltet sein)
            char_count = 0
            if idx < len(bbox_data_list):
                bd = bbox_data_list[idx]
                text = bd.get("reviewed_text") or bd.get("text") or ""
                # Stelle sicher, dass text ein String ist
                if not isinstance(text, str):
                    text = str(text) if text is not None else ""
                char_count = len(text)
            else:
                # Fallback: verwende char_count aus quality_metrics
                char_count = bbox.get("char_count", 0)
                # Stelle sicher, dass char_count ein Integer ist
                if not isinstance(char_count, int):
                    try:
                        char_count = int(char_count)
                    except (ValueError, TypeError):
                        char_count = 0

            # Stelle sicher, dass char_count ein Integer ist
            if not isinstance(char_count, int):
                try:
                    char_count = int(char_count)
                except (ValueError, TypeError):
                    char_count = 0

            # Filter nach char_count
            if min_char_count is not None and char_count < min_char_count:
                continue
            if max_char_count is not None and char_count > max_char_count:
                continue
            bp = bbox_black_pc.get(idx, {})
            black_px = bp.get("black_pixels")
            black_pc_val = bp.get("black_pixels_per_char")
            if min_chars_per_1k_px is not None and chars_per_1k < min_chars_per_1k_px:
                continue
            if max_chars_per_1k_px is not None and chars_per_1k > max_chars_per_1k_px:
                continue
            if min_black_pixels_per_char is not None:
                if black_pc_val is None:
                    continue
                if black_pc_val < min_black_pixels_per_char:
                    continue
            if max_black_pixels_per_char is not None:
                if black_pc_val is None:
                    continue
                if black_pc_val > max_black_pixels_per_char:
                    continue
            if min_black_pixels is not None:
                if black_px is None:
                    continue
                if black_px < min_black_pixels:
                    continue
            if max_black_pixels is not None:
                if black_px is None:
                    continue
                if black_px > max_black_pixels:
                    continue
            if text_search and text_search.strip():
                search_lower = text_search.strip().lower()
                full_text = ""
                if idx < len(bbox_data_list):
                    bd = bbox_data_list[idx]
                    full_text = (
                        bd.get("reviewed_text") or bd.get("text") or ""
                    ).strip()
                if not full_text:
                    full_text = (bbox.get("text_preview") or "").strip()
                if search_lower not in full_text.lower():
                    continue
            review_status = "pending"
            if idx < len(bbox_data_list):
                review_status = bbox_data_list[idx].get("review_status", "pending")
            if review_status_filter and review_status not in review_status_filter:
                continue

            if box_type_filter:
                bd = bbox_data_list[idx] if idx < len(bbox_data_list) else {}
                is_persistent = bd.get("persistent_multibox_region") is True
                is_note = bd.get("box_type") == "note"
                actual_type = (
                    "persistent_region"
                    if is_persistent
                    else ("note" if is_note else "normal")
                )
                if actual_type not in box_type_filter:
                    continue

            # Berechne Positionen als Prozent der Seitenbreite
            left_pct = None
            right_pct = None
            width_pct = None
            if page_width and page_width > 0:
                bbox_pixel = None
                if idx < len(bbox_data_list):
                    bbox_pixel = bbox_data_list[idx].get("bbox_pixel")
                if isinstance(bbox_pixel, (list, tuple)) and len(bbox_pixel) >= 4:
                    x1, _, x2, _ = (
                        bbox_pixel[0],
                        bbox_pixel[1],
                        bbox_pixel[2],
                        bbox_pixel[3],
                    )
                    left_pct = round((x1 / page_width) * 100.0, 2)
                    right_pct = round((x2 / page_width) * 100.0, 2)
                    width_pct = round(((x2 - x1) / page_width) * 100.0, 2)

            # Filter nach Positionen
            if (
                max_left_pct is not None
                and left_pct is not None
                and left_pct > max_left_pct
            ):
                continue
            if (
                min_right_pct is not None
                and right_pct is not None
                and right_pct < min_right_pct
            ):
                continue
            if (
                min_width_pct is not None
                and width_pct is not None
                and width_pct < min_width_pct
            ):
                continue
            if (
                max_width_pct is not None
                and width_pct is not None
                and width_pct > max_width_pct
            ):
                continue

            full_text = ""
            if idx < len(bbox_data_list):
                bd = bbox_data_list[idx]
                full_text = bd.get("reviewed_text") or bd.get("text") or ""
                if not isinstance(full_text, str):
                    full_text = str(full_text) if full_text is not None else ""
            yield {
                "page_id": page.id,
                "document_id": page.document_id,
                "document_title": document_title,
                "page_number": page.page_number,
                "bbox_index": idx,
                "id": f"{page.id}_{idx}",
                "text_preview": bbox.get("text_preview", ""),
                "text": full_text,
                "char_count": char_count,
                "chars_per_1k_px": round(chars_per_1k, 2),
                "black_pixels": black_px,
                "black_pixels_per_char": round(black_pc_val, 2)
                if black_pc_val is not None
                else None,
                "review_status": review_status,
                "left_pct": left_pct,
                "right_pct": right_pct,
                "width_pct": width_pct,
            }


@router.get("/bbox-list")
def get_bbox_list(
    document_id: int | None = Query(None, description="Optional: nur dieses Dokument"),
    min_chars_per_1k_px: float | None = Query(
        None, description="Filter: Mindestwert Zeichen/1000 px"
    ),
    max_chars_per_1k_px: float | None = Query(
        None, description="Filter: Maximalwert Zeichen/1000 px"
    ),
    min_black_pixels_per_char: float | None = Query(
        None, description="Filter: Mindestwert schwarze px/Zeichen"
    ),
    max_black_pixels_per_char: float | None = Query(
        None, description="Filter: Maximalwert schwarze px/Zeichen"
    ),
    min_black_pixels: int | None = Query(
        None, description="Filter: Mindestwert schwarze Pixel pro Box"
    ),
    max_black_pixels: int | None = Query(
        None, description="Filter: Maximalwert schwarze Pixel pro Box"
    ),
    text_search: str | None = Query(
        None,
        description="Filter: erkannten Text durchsuchen (Vorkommen im BBox-Text)",
    ),
    min_char_count: int | None = Query(
        None, description="Filter: Mindestwert Zeichenanzahl pro Box"
    ),
    max_char_count: int | None = Query(
        None, description="Filter: Maximalwert Zeichenanzahl pro Box"
    ),
    review_status: list[str] | None = Query(
        None, description="Filter: Review-Status (kann mehrfach angegeben werden)"
    ),
    max_left_pct: float | None = Query(
        None,
        description="Filter: Maximale Position der linken Kante in % der Seitenbreite",
    ),
    min_right_pct: float | None = Query(
        None,
        description="Filter: Minimale Position der rechten Kante in % der Seitenbreite",
    ),
    min_width_pct: float | None = Query(
        None, description="Filter: Minimale Breite in % der Seitenbreite"
    ),
    max_width_pct: float | None = Query(
        None, description="Filter: Maximale Breite in % der Seitenbreite"
    ),
    box_type: list[str] | None = Query(
        None, description="Filter: Box-Art (normal, note, persistent_region)"
    ),
    page_number_min: int | None = Query(
        None, description="Filter: Seitenzahl ab (inklusive)"
    ),
    page_number_max: int | None = Query(
        None, description="Filter: Seitenzahl bis (inklusive)"
    ),
    limit: int = Query(200, ge=1, le=500, description="Anzahl pro Seite"),
    offset: int = Query(0, ge=0, description="Offset für Paginierung"),
    db: Session = Depends(get_db),
):
    """
    Liste aller BBoxen mit Qualitätsmetriken (Dichte, schwarze px, schwarze px/Zeichen).
    Gefiltert und paginiert (z. B. 200 pro Seite).
    """
    try:
        latest_ocr_subq = (
            db.query(
                OCRResult.document_page_id,
                sqlfunc.max(OCRResult.created_at).label("max_created_at"),
            )
            .filter(OCRResult.quality_metrics.isnot(None))
            .group_by(OCRResult.document_page_id)
        ).subquery("latest_ocr")
        query = (
            db.query(OCRResult, DocumentPage, Document)
            .join(
                latest_ocr_subq,
                (OCRResult.document_page_id == latest_ocr_subq.c.document_page_id)
                & (OCRResult.created_at == latest_ocr_subq.c.max_created_at),
            )
            .join(DocumentPage, DocumentPage.id == OCRResult.document_page_id)
            .join(Document, Document.id == DocumentPage.document_id)
        )
        if document_id is not None:
            query = query.filter(DocumentPage.document_id == document_id)
        if page_number_min is not None:
            query = query.filter(DocumentPage.page_number >= page_number_min)
        if page_number_max is not None:
            query = query.filter(DocumentPage.page_number <= page_number_max)
        rows = query.order_by(DocumentPage.document_id, DocumentPage.page_number).all()

        it = _iter_matching_bboxes(
            rows,
            min_chars_per_1k_px,
            max_chars_per_1k_px,
            min_black_pixels_per_char,
            max_black_pixels_per_char,
            min_black_pixels,
            max_black_pixels,
            text_search=text_search,
            min_char_count=min_char_count,
            max_char_count=max_char_count,
            review_status_filter=review_status if review_status else None,
            max_left_pct=max_left_pct,
            min_right_pct=min_right_pct,
            min_width_pct=min_width_pct,
            max_width_pct=max_width_pct,
            box_type_filter=box_type if box_type else None,
        )
        all_matching = list(it)
        total = len(all_matching)
        items = all_matching[offset : offset + limit]
        return {"total": total, "items": items}
    except Exception as e:
        logger.error(f"Fehler im BBox-List-Endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der BBox-Liste: {e!s}",
        ) from None


@router.get("/pages/{page_id}")
def get_page_quality_metrics(page_id: int, db: Session = Depends(get_db)):
    """
    Hole gespeicherte Qualitätsmetriken für eine Seite.

    Args:
        page_id: ID der Seite

    Returns:
        Quality-Metriken (coverage + density) aus OCRResult.quality_metrics

    Raises:
        404: Wenn Seite nicht gefunden oder keine Metriken vorhanden
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )

    # Hole bestes OCRResult mit bbox_data für diese Seite (OLLAMA_VISION oder PDF_NATIVE)
    ocr_result = get_best_ocr_result_with_bbox_for_page(db, page_id)

    if not ocr_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine OCR-Ergebnisse mit BBox-Daten für diese Seite gefunden",
        )

    if not ocr_result.quality_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qualitätsmetriken für diese Seite noch nicht berechnet",
        )

    # Review-Status aus bbox_data in density.bboxes mergen + reviewed_pct
    result = copy.deepcopy(ocr_result.quality_metrics)
    bbox_data_list = ocr_result.bbox_data
    if isinstance(bbox_data_list, str):
        try:
            bbox_data_list = json.loads(bbox_data_list) if bbox_data_list else []
        except json.JSONDecodeError:
            bbox_data_list = []
    bbox_data_list = bbox_data_list if isinstance(bbox_data_list, list) else []
    review_bboxes = [b for b in bbox_data_list if b.get("box_type") != "note"]
    total_bboxes = len(review_bboxes)
    reviewed_count = sum(
        1
        for b in review_bboxes
        if b.get("review_status") in ("confirmed", "rejected", "auto_confirmed")
    )
    result["reviewed_pct"] = (
        round(reviewed_count / total_bboxes * 100.0, 1) if total_bboxes else 0.0
    )
    density = result.get("density", {})
    for bbox in density.get("bboxes", []):
        idx = bbox.get("index")
        if isinstance(idx, int) and idx < len(bbox_data_list):
            bd = bbox_data_list[idx]
            bbox["review_status"] = bd.get("review_status", "pending")
            bbox["reviewed_at"] = bd.get("reviewed_at")
            bbox["reviewed_by"] = bd.get("reviewed_by")

    return result


@router.post("/pages/{page_id}/compute", response_model=QualityJobCreateResponse)
def create_quality_job(page_id: int, db: Session = Depends(get_db)):
    """
    Erstellt einen Quality-Job für eine einzelne Seite.

    Args:
        page_id: ID der Seite

    Returns:
        Job-ID und Bestätigung
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )

    # Prüfe ob bereits ein Quality-Job für diese Seite pending/running ist
    existing_job = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_page_id == page_id,
            OCRJob.job_type == "quality",
            OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
        )
        .first()
    )

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quality-Job für diese Seite bereits vorhanden (Job-ID: {existing_job.id})",
        )

    # Erstelle Quality-Job
    quality_job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="quality",
        status=OCRJobStatus.PENDING,
        language="deu+eng",  # Nicht relevant für Quality, aber erforderlich
        use_correction=False,  # Nicht relevant für Quality
        priority=0,
    )

    db.add(quality_job)
    db.commit()
    db.refresh(quality_job)

    return QualityJobCreateResponse(
        job_id=quality_job.id, message="Quality-Job erstellt"
    )


@router.post("/batch-create-jobs", response_model=BatchCreateJobsResponse)
def batch_create_quality_jobs(
    document_id: int | None = Query(
        None, description="Optional: nur für dieses Dokument"
    ),
    db: Session = Depends(get_db),
):
    """
    Erstellt Quality-Jobs für alle Seiten mit bbox_data (inkl. Seiten die bereits Metriken haben = Nachberechnung).

    Args:
        document_id: Optional: nur Seiten dieses Dokuments

    Returns:
        Anzahl erstellter Jobs und Liste von Job-IDs
    """
    # Finde alle DocumentPages mit OCRResult.bbox_data (mit und ohne quality_metrics)

    # Schritt 1: Finde alle Seiten mit bbox_data
    pages_with_bbox_query = (
        db.query(DocumentPage.id)
        .join(OCRResult, OCRResult.document_page_id == DocumentPage.id)
        .filter(OCRResult.bbox_data.isnot(None))
        .distinct()
    )

    if document_id:
        pages_with_bbox_query = pages_with_bbox_query.filter(
            DocumentPage.document_id == document_id
        )

    page_ids_with_bbox = {row[0] for row in pages_with_bbox_query.all()}

    # Schritt 2: Lade DocumentPage-Objekte (alle mit bbox_data, auch mit bestehenden Metriken)
    if not page_ids_with_bbox:
        pages_to_process = []
    else:
        pages_to_process = (
            db.query(DocumentPage)
            .filter(DocumentPage.id.in_(page_ids_with_bbox))
            .order_by(DocumentPage.id)
            .all()
        )

    logger.info(
        f"Batch-Quality-Jobs: {len(pages_to_process)} Seiten mit BBox zur (Nach-)Berechnung"
    )

    created_jobs: list[int] = []
    skipped = 0
    reset_failed = 0

    for page in pages_to_process:
        # Prüfe ob bereits ein Quality-Job für diese Seite existiert
        existing_job = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_page_id == page.id,
                OCRJob.job_type == "quality",
            )
            .order_by(OCRJob.created_at.desc())
            .first()
        )

        if existing_job:
            # Wenn Job pending/running: überspringen
            if existing_job.status in [OCRJobStatus.PENDING, OCRJobStatus.RUNNING]:
                skipped += 1
                continue
            # Wenn Job failed: auf PENDING zurücksetzen statt neuen zu erstellen
            elif existing_job.status == OCRJobStatus.FAILED:
                existing_job.status = OCRJobStatus.PENDING
                existing_job.error_message = None
                existing_job.started_at = None
                existing_job.completed_at = None
                existing_job.progress = 0.0
                existing_job.current_step = None
                created_jobs.append(existing_job.id)
                reset_failed += 1
                continue
            # Wenn completed: neuen Job erstellen für Nachberechnung (Metriken werden überschrieben)
            elif existing_job.status == OCRJobStatus.COMPLETED:
                quality_job = OCRJob(
                    document_id=page.document_id,
                    document_page_id=page.id,
                    job_type="quality",
                    status=OCRJobStatus.PENDING,
                    language="deu+eng",
                    use_correction=False,
                    priority=0,
                )
                db.add(quality_job)
                db.flush()
                created_jobs.append(quality_job.id)
                continue
            # Andere Status (z.B. CANCELLED): erstelle neuen Job
            else:
                logger.info(
                    f"Seite {page.id} hat Job mit Status {existing_job.status} - erstelle neuen Job"
                )
                # Erstelle neuen Quality-Job
                quality_job = OCRJob(
                    document_id=page.document_id,
                    document_page_id=page.id,
                    job_type="quality",
                    status=OCRJobStatus.PENDING,
                    language="deu+eng",
                    use_correction=False,
                    priority=0,
                )
                db.add(quality_job)
                db.flush()  # Flush um ID zu erhalten
                created_jobs.append(quality_job.id)
                continue

        # Erstelle neuen Quality-Job (kein existierender Job)
        quality_job = OCRJob(
            document_id=page.document_id,
            document_page_id=page.id,
            job_type="quality",
            status=OCRJobStatus.PENDING,
            language="deu+eng",
            use_correction=False,
            priority=0,
        )

        db.add(quality_job)
        db.flush()  # Flush um ID zu erhalten
        created_jobs.append(quality_job.id)

    db.commit()

    logger.info(
        f"Batch-Quality-Jobs: {len(created_jobs) - reset_failed} neue Jobs erstellt, "
        f"{reset_failed} fehlgeschlagene Jobs zurückgesetzt, {skipped} übersprungen"
    )

    return BatchCreateJobsResponse(created=len(created_jobs), job_ids=created_jobs)


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


def _iter_persistent_regions(rows):
    """Iteriert über alle persistente Regionen aus (OCRResult, DocumentPage, Document) rows."""
    for ocr_result, page, document in rows:
        bbox_data_list = ocr_result.bbox_data
        if isinstance(bbox_data_list, str):
            try:
                bbox_data_list = json.loads(bbox_data_list) if bbox_data_list else []
            except json.JSONDecodeError:
                bbox_data_list = []
        if not isinstance(bbox_data_list, list):
            continue

        pr_metrics_list = []
        qm = ocr_result.quality_metrics
        if qm and isinstance(qm, dict):
            pr_metrics_list = qm.get("persistent_region_metrics") or []
        elif qm and isinstance(qm, str):
            try:
                qm = json.loads(qm)
                pr_metrics_list = qm.get("persistent_region_metrics") or []
            except json.JSONDecodeError:
                pass

        metrics_by_index = {
            m["region_bbox_index"]: m
            for m in pr_metrics_list
            if "region_bbox_index" in m
        }

        document_title = (
            document.title or document.filename or f"Dokument #{document.id}"
        )

        for idx, b in enumerate(bbox_data_list):
            if b.get("persistent_multibox_region") is not True:
                continue
            rp = b.get("bbox_pixel")
            if not rp or len(rp) != 4:
                continue

            children = []
            for cidx, c in enumerate(bbox_data_list):
                if cidx == idx:
                    continue
                if c.get("box_type") in ("ignore_region", "note"):
                    continue
                if c.get("persistent_multibox_region") is True:
                    continue
                cp = c.get("bbox_pixel")
                if not cp or len(cp) != 4:
                    continue
                if not _bbox_inside_region(cp, rp):
                    continue
                text = c.get("reviewed_text") or c.get("text") or ""
                children.append(
                    {
                        "bbox_index": cidx,
                        "text_preview": text[:50] + ("..." if len(text) > 50 else ""),
                        "char_count": len(text),
                        "review_status": c.get("review_status", "pending"),
                    }
                )

            metrics = metrics_by_index.get(idx, {})
            for ch in metrics.get("children", []):
                bi = ch.get("bbox_index")
                for c in children:
                    if c.get("bbox_index") == bi:
                        c["black_pixels"] = ch.get("black_pixels")
                        c["black_pixels_per_char"] = ch.get("black_pixels_per_char")
                        break

            sum_black = sum((c.get("black_pixels") or 0) for c in children)
            sum_chars = sum((c.get("char_count") or 0) for c in children)
            children_black_pixels_per_char = (
                sum_black / sum_chars if sum_chars > 0 else None
            )

            coverage_ratio = metrics.get("coverage_ratio")
            uncovered_ratio = metrics.get("uncovered_ratio")
            total_dark = metrics.get("total_dark_pixels_region")
            re_recognition_stages = metrics.get("re_recognition_stages")
            best_stage_index = metrics.get("best_stage_index")

            yield {
                "document_id": page.document_id,
                "document_title": document_title,
                "page_id": page.id,
                "page_number": page.page_number,
                "region_bbox_index": idx,
                "region_bbox_pixel": rp,
                "coverage_ratio": coverage_ratio,
                "uncovered_ratio": uncovered_ratio,
                "total_dark_pixels_region": total_dark,
                "child_count": len(children),
                "children_black_pixels_sum": sum_black if children else None,
                "children_char_count_sum": sum_chars if children else None,
                "children_black_pixels_per_char": children_black_pixels_per_char,
                "children": children,
                "re_recognition_stages": re_recognition_stages,
                "best_stage_index": best_stage_index,
            }


@router.get("/persistent-regions")
def get_persistent_regions(
    document_id: int | None = Query(
        None, description="Optional: Filter nach Dokument-ID"
    ),
    page_id: int | None = Query(None, description="Optional: Filter nach Seiten-ID"),
    min_coverage: float | None = Query(None, description="Min. Coverage (0.0-1.0)"),
    max_coverage: float | None = Query(None, description="Max. Coverage (0.0-1.0)"),
    min_uncovered_ratio: float | None = Query(
        None, description="Min. Unbedeckte Ratio (0.0-1.0)"
    ),
    max_uncovered_ratio: float | None = Query(
        None, description="Max. Unbedeckte Ratio (0.0-1.0)"
    ),
    min_children_black_pixels_per_char: float | None = Query(
        None, description="Min. Schwarze px/Zeichen (Summe aller Kind-Boxen)"
    ),
    max_children_black_pixels_per_char: float | None = Query(
        None, description="Max. Schwarze px/Zeichen (Summe aller Kind-Boxen)"
    ),
    sort: str = Query(
        "page_id",
        description="Sortierung: page_id, document_id, coverage_ratio, child_count, children_black_pixels_per_char",
    ),
    order: str = Query("asc", description="asc oder desc"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Liste aller persistenter Multibox-Regionen mit optionalen Metriken und Kind-Boxen.
    """
    try:
        latest_ocr_subq = (
            db.query(
                OCRResult.document_page_id,
                sqlfunc.max(OCRResult.created_at).label("max_created_at"),
            )
            .filter(OCRResult.bbox_data.isnot(None))
            .group_by(OCRResult.document_page_id)
        ).subquery("latest_ocr")

        query = (
            db.query(OCRResult, DocumentPage, Document)
            .join(
                latest_ocr_subq,
                (OCRResult.document_page_id == latest_ocr_subq.c.document_page_id)
                & (OCRResult.created_at == latest_ocr_subq.c.max_created_at),
            )
            .join(DocumentPage, DocumentPage.id == OCRResult.document_page_id)
            .join(Document, Document.id == DocumentPage.document_id)
            .filter(OCRResult.bbox_data.isnot(None))
        )
        if document_id is not None:
            query = query.filter(DocumentPage.document_id == document_id)
        if page_id is not None:
            query = query.filter(DocumentPage.id == page_id)
        rows = query.order_by(DocumentPage.document_id, DocumentPage.page_number).all()

        all_items = list(_iter_persistent_regions(rows))

        if min_coverage is not None:
            all_items = [
                i
                for i in all_items
                if i.get("coverage_ratio") is not None
                and i["coverage_ratio"] >= min_coverage
            ]
        if max_coverage is not None:
            all_items = [
                i
                for i in all_items
                if i.get("coverage_ratio") is not None
                and i["coverage_ratio"] <= max_coverage
            ]
        if min_uncovered_ratio is not None:
            all_items = [
                i
                for i in all_items
                if i.get("uncovered_ratio") is not None
                and i["uncovered_ratio"] >= min_uncovered_ratio
            ]
        if max_uncovered_ratio is not None:
            all_items = [
                i
                for i in all_items
                if i.get("uncovered_ratio") is not None
                and i["uncovered_ratio"] <= max_uncovered_ratio
            ]

        if min_children_black_pixels_per_char is not None:
            all_items = [
                i
                for i in all_items
                if i.get("children_black_pixels_per_char") is not None
                and i["children_black_pixels_per_char"]
                >= min_children_black_pixels_per_char
            ]
        if max_children_black_pixels_per_char is not None:
            all_items = [
                i
                for i in all_items
                if i.get("children_black_pixels_per_char") is not None
                and i["children_black_pixels_per_char"]
                <= max_children_black_pixels_per_char
            ]

        key_map = {
            "page_id": lambda i: (i.get("page_id") or 0),
            "document_id": lambda i: (i.get("document_id") or 0),
            "coverage_ratio": lambda i: (
                i.get("coverage_ratio") if i.get("coverage_ratio") is not None else -1.0
            ),
            "child_count": lambda i: (i.get("child_count") or 0),
            "children_black_pixels_per_char": lambda i: (
                i.get("children_black_pixels_per_char")
                if i.get("children_black_pixels_per_char") is not None
                else -1.0
            ),
        }
        sort_key = key_map.get(sort, key_map["page_id"])
        reverse = order.lower() == "desc"
        all_items.sort(key=sort_key, reverse=reverse)

        total = len(all_items)
        items = all_items[offset : offset + limit]
        return {"total": total, "items": items}
    except Exception as e:
        logger.error(f"Fehler GET /persistent-regions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der persistente Regionen: {e!s}",
        ) from None


@router.post(
    "/pages/{page_id}/persistent-region-compute",
    response_model=QualityJobCreateResponse,
)
def create_persistent_region_quality_job(page_id: int, db: Session = Depends(get_db)):
    """Erstellt einen Persistent-Region-Quality-Job für eine einzelne Seite."""
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )

    existing = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_page_id == page_id,
            OCRJob.job_type == "persistent_region_quality",
            OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Persistent-Region-Quality-Job für diese Seite bereits vorhanden (Job-ID: {existing.id})",
        )

    job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="persistent_region_quality",
        status=OCRJobStatus.PENDING,
        language="deu+eng",
        use_correction=False,
        priority=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return QualityJobCreateResponse(
        job_id=job.id, message="Persistent-Region-Quality-Job erstellt"
    )


@router.post(
    "/batch-create-persistent-region-jobs", response_model=BatchCreateJobsResponse
)
def batch_create_persistent_region_jobs(
    document_id: int | None = Query(None, description="Optional: nur dieses Dokument"),
    db: Session = Depends(get_db),
):
    """Erstellt Persistent-Region-Quality-Jobs für alle Seiten mit mindestens einer persistente Region."""
    pages_with_bbox = (
        db.query(DocumentPage.id)
        .join(OCRResult, OCRResult.document_page_id == DocumentPage.id)
        .filter(OCRResult.bbox_data.isnot(None))
        .distinct()
    )
    if document_id is not None:
        pages_with_bbox = pages_with_bbox.filter(
            DocumentPage.document_id == document_id
        )
    page_ids = {r[0] for r in pages_with_bbox.all()}

    if not page_ids:
        return BatchCreateJobsResponse(created=0, job_ids=[])

    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.id.in_(page_ids))
        .order_by(DocumentPage.id)
        .all()
    )

    created_jobs: list[int] = []
    for page in pages:
        ocr_result = get_best_ocr_result_with_bbox_for_page(db, page.id)
        if not ocr_result or not ocr_result.bbox_data:
            continue
        bbox_list = ocr_result.bbox_data
        if isinstance(bbox_list, str):
            try:
                bbox_list = json.loads(bbox_list)
            except json.JSONDecodeError:
                continue
        if not isinstance(bbox_list, list):
            continue
        has_region = any(
            b.get("persistent_multibox_region") is True
            and b.get("bbox_pixel")
            and len(b.get("bbox_pixel", [])) == 4
            for b in bbox_list
        )
        if not has_region:
            continue

        existing = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_page_id == page.id,
                OCRJob.job_type == "persistent_region_quality",
                OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
            )
            .first()
        )
        if existing:
            continue

        job = OCRJob(
            document_id=page.document_id,
            document_page_id=page.id,
            job_type="persistent_region_quality",
            status=OCRJobStatus.PENDING,
            language="deu+eng",
            use_correction=False,
            priority=0,
        )
        db.add(job)
        db.flush()
        created_jobs.append(job.id)

    db.commit()
    return BatchCreateJobsResponse(created=len(created_jobs), job_ids=created_jobs)


@router.post(
    "/pages/{page_id}/persistent-regions/re-recognize",
    response_model=QualityJobCreateResponse,
)
def create_persistent_region_re_recognize_job(
    page_id: int,
    body: ReRecognizeSingleRequest,
    db: Session = Depends(get_db),
):
    """Erstellt einen Re-OCR-mehrstufig-Job für eine persistente Region auf der Seite."""
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )
    ocr_result = get_best_ocr_result_with_bbox_for_page(db, page_id)
    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine BBox-Daten für diese Seite",
        )
    bbox_list = (
        json.loads(ocr_result.bbox_data)
        if isinstance(ocr_result.bbox_data, str)
        else list(ocr_result.bbox_data)
    )
    idx = body.region_bbox_index
    if idx < 0 or idx >= len(bbox_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"region_bbox_index {idx} ungültig",
        )
    if bbox_list[idx].get("persistent_multibox_region") is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine persistente Multibox-Region an diesem Index",
        )
    job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="persistent_region_re_recognize",
        status=OCRJobStatus.PENDING,
        language="deu+eng",
        use_correction=False,
        progress=0.0,
        priority=0,
        job_params={"region_bbox_index": idx},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return QualityJobCreateResponse(
        job_id=job.id,
        message="Re-OCR-mehrstufig-Job erstellt",
    )


@router.post(
    "/persistent-regions/re-recognize",
    response_model=BatchCreateJobsResponse,
)
def create_persistent_region_re_recognize_batch(
    body: ReRecognizeBatchRequest,
    db: Session = Depends(get_db),
):
    """Erstellt Re-OCR-mehrstufig-Jobs für alle angegebenen (page_id, region_bbox_index)."""
    if not body.items:
        return BatchCreateJobsResponse(created=0, job_ids=[])
    created_jobs: list[int] = []
    for item in body.items:
        page = db.query(DocumentPage).filter(DocumentPage.id == item.page_id).first()
        if not page:
            continue
        ocr_result = get_best_ocr_result_with_bbox_for_page(db, item.page_id)
        if not ocr_result or not ocr_result.bbox_data:
            continue
        bbox_list = ocr_result.bbox_data
        if isinstance(bbox_list, str):
            try:
                bbox_list = json.loads(bbox_list)
            except json.JSONDecodeError:
                continue
        if not isinstance(bbox_list, list):
            continue
        idx = item.region_bbox_index
        if idx < 0 or idx >= len(bbox_list):
            continue
        if bbox_list[idx].get("persistent_multibox_region") is not True:
            continue
        job = OCRJob(
            document_id=page.document_id,
            document_page_id=item.page_id,
            job_type="persistent_region_re_recognize",
            status=OCRJobStatus.PENDING,
            language="deu+eng",
            use_correction=False,
            progress=0.0,
            priority=0,
            job_params={"region_bbox_index": idx},
        )
        db.add(job)
        db.flush()
        created_jobs.append(job.id)
    db.commit()
    return BatchCreateJobsResponse(created=len(created_jobs), job_ids=created_jobs)
