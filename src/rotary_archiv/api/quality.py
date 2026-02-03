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
            if min_coverage is not None and coverage_ratio < min_coverage:
                continue
            if max_coverage is not None and coverage_ratio > max_coverage:
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
            total_bboxes = len(bbox_data_list)
            reviewed_count = sum(
                1
                for b in bbox_data_list
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

    # Hole neuestes OCRResult mit bbox_data für diese Seite
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.bbox_data.isnot(None),
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

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
    total_bboxes = len(bbox_data_list)
    reviewed_count = sum(
        1
        for b in bbox_data_list
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
