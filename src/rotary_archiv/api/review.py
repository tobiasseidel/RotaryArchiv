"""
Review API-Endpoints für Bounding Box Review
"""

from datetime import datetime
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from pathlib import Path
import tempfile
import uuid

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore
    PIL_AVAILABLE = False

from src.rotary_archiv.config import settings
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    OCRJob,
    OCRJobStatus,
    OCRResult,
    OCRSource,
)
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from sqlalchemy import func as sqlfunc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


def _create_quality_job_if_needed(page_id: int, db: Session) -> None:
    """
    Erstellt einen Quality-Job für eine Seite, falls noch keiner pending/running ist.

    Args:
        page_id: ID der Seite
        db: Datenbank-Session
    """
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
        return  # Job existiert bereits

    # Hole Seite für document_id
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        logger.warning(f"Seite {page_id} nicht gefunden für Quality-Job-Erstellung")
        return

    # Erstelle Quality-Job mit niedrigerer Priorität als BBox-Review-Jobs
    # (höhere Zahl = niedrigere Priorität)
    quality_job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="quality",
        status=OCRJobStatus.PENDING,
        language="deu+eng",  # Nicht relevant für Quality, aber erforderlich
        use_correction=False,  # Nicht relevant für Quality
        priority=1,  # Niedrigere Priorität als BBox-Review-Jobs (priority=-1)
    )

    db.add(quality_job)
    db.commit()
    logger.info(f"Quality-Job für Seite {page_id} erstellt (Job-ID: {quality_job.id})")


class SaveReviewedBBoxRequest(BaseModel):
    """Request-Schema für gespeicherte Review-BBox"""

    reviewed_text: str


class AddBBoxRequest(BaseModel):
    """Request-Schema für neu hinzugefügte BBox"""

    bbox_pixel: list[int]  # [x1, y1, x2, y2] Pixel-Koordinaten


class AddMultipleBBoxesRequest(BaseModel):
    """Request-Schema für automatische Erkennung mehrerer BBoxen in einem Bereich"""

    bbox_pixel: list[int]  # [x1, y1, x2, y2] Pixel-Koordinaten der gezeichneten Box


class BBoxRef(BaseModel):
    """Referenz auf eine BBox"""

    page_id: int
    bbox_index: int


class BatchChangeStatusRequest(BaseModel):
    """Request-Schema für Batch-Status-Änderung"""

    bboxes: list[BBoxRef] | None = None  # Optional: explizite Liste von BBoxen
    new_status: str  # pending, confirmed, rejected, auto_confirmed, ignored, new
    # Filter-Parameter (optional, wenn gesetzt werden bboxes ignoriert)
    document_id: int | None = None
    min_chars_per_1k_px: float | None = None
    max_chars_per_1k_px: float | None = None
    min_black_pixels_per_char: float | None = None
    max_black_pixels_per_char: float | None = None
    min_black_pixels: int | None = None
    max_black_pixels: int | None = None
    text_search: str | None = None
    min_char_count: int | None = None
    max_char_count: int | None = None
    review_status: list[str] | None = None
    max_left_pct: float | None = None
    min_right_pct: float | None = None
    min_width_pct: float | None = None
    max_width_pct: float | None = None


class BatchDiscardAndRecalcRequest(BaseModel):
    """Request-Schema für Batch-OCR verwerfen und neu berechnen"""

    bboxes: list[BBoxRef] | None = None  # Optional: explizite Liste von BBoxen
    # Filter-Parameter (optional, wenn gesetzt werden bboxes ignoriert)
    document_id: int | None = None
    min_chars_per_1k_px: float | None = None
    max_chars_per_1k_px: float | None = None
    min_black_pixels_per_char: float | None = None
    max_black_pixels_per_char: float | None = None
    min_black_pixels: int | None = None
    max_black_pixels: int | None = None
    text_search: str | None = None
    min_char_count: int | None = None
    max_char_count: int | None = None
    review_status: list[str] | None = None
    max_left_pct: float | None = None
    min_right_pct: float | None = None
    min_width_pct: float | None = None
    max_width_pct: float | None = None


class BatchDeleteRequest(BaseModel):
    """Request-Schema für Batch-BBoxen löschen"""

    bboxes: list[BBoxRef] | None = None  # Optional: explizite Liste von BBoxen
    # Filter-Parameter (optional, wenn gesetzt werden bboxes ignoriert)
    document_id: int | None = None
    min_chars_per_1k_px: float | None = None
    max_chars_per_1k_px: float | None = None
    min_black_pixels_per_char: float | None = None
    max_black_pixels_per_char: float | None = None
    min_black_pixels: int | None = None
    max_black_pixels: int | None = None
    text_search: str | None = None
    min_char_count: int | None = None
    max_char_count: int | None = None
    review_status: list[str] | None = None
    max_left_pct: float | None = None
    min_right_pct: float | None = None
    min_width_pct: float | None = None
    max_width_pct: float | None = None


def _get_filtered_bboxes_from_request(
    request: BatchChangeStatusRequest | BatchDiscardAndRecalcRequest | BatchDeleteRequest,
    db: Session,
):
    """
    Hilfsfunktion: Ermittelt BBoxen basierend auf Filter-Parametern oder expliziter Liste.
    
    Returns:
        Liste von (page_id, bbox_index) Tupeln
    """
    # Prüfe ob Filter-Parameter vorhanden sind
    # Wenn bboxes explizit gesetzt ist, verwende diese (auch wenn Filter gesetzt sind)
    if request.bboxes:
        logger.debug("Filter: Verwende explizite bboxes-Liste (Filter-Parameter werden ignoriert)")
        return [(bbox_ref.page_id, bbox_ref.bbox_index) for bbox_ref in request.bboxes]
    
    has_filters = any([
        request.document_id is not None,
        request.min_chars_per_1k_px is not None,
        request.max_chars_per_1k_px is not None,
        request.min_black_pixels_per_char is not None,
        request.max_black_pixels_per_char is not None,
        request.min_black_pixels is not None,
        request.max_black_pixels is not None,
        request.text_search,
        request.min_char_count is not None,
        request.max_char_count is not None,
        request.review_status,
        request.max_left_pct is not None,
        request.min_right_pct is not None,
        request.min_width_pct is not None,
        request.max_width_pct is not None,
    ])
    
    if not has_filters:
        logger.warning("Filter: Weder bboxes noch Filter-Parameter gesetzt, gebe leere Liste zurück")
        return []
    
    if has_filters:
        # Verwende Filter-Logik aus quality.py
        from src.rotary_archiv.api.quality import _iter_matching_bboxes
        
        # Baue Query wie in get_bbox_list
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
        
        if request.document_id is not None:
            query = query.filter(DocumentPage.document_id == request.document_id)
        
        rows = query.order_by(DocumentPage.document_id, DocumentPage.page_number).all()
        
        # Verwende Filter-Funktion
        it = _iter_matching_bboxes(
            rows,
            request.min_chars_per_1k_px,
            request.max_chars_per_1k_px,
            request.min_black_pixels_per_char,
            request.max_black_pixels_per_char,
            request.min_black_pixels,
            request.max_black_pixels,
            text_search=request.text_search,
            min_char_count=request.min_char_count,
            max_char_count=request.max_char_count,
            review_status_filter=request.review_status if request.review_status else None,
            max_left_pct=request.max_left_pct,
            min_right_pct=request.min_right_pct,
            min_width_pct=request.min_width_pct,
            max_width_pct=request.max_width_pct,
        )
        
        # Sammle alle gefilterten BBoxen
        # HINWEIS: Wir validieren die Indizes NICHT hier, sondern lassen batch_delete
        # die ungültigen Indizes einfach überspringen. Das ist effizienter und vermeidet
        # das Problem, dass quality_metrics veraltet sein können.
        filtered_items = list(it)
        logger.info(f"Filter: {len(filtered_items)} BBoxen gefunden durch Filter-Logik")
        
        # Konvertiere direkt zu Liste von (page_id, bbox_index) Tupeln
        # Die Validierung erfolgt später in batch_delete, wo ungültige Indizes einfach übersprungen werden
        return [(item["page_id"], item["bbox_index"]) for item in filtered_items]


@router.get("/pages/{page_id}/bboxes")
async def get_page_bboxes(
    page_id: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Hole alle BBoxes einer Seite mit Review-Status

    Returns:
        {
            "page_id": 1,
            "bboxes": [
                {
                    "index": 0,
                    "text": "...",
                    "bbox": [...],
                    "bbox_pixel": [...],
                    "review_status": "pending",
                    "reviewed_at": null,
                    "reviewed_by": null,
                    "ocr_results": {...},
                    "differences": [...]
                },
                ...
            ]
        }
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole OCRResult mit bbox_data
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        return {"page_id": page_id, "bboxes": []}

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data

    # Formatiere für Response
    bboxes = []
    for idx, bbox_item in enumerate(bbox_list):
        bboxes.append(
            {
                "index": idx,
                "text": bbox_item.get("text", ""),
                "bbox": bbox_item.get("bbox", []),
                "bbox_pixel": bbox_item.get("bbox_pixel", []),
                "review_status": bbox_item.get("review_status", "pending"),
                "reviewed_at": bbox_item.get("reviewed_at"),
                "reviewed_by": bbox_item.get("reviewed_by"),
                "ocr_results": bbox_item.get("ocr_results"),
                "differences": bbox_item.get("differences", []),
            }
        )

    return {"page_id": page_id, "bboxes": bboxes}


@router.post("/pages/{page_id}/bboxes/{bbox_index}/confirm")
async def confirm_bbox(
    page_id: int,
    bbox_index: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Manuelle Bestätigung einer BBox

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data.copy()

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    # Aktualisiere BBox
    bbox_list[bbox_index]["review_status"] = "confirmed"
    bbox_list[bbox_index]["reviewed_at"] = datetime.now().isoformat()
    bbox_list[bbox_index]["reviewed_by"] = None  # TODO: User-ID aus Session

    # Speichere zurück - SQLAlchemy muss über Änderung an JSON-Feld informiert werden
    ocr_result.bbox_data = bbox_list
    flag_modified(ocr_result, "bbox_data")
    db.commit()

    # Erstelle Quality-Job für diese Seite
    _create_quality_job_if_needed(page_id, db)

    return {
        "success": True,
        "message": f"BBox {bbox_index} bestätigt",
        "bbox": bbox_list[bbox_index],
    }


@router.post("/pages/{page_id}/bboxes/{bbox_index}/reject")
async def reject_bbox(
    page_id: int,
    bbox_index: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Manuelle Ablehnung einer BBox

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data.copy()

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    # Aktualisiere BBox
    bbox_list[bbox_index]["review_status"] = "rejected"
    bbox_list[bbox_index]["reviewed_at"] = datetime.now().isoformat()
    bbox_list[bbox_index]["reviewed_by"] = None  # TODO: User-ID aus Session

    # Speichere zurück - SQLAlchemy muss über Änderung an JSON-Feld informiert werden
    ocr_result.bbox_data = bbox_list
    flag_modified(ocr_result, "bbox_data")
    db.commit()

    # Erstelle Quality-Job für diese Seite
    _create_quality_job_if_needed(page_id, db)

    return {
        "success": True,
        "message": f"BBox {bbox_index} abgelehnt",
        "bbox": bbox_list[bbox_index],
    }


@router.post("/pages/{page_id}/bboxes/{bbox_index}/ignore")
async def ignore_bbox(
    page_id: int,
    bbox_index: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Ignoriere eine BBox (z.B. wenn es ein Fehler ist wie Ausschnitt von Nachbarseite)

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data.copy()

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    # Aktualisiere BBox
    bbox_list[bbox_index]["review_status"] = "ignored"
    bbox_list[bbox_index]["reviewed_at"] = datetime.now().isoformat()
    bbox_list[bbox_index]["reviewed_by"] = None  # TODO: User-ID aus Session

    # Speichere zurück - SQLAlchemy muss über Änderung an JSON-Feld informiert werden
    ocr_result.bbox_data = bbox_list
    flag_modified(ocr_result, "bbox_data")
    db.commit()

    # Erstelle Quality-Job für diese Seite
    _create_quality_job_if_needed(page_id, db)

    return {
        "success": True,
        "message": f"BBox {bbox_index} ignoriert",
        "bbox": bbox_list[bbox_index],
    }


@router.delete("/pages/{page_id}/bboxes/{bbox_index}")
async def delete_bbox(
    page_id: int,
    bbox_index: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Löscht eine BBox dauerhaft aus bbox_data.

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste

    Returns:
        {"success": True, "message": "BBox gelöscht"}
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data.copy()

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    bbox_list.pop(bbox_index)
    ocr_result.bbox_data = bbox_list
    flag_modified(ocr_result, "bbox_data")
    db.commit()

    # Erstelle Quality-Job für diese Seite
    _create_quality_job_if_needed(page_id, db)

    return {"success": True, "message": "BBox gelöscht"}


@router.post("/batch-change-status")
async def batch_change_status(
    request: BatchChangeStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Ändert den Review-Status mehrerer BBoxen in einem Batch.

    Args:
        request: Liste von BBox-Referenzen und neuer Status

    Returns:
        {"success": True, "updated": int, "errors": [...]}
    """
    valid_statuses = {
        "pending",
        "confirmed",
        "rejected",
        "auto_confirmed",
        "ignored",
        "new",
    }
    if request.new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Status: {request.new_status}. Erlaubt: {valid_statuses}",
        )

    updated = 0
    errors = []

    # Ermittle BBoxen (entweder aus Filter oder expliziter Liste)
    bbox_refs = _get_filtered_bboxes_from_request(request, db)
    
    if not bbox_refs:
        return {"success": True, "updated": 0, "errors": []}

    # Gruppiere BBoxen nach page_id für effiziente DB-Zugriffe
    from collections import defaultdict

    bboxes_by_page = defaultdict(list)
    for page_id, bbox_index in bbox_refs:
        bboxes_by_page[page_id].append(bbox_index)

    for page_id, bbox_indices in bboxes_by_page.items():
        # Hole Seite
        page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
        if not page:
            for idx in bbox_indices:
                errors.append(
                    {
                        "page_id": page_id,
                        "bbox_index": idx,
                        "error": "Seite nicht gefunden",
                    }
                )
            continue

        # Hole OCRResult
        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == page_id,
                OCRResult.source == OCRSource.OLLAMA_VISION,
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )

        if not ocr_result or not ocr_result.bbox_data:
            for idx in bbox_indices:
                errors.append(
                    {
                        "page_id": page_id,
                        "bbox_index": idx,
                        "error": "Keine BBox-Daten für diese Seite gefunden",
                    }
                )
            continue

        # Parse bbox_data
        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data.copy()

        # Aktualisiere alle BBoxen dieser Seite
        modified = False
        for bbox_index in bbox_indices:
            if bbox_index < 0 or bbox_index >= len(bbox_list):
                errors.append(
                    {
                        "page_id": page_id,
                        "bbox_index": bbox_index,
                        "error": "BBox-Index außerhalb des Bereichs",
                    }
                )
                continue

            bbox_list[bbox_index]["review_status"] = request.new_status
            if request.new_status in ("pending", "new"):
                bbox_list[bbox_index]["reviewed_at"] = None
                bbox_list[bbox_index]["reviewed_by"] = None
            else:
                bbox_list[bbox_index]["reviewed_at"] = datetime.now().isoformat()
                bbox_list[bbox_index]["reviewed_by"] = None  # TODO: User-ID aus Session
            modified = True
            updated += 1

        if modified:
            ocr_result.bbox_data = bbox_list
            flag_modified(ocr_result, "bbox_data")
            db.commit()
            # Erstelle Quality-Job für diese Seite
            _create_quality_job_if_needed(page_id, db)

    return {"success": True, "updated": updated, "errors": errors}


@router.post("/batch-discard-and-recalc")
async def batch_discard_and_recalc(
    request: BatchDiscardAndRecalcRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Verwirft OCR-Inhalte mehrerer BBoxen und erstellt Review-Jobs für Neuberechnung.

    Schritt 1: Setzt text="", ocr_results=None, differences=[], review_status="new"
    Schritt 2: Erstellt Review-Jobs (gruppiert nach Seite)

    Args:
        request: Liste von BBox-Referenzen oder Filter-Parameter

    Returns:
        {"success": True, "discarded": int, "jobs_created": int, "jobs_existing": int, "errors": [...]}
    """
    discarded = 0
    errors = []
    jobs_created = 0
    jobs_existing = 0

    # Ermittle BBoxen (entweder aus Filter oder expliziter Liste)
    try:
        bbox_refs = _get_filtered_bboxes_from_request(request, db)
        logger.info(f"Batch-Discard-And-Recalc: Gefilterte BBoxen gefunden: {len(bbox_refs)}")
    except Exception as e:
        logger.error(f"Batch-Discard-And-Recalc: Fehler beim Filtern der BBoxen: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fehler beim Filtern der BBoxen: {e!s}")
    
    if not bbox_refs:
        logger.info("Batch-Discard-And-Recalc: Keine BBoxen gefunden, die den Filtern entsprechen")
        return {
            "success": True,
            "discarded": 0,
            "jobs_created": 0,
            "jobs_existing": 0,
            "errors": [],
        }

    # Gruppiere BBoxen nach page_id
    from collections import defaultdict

    bboxes_by_page = defaultdict(list)
    for page_id, bbox_index in bbox_refs:
        bboxes_by_page[page_id].append(bbox_index)
    
    logger.info(f"Batch-Discard-And-Recalc: Verarbeite {len(bboxes_by_page)} Seiten mit insgesamt {len(bbox_refs)} BBoxen")

    # Schritt 1: Verwerfen
    for page_id, bbox_indices in bboxes_by_page.items():
        page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
        if not page:
            # Zusammenfassende Fehlermeldung statt für jeden Index
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"Seite {page_id} nicht gefunden ({len(bbox_indices)} BBoxen betroffen)",
                }
            )
            continue

        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == page_id,
                OCRResult.source == OCRSource.OLLAMA_VISION,
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )

        if not ocr_result or not ocr_result.bbox_data:
            # Zusammenfassende Fehlermeldung statt für jeden Index
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"Keine BBox-Daten für Seite {page_id} gefunden ({len(bbox_indices)} BBoxen betroffen)",
                }
            )
            continue

        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data.copy()

        modified = False
        valid_indices = [idx for idx in bbox_indices if 0 <= idx < len(bbox_list)]
        
        # Fehler nur loggen, nicht für jeden einzelnen Index zurückgeben
        invalid_count = len(bbox_indices) - len(valid_indices)
        if invalid_count > 0:
            logger.warning(
                f"Batch-Discard-And-Recalc: {invalid_count} von {len(bbox_indices)} BBox-Indizes "
                f"außerhalb des Bereichs für Seite {page_id} (BBox-Liste hat {len(bbox_list)} Einträge)"
            )
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"{invalid_count} BBox-Indizes außerhalb des Bereichs (Seite hat {len(bbox_list)} BBoxen)",
                }
            )

        for bbox_index in valid_indices:
            bbox_list[bbox_index]["text"] = ""
            bbox_list[bbox_index]["ocr_results"] = None
            bbox_list[bbox_index]["differences"] = []
            bbox_list[bbox_index]["review_status"] = "new"
            bbox_list[bbox_index]["reviewed_at"] = None
            bbox_list[bbox_index]["reviewed_by"] = None
            modified = True
            discarded += 1

        if modified:
            ocr_result.bbox_data = bbox_list
            flag_modified(ocr_result, "bbox_data")
            db.commit()
            # Erstelle Quality-Job für diese Seite
            _create_quality_job_if_needed(page_id, db)

    # Schritt 2: Review-Jobs erstellen (ein Job pro Seite)
    for page_id in bboxes_by_page:
        page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
        if not page:
            continue

        # Prüfe ob bereits ein Review-Job existiert
        existing_job = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_page_id == page_id,
                OCRJob.job_type == "bbox_review",
                OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
            )
            .first()
        )

        if existing_job:
            jobs_existing += 1
        else:
            # Erstelle neuen Review-Job mit höherer Priorität als Quality-Jobs
            # (niedrigere Zahl = höhere Priorität)
            review_job = OCRJob(
                document_id=page.document_id,
                document_page_id=page_id,
                job_type="bbox_review",
                status=OCRJobStatus.PENDING,
                language="deu+eng",
                use_correction=False,
                progress=0.0,
                priority=-1,  # Höhere Priorität als Quality-Jobs (priority=1)
            )
            db.add(review_job)
            db.commit()
            jobs_created += 1

    return {
        "success": True,
        "discarded": discarded,
        "jobs_created": jobs_created,
        "jobs_existing": jobs_existing,
        "errors": errors,
    }


@router.post("/batch-delete")
async def batch_delete(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Löscht mehrere BBoxen in einem Batch.

    Args:
        request: Liste von BBox-Referenzen

    Returns:
        {"success": True, "deleted": int, "errors": [...]}
    """
    deleted = 0
    errors = []

    # Ermittle BBoxen (entweder aus Filter oder expliziter Liste)
    try:
        bbox_refs = _get_filtered_bboxes_from_request(request, db)
        logger.info(f"Batch-Delete: Gefilterte BBoxen gefunden: {len(bbox_refs)}")
    except Exception as e:
        logger.error(f"Batch-Delete: Fehler beim Filtern der BBoxen: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fehler beim Filtern der BBoxen: {e!s}")
    
    if not bbox_refs:
        logger.info("Batch-Delete: Keine BBoxen gefunden, die den Filtern entsprechen")
        return {"success": True, "deleted": 0, "errors": []}

    # Gruppiere BBoxen nach page_id
    from collections import defaultdict

    bboxes_by_page = defaultdict(list)
    for page_id, bbox_index in bbox_refs:
        bboxes_by_page[page_id].append(bbox_index)
    
    logger.info(f"Batch-Delete: Verarbeite {len(bboxes_by_page)} Seiten mit insgesamt {len(bbox_refs)} BBoxen")

    for page_id, bbox_indices in bboxes_by_page.items():
        page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
        if not page:
            # Zusammenfassende Fehlermeldung statt für jeden Index
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"Seite {page_id} nicht gefunden ({len(bbox_indices)} BBoxen betroffen)",
                }
            )
            continue

        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == page_id,
                OCRResult.source == OCRSource.OLLAMA_VISION,
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )

        if not ocr_result or not ocr_result.bbox_data:
            # Zusammenfassende Fehlermeldung statt für jeden Index
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"Keine BBox-Daten für Seite {page_id} gefunden ({len(bbox_indices)} BBoxen betroffen)",
                }
            )
            continue

        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data.copy()

        # Sortiere Indizes in umgekehrter Reihenfolge, damit Löschung von hinten nach vorne erfolgt
        sorted_indices = sorted(set(bbox_indices), reverse=True)
        valid_indices = [idx for idx in sorted_indices if 0 <= idx < len(bbox_list)]

        # Fehler nur loggen, nicht für jeden einzelnen Index zurückgeben (zu viele Fehler)
        invalid_count = len(sorted_indices) - len(valid_indices)
        if invalid_count > 0:
            # Logge nur einen repräsentativen Fehler statt tausender einzelner Fehler
            logger.warning(
                f"Batch-Delete: {invalid_count} von {len(sorted_indices)} BBox-Indizes "
                f"außerhalb des Bereichs für Seite {page_id} (BBox-Liste hat {len(bbox_list)} Einträge)"
            )
            # Füge nur einen zusammenfassenden Fehler hinzu statt für jeden Index
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"{invalid_count} BBox-Indizes außerhalb des Bereichs (Seite hat {len(bbox_list)} BBoxen)",
                }
            )

        # Lösche BBoxen (von hinten nach vorne)
        try:
            if not valid_indices:
                logger.debug(f"Batch-Delete: Keine gültigen Indizes für Seite {page_id}")
                continue
                
            for bbox_index in valid_indices:
                if bbox_index < 0 or bbox_index >= len(bbox_list):
                    logger.warning(f"Batch-Delete: Index {bbox_index} außerhalb des Bereichs für Seite {page_id} (Liste hat {len(bbox_list)} Einträge)")
                    continue
                bbox_list.pop(bbox_index)
                deleted += 1

            if deleted > 0:
                ocr_result.bbox_data = bbox_list
                flag_modified(ocr_result, "bbox_data")
                db.commit()
                # Refresh nach Commit, um sicherzustellen, dass die Daten konsistent sind
                db.refresh(ocr_result)
                logger.info(f"Batch-Delete: {len(valid_indices)} BBoxen von Seite {page_id} gelöscht (gesamt gelöscht: {deleted})")
                # Erstelle Quality-Job für diese Seite, um quality_metrics zu aktualisieren
                _create_quality_job_if_needed(page_id, db)
        except Exception as e:
            logger.error(f"Batch-Delete: Fehler beim Löschen von BBoxen auf Seite {page_id}: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Batch-Delete: Fehler beim Rollback für Seite {page_id}: {rollback_error}")
            errors.append(
                {
                    "page_id": page_id,
                    "bbox_index": None,
                    "error": f"Fehler beim Löschen: {e!s}",
                }
            )
            # Weiter mit nächster Seite statt abzubrechen
            continue

    logger.info(f"Batch-Delete: Abgeschlossen. {deleted} BBoxen gelöscht, {len(errors)} Fehler")
    return {"success": True, "deleted": deleted, "errors": errors}


@router.get("/pages/{page_id}/bboxes/{bbox_index}/crop-preview")
async def get_bbox_crop_preview(
    page_id: int,
    bbox_index: int,
    db: Session = Depends(get_db),
):
    """
    Hole Preview-Bild der gecroppten BBox
    - Sucht zuerst nach gespeichertem Debug-Crop
    - Falls nicht vorhanden, erstellt es on-the-fly

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste

    Returns:
        FileResponse mit dem Crop-Bild
    """
    import tempfile

    from fastapi.responses import FileResponse

    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole Dokument
    document = db.query(Document).filter(Document.id == page.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    bbox_item = bbox_list[bbox_index]

    # Erstelle Preview-Bild immer on-the-fly mit Padding und Box-Grenzen
    # (ignoriere Debug-Crops, da diese kein Padding haben)
    # Verwende die GLEICHE Logik wie in bbox_ocr.py
    try:
        from src.rotary_archiv.utils.file_handler import get_file_path
        from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

        # Lade Seitenbild
        pdf_path = get_file_path(document.file_path)
        if not pdf_path.exists():
            raise HTTPException(
                status_code=404, detail=f"PDF-Datei nicht gefunden: {pdf_path}"
            )

        # Hole OCR-Bild-Dimensionen (wie in bbox_ocr.py)
        ocr_image_width = ocr_result.image_width
        ocr_image_height = ocr_result.image_height

        # Verwende das gleiche DPI wie beim ursprünglichen OCR
        dpi = settings.pdf_extraction_dpi

        # Versuche DPI aus Bild-Dimensionen abzuleiten (wie in bbox_ocr.py)
        if ocr_image_width and ocr_image_height:
            # Extrahiere mit Standard-DPI
            page_image = extract_page_as_image(str(pdf_path), page.page_number, dpi=dpi)
            extracted_width, extracted_height = page_image.size

            # Toleranz für Dimensionen-Unterschiede (in Pixeln)
            dimension_tolerance = 10  # Pixel

            width_diff = abs(extracted_width - ocr_image_width)
            height_diff = abs(extracted_height - ocr_image_height)

            # Wenn Dimensionen außerhalb der Toleranz liegen, versuche DPI anzupassen
            if width_diff > dimension_tolerance or height_diff > dimension_tolerance:
                # Berechne geschätztes DPI basierend auf Verhältnis
                width_ratio = (
                    ocr_image_width / extracted_width if extracted_width > 0 else 1.0
                )
                height_ratio = (
                    ocr_image_height / extracted_height if extracted_height > 0 else 1.0
                )
                estimated_dpi = int(dpi * ((width_ratio + height_ratio) / 2))

                logger.info(
                    f"Crop-Preview: Bild-Dimensionen weichen ab, verwende geschätztes DPI {estimated_dpi}"
                )

                # Versuche mit geschätztem DPI
                page_image = extract_page_as_image(
                    str(pdf_path), page.page_number, dpi=estimated_dpi
                )
        else:
            page_image = extract_page_as_image(str(pdf_path), page.page_number, dpi=dpi)

        # Hole bbox_pixel Koordinaten
        bbox_pixel = bbox_item.get("bbox_pixel")
        if not bbox_pixel or len(bbox_pixel) != 4:
            raise HTTPException(
                status_code=400, detail="Ungültige bbox_pixel-Koordinaten"
            )

        # Wende den gleichen X-Skalierungsfaktor an wie in bbox_ocr.py (0.7)
        # Dies korrigiert die X-Achsen-Ausrichtung für das Cropping
        bbox_pixel_adjusted = [
            int(bbox_pixel[0] * 0.7),  # x1
            bbox_pixel[1],  # y1 (unverändert)
            int(bbox_pixel[2] * 0.7),  # x2
            bbox_pixel[3],  # y2 (unverändert)
        ]

        # Padding für Preview (20 Pixel)
        padding = 20

        # Berechne Crop-Bereich mit Padding (kann über Seitenrand hinausgehen)
        x1, y1, x2, y2 = bbox_pixel_adjusted
        crop_x1 = x1 - padding
        crop_y1 = y1 - padding
        crop_x2 = x2 + padding
        crop_y2 = y2 + padding

        # Berechne tatsächliche Bild-Dimensionen für Crop
        crop_width = crop_x2 - crop_x1
        crop_height = crop_y2 - crop_y1

        logger.debug(
            f"Crop-Preview für BBox {bbox_index}: "
            f"Box=({x1},{y1},{x2},{y2}), "
            f"Crop=({crop_x1},{crop_y1},{crop_x2},{crop_y2}), "
            f"Bild-Größe=({page_image.width},{page_image.height}), "
            f"Crop-Größe=({crop_width},{crop_height})"
        )

        # Erstelle neues Bild mit grauem Hintergrund
        from PIL import Image, ImageDraw

        cropped_image = Image.new(
            "RGB", (crop_width, crop_height), color=(200, 200, 200)
        )

        # Berechne Offset für das Seitenbild im Crop-Bereich
        # Wenn crop_x1 < 0, dann ist Padding links vom Seitenrand -> Offset ist -crop_x1
        # Wenn crop_y1 < 0, dann ist Padding oben vom Seitenrand -> Offset ist -crop_y1
        image_offset_x = -crop_x1 if crop_x1 < 0 else 0
        image_offset_y = -crop_y1 if crop_y1 < 0 else 0

        # Berechne welche Teile des Seitenbilds sichtbar sind
        source_x1 = max(0, crop_x1)
        source_y1 = max(0, crop_y1)
        source_x2 = min(page_image.width, crop_x2)
        source_y2 = min(page_image.height, crop_y2)

        # Croppe sichtbaren Teil des Seitenbilds
        if source_x2 > source_x1 and source_y2 > source_y1:
            visible_part = page_image.crop((source_x1, source_y1, source_x2, source_y2))
            # Berechne Ziel-Position im Crop-Bild
            # Wenn crop_x1 < 0, dann startet das Bild bei -crop_x1 im Crop-Bild
            dest_x = image_offset_x
            dest_y = image_offset_y

            logger.debug(
                f"Crop-Preview Einfügen: "
                f"source=({source_x1},{source_y1},{source_x2},{source_y2}), "
                f"dest=({dest_x},{dest_y}), "
                f"visible_part.size={visible_part.size}"
            )

            # Füge sichtbaren Teil in das Crop-Bild ein
            cropped_image.paste(visible_part, (dest_x, dest_y))

        # Zeichne Box-Grenzen auf das Bild
        draw = ImageDraw.Draw(cropped_image)

        # Berechne relative Koordinaten für die aktuelle Box (bezogen auf den Crop-Bereich)
        current_box_x1 = x1 - crop_x1
        current_box_y1 = y1 - crop_y1
        current_box_x2 = x2 - crop_x1
        current_box_y2 = y2 - crop_y1

        # Zeichne Grenzen der aktuellen Box (dick, rot)
        draw.rectangle(
            [current_box_x1, current_box_y1, current_box_x2, current_box_y2],
            outline="red",
            width=3,
        )

        # Zeichne Grenzen der umliegenden Boxen (dünn, blau)
        for idx, other_bbox in enumerate(bbox_list):
            if idx == bbox_index:
                continue  # Überspringe aktuelle Box

            other_bbox_pixel = other_bbox.get("bbox_pixel")
            if not other_bbox_pixel or len(other_bbox_pixel) != 4:
                continue

            # Wende X-Skalierung an
            other_x1 = int(other_bbox_pixel[0] * 0.7)
            other_y1 = other_bbox_pixel[1]
            other_x2 = int(other_bbox_pixel[2] * 0.7)
            other_y2 = other_bbox_pixel[3]

            # Prüfe ob Box im sichtbaren Bereich liegt (mit etwas Toleranz)
            if (
                other_x2 >= crop_x1 - 10
                and other_x1 <= crop_x2 + 10
                and other_y2 >= crop_y1 - 10
                and other_y1 <= crop_y2 + 10
            ):
                # Berechne relative Koordinaten
                rel_x1 = other_x1 - crop_x1
                rel_y1 = other_y1 - crop_y1
                rel_x2 = other_x2 - crop_x1
                rel_y2 = other_y2 - crop_y1

                # Zeichne Box-Grenze (dünn, blau)
                draw.rectangle(
                    [rel_x1, rel_y1, rel_x2, rel_y2],
                    outline="blue",
                    width=1,
                )

        # Speichere temporär
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            cropped_image.save(temp_file.name, "PNG")
            temp_path = temp_file.name

        return FileResponse(
            path=temp_path,
            media_type="image/png",
            filename=f"bbox_{bbox_index}_crop.png",
        )
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Crop-Previews: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Fehler beim Erstellen des Crop-Previews: {e!s}"
        ) from e


@router.post("/pages/{page_id}/bboxes/{bbox_index}/save-reviewed")
async def save_reviewed_bbox(
    page_id: int,
    bbox_index: int,
    request: SaveReviewedBBoxRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Speichere manuell überprüften und bearbeiteten Text einer BBox
    - Aktualisiert den Text
    - Setzt review_status auf "confirmed"
    - Setzt reviewed_at und reviewed_by

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste
        request: Request mit reviewed_text
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data.copy()

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    # Aktualisiere BBox: Text ändern und als confirmed markieren
    bbox_list[bbox_index]["text"] = request.reviewed_text
    bbox_list[bbox_index]["review_status"] = "confirmed"
    bbox_list[bbox_index]["reviewed_at"] = datetime.now().isoformat()
    bbox_list[bbox_index]["reviewed_by"] = None  # TODO: User-ID aus Session

    # Speichere zurück - SQLAlchemy muss über Änderung an JSON-Feld informiert werden
    ocr_result.bbox_data = bbox_list
    flag_modified(ocr_result, "bbox_data")
    db.commit()

    # Erstelle Quality-Job für diese Seite
    _create_quality_job_if_needed(page_id, db)

    return {
        "success": True,
        "message": f"BBox {bbox_index} als geprüft gespeichert",
        "bbox": bbox_list[bbox_index],
    }


@router.post("/pages/{page_id}/bboxes/{bbox_index}/test-review")
async def test_bbox_review(
    page_id: int,
    bbox_index: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Manueller Test-Review für eine einzelne BBox
    - Schneidet BBox aus
    - Führt OCR durch
    - Speichert Crop-Bild im Debug-Ordner

    Args:
        page_id: ID der Seite
        bbox_index: Index der BBox in der Liste

    Returns:
        {
            "success": True,
            "crop_path": "...",
            "tesseract": {...},
            "ollama_vision": {...},
            "comparison": {...}
        }
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole Dokument
    document = db.query(Document).filter(Document.id == page.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=404, detail="Keine BBox-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data

    if bbox_index < 0 or bbox_index >= len(bbox_list):
        raise HTTPException(status_code=404, detail="BBox-Index außerhalb des Bereichs")

    bbox_item = bbox_list[bbox_index]

    # Stelle sicher, dass Debug-Ordner existiert
    from pathlib import Path

    from src.rotary_archiv.config import settings

    debug_dir = Path(settings.debug_bbox_crops_path)
    debug_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Debug-Ordner sichergestellt: {debug_dir}")

    # Führe BBox-OCR durch
    import asyncio

    from src.rotary_archiv.ocr.bbox_ocr import process_bbox_ocr

    try:
        ocr_results = await process_bbox_ocr(
            db=db,
            document_page_id=page_id,
            bbox_item=bbox_item,
            pdf_path=document.file_path,
            page_number=page.page_number,
            ocr_models=["tesseract", "ollama_vision"],
            bbox_index=bbox_index,  # Für Debug-Dateinamen
        )
    except asyncio.CancelledError:
        # Wird beim Shutdown abgebrochen - das ist normal
        raise HTTPException(
            status_code=503, detail="Service wird heruntergefahren"
        ) from None

    # Finde das gespeicherte Debug-Bild
    from pathlib import Path

    from src.rotary_archiv.config import settings

    debug_dir = Path(settings.debug_bbox_crops_path)
    debug_files = list(debug_dir.glob(f"page_{page_id}_bbox_*.png"))
    latest_crop = (
        max(debug_files, key=lambda p: p.stat().st_mtime) if debug_files else None
    )

    return {
        "success": True,
        "bbox_index": bbox_index,
        "bbox_text": bbox_item.get("text", ""),
        "crop_path": str(latest_crop) if latest_crop else None,
        "tesseract": ocr_results.get("tesseract"),
        "ollama_vision": ocr_results.get("ollama_vision"),
        "auto_confirmed": ocr_results.get("auto_confirmed", False),
        "differences": ocr_results.get("differences", []),
        "error": ocr_results.get("error"),
    }


@router.post("/pages/{page_id}/create-review-job")
async def create_review_job(
    page_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Erstelle einen Review-Job für die gesamte Seite (verarbeitet alle BBoxes)

    Args:
        page_id: ID der Seite

    Returns:
        {
            "success": True,
            "job_id": 123,
            "message": "Review-Job erstellt"
        }
    """
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Prüfe ob bereits ein Review-Job für diese Seite existiert (pending/running)
    existing_job = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_page_id == page_id,
            OCRJob.job_type == "bbox_review",
            OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
        )
        .first()
    )

    if existing_job:
        return {
            "success": False,
            "message": "Review-Job für diese Seite existiert bereits",
            "job_id": existing_job.id,
        }

    # Prüfe ob BBox-Daten vorhanden sind
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result or not ocr_result.bbox_data:
        raise HTTPException(
            status_code=400,
            detail="Keine BBox-Daten für diese Seite gefunden. OCR muss zuerst durchgeführt werden.",
        )

    # Parse bbox_data um Anzahl zu prüfen
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data

    if not isinstance(bbox_list, list) or len(bbox_list) == 0:
        raise HTTPException(
            status_code=400, detail="Keine BBoxes auf dieser Seite vorhanden"
        )

    # Filtere ignorierte BBoxes heraus (diese müssen nicht gereviewt werden)
    bboxes_to_review = [
        bbox for bbox in bbox_list if bbox.get("review_status") != "ignored"
    ]

    if len(bboxes_to_review) == 0:
        raise HTTPException(
            status_code=400,
            detail="Alle BBoxes sind bereits ignoriert oder verarbeitet",
        )

    # Erstelle Review-Job mit höherer Priorität als Quality-Jobs
    review_job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="bbox_review",
        status=OCRJobStatus.PENDING,
        language="deu+eng",
        use_correction=False,  # Review-Jobs benötigen keine GPT-Korrektur
        progress=0.0,
        priority=-1,  # Höhere Priorität als Quality-Jobs (priority=1)
    )

    db.add(review_job)
    db.commit()
    db.refresh(review_job)

    return {
        "success": True,
        "job_id": review_job.id,
        "message": f"Review-Job für {len(bbox_list)} BBoxes erstellt",
    }


@router.post("/pages/{page_id}/bboxes/add")
async def add_new_bbox(
    page_id: int,
    request: AddBBoxRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Füge eine neue manuell erstellte BBox hinzu
    - Erstellt neue BBox mit Status "new"
    - Fügt sie zu bbox_data hinzu
    - Erstellt OCR-Job mit hoher Priorität

    Args:
        page_id: ID der Seite
        request: Request mit bbox_pixel [x1, y1, x2, y2] (bezogen auf OCR-Bild)

    Returns:
        {
            "success": True,
            "bbox_index": 123,
            "job_id": 456,
            "message": "Neue BBox hinzugefügt"
        }
    """
    bbox_pixel = request.bbox_pixel
    # Hole Seite
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")

    # Hole OCRResult
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.OLLAMA_VISION,
        )
        .order_by(OCRResult.created_at.desc())
        .first()
    )

    if not ocr_result:
        raise HTTPException(
            status_code=404, detail="Keine OCR-Daten für diese Seite gefunden"
        )

    # Parse bbox_data
    if isinstance(ocr_result.bbox_data, str):
        bbox_list = json.loads(ocr_result.bbox_data)
    else:
        bbox_list = ocr_result.bbox_data.copy() if ocr_result.bbox_data else []

    # Erstelle neue BBox
    new_bbox = {
        "text": "",  # Wird nach OCR gefüllt
        "bbox": [],  # Relative Koordinaten (optional)
        "bbox_pixel": bbox_pixel,
        "review_status": "new",  # Markiere als neu
        "reviewed_at": None,
        "reviewed_by": None,
        "ocr_results": None,
        "differences": [],
    }

    # Füge neue BBox hinzu
    bbox_list.append(new_bbox)
    new_bbox_index = len(bbox_list) - 1

    # Speichere zurück
    ocr_result.bbox_data = bbox_list
    flag_modified(ocr_result, "bbox_data")
    db.commit()

    # Erstelle OCR-Job mit hoher Priorität
    # Finde die niedrigste aktuelle Priorität (höchste Priorität = niedrigste Zahl)
    from sqlalchemy import func

    min_priority = (
        db.query(func.min(OCRJob.priority))
        .filter(OCRJob.status == OCRJobStatus.PENDING)
        .scalar()
    ) or 0

    # Setze Priorität auf niedrigste - 1 (höchste Priorität)
    review_job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="bbox_review",
        status=OCRJobStatus.PENDING,
        language="deu+eng",
        use_correction=False,
        progress=0.0,
        priority=min_priority - 1,  # Höchste Priorität
    )

    db.add(review_job)
    db.commit()
    db.refresh(review_job)

    return {
        "success": True,
        "bbox_index": new_bbox_index,
        "job_id": review_job.id,
        "message": "Neue BBox hinzugefügt und OCR-Job erstellt",
    }


# HINWEIS: +X (Multibox-Region) ist wegen Bugs deaktiviert – Frontend-Button ausgeblendet.
# Die Logik bleibt für spätere Reparatur erhalten.
@router.post("/pages/{page_id}/bboxes/add-multiple")
async def add_multiple_bboxes(
    page_id: int,
    request: AddMultipleBBoxesRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Erkenne automatisch mehrere BBoxen in einem gezeichneten Bereich.
    - Croppt den Bereich aus der Seite
    - Führt OCR mit BBox-Extraktion auf dem gecroppten Bild durch
    - Transformiert gefundene BBox-Koordinaten zurück auf die gesamte Seite
    - Fügt alle gefundenen BBoxen zu bbox_data hinzu
    - Erstellt Review-Jobs für die neuen BBoxen

    Args:
        page_id: ID der Seite
        request: Request mit bbox_pixel [x1, y1, x2, y2] (bezogen auf OCR-Bild)

    Returns:
        {
            "success": True,
            "bboxes_added": 5,
            "job_id": 456,
            "message": "5 Boxen erkannt und hinzugefügt"
        }
    """
    logger.info(f"Add-Multiple-BBox: Funktion aufgerufen für Seite {page_id}")
    
    try:
        bbox_pixel = request.bbox_pixel
        logger.info(f"Add-Multiple-BBox: Request-Daten erhalten: bbox_pixel={bbox_pixel}")
        
        # Validiere bbox_pixel
        if len(bbox_pixel) != 4:
            logger.error(f"Add-Multiple-BBox: Ungültige bbox_pixel-Länge: {len(bbox_pixel)}")
            raise HTTPException(status_code=400, detail="bbox_pixel muss 4 Werte haben [x1, y1, x2, y2]")
        
        x1, y1, x2, y2 = bbox_pixel
        logger.info(
            f"Add-Multiple-BBox: Empfangene Koordinaten: [{x1}, {y1}, {x2}, {y2}]"
        )
        
        if x1 >= x2 or y1 >= y2:
            raise HTTPException(status_code=400, detail="Ungültige Koordinaten: x1 < x2 und y1 < y2 erforderlich")
        
        # Hole Seite
        page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
        if not page:
            raise HTTPException(status_code=404, detail="Seite nicht gefunden")

        # Hole Dokument
        document = db.query(Document).filter(Document.id == page.document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

        # Hole OCRResult für Bild-Dimensionen
        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == page_id,
                OCRResult.source == OCRSource.OLLAMA_VISION,
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )

        if not ocr_result:
            raise HTTPException(
                status_code=404, detail="Keine OCR-Daten für diese Seite gefunden"
            )

        ocr_image_width = ocr_result.image_width
        ocr_image_height = ocr_result.image_height
        
        if not ocr_image_width or not ocr_image_height:
            raise HTTPException(
                status_code=400, detail="OCR-Bild-Dimensionen nicht verfügbar"
            )
        
        logger.info(
            f"Add-Multiple-BBox: OCR-Bild-Dimensionen: {ocr_image_width}x{ocr_image_height}, "
            f"Empfangene Koordinaten: [{x1}, {y1}, {x2}, {y2}], "
            f"Breite: {x2 - x1}, Höhe: {y2 - y1}"
        )
        
        # Speichere originale Koordinaten für die Box-Speicherung
        # Die Beschneidung wird nur für das Cropping verwendet
        x1_original = x1
        y1_original = y1
        x2_original = x2
        y2_original = y2
        
        # Beschneide Koordinaten auf Bildgrenzen (mit kleiner Toleranz für Rundungsfehler)
        # Diese beschrittenen Koordinaten werden nur für das Cropping verwendet
        tolerance = 10  # Pixel Toleranz für Rundungsfehler
        x1_before = x1
        y1_before = y1
        x2_before = x2
        y2_before = y2
        
        x1 = max(0, min(x1, ocr_image_width + tolerance))
        y1 = max(0, min(y1, ocr_image_height + tolerance))
        x2 = max(x1 + 1, min(x2, ocr_image_width + tolerance))
        y2 = max(y1 + 1, min(y2, ocr_image_height + tolerance))
        
        # Stelle sicher, dass Koordinaten innerhalb Bildgrenzen liegen (nach Beschneidung)
        x1 = max(0, min(x1, ocr_image_width - 1))
        y1 = max(0, min(y1, ocr_image_height - 1))
        x2 = max(x1 + 1, min(x2, ocr_image_width))
        y2 = max(y1 + 1, min(y2, ocr_image_height))
        
        # Prüfe, dass BBox noch gültig ist nach Beschneidung
        if x1 >= x2 or y1 >= y2:
            raise HTTPException(
                status_code=400,
                detail=f"BBox-Koordinaten ungültig nach Beschneidung: [{x1}, {y1}, {x2}, {y2}]"
            )
        
        # Logge Änderungen durch Beschneidung
        if x1 != x1_before or y1 != y1_before or x2 != x2_before or y2 != y2_before:
            logger.warning(
                f"Add-Multiple-BBox: Koordinaten wurden beschnitten: "
                f"Vorher: [{x1_before}, {y1_before}, {x2_before}, {y2_before}], "
                f"Nachher: [{x1}, {y1}, {x2}, {y2}], "
                f"Breite: {x2_before - x1_before} -> {x2 - x1}, "
                f"Höhe: {y2_before - y1_before} -> {y2 - y1}"
            )
        
        logger.info(
            f"Add-Multiple-BBox: Koordinaten nach Beschneidung: [{x1}, {y1}, {x2}, {y2}], "
            f"Breite: {x2 - x1}, Höhe: {y2 - y1}"
        )
        
        # Prüfe Verfügbarkeit von PIL
        if not PIL_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="PIL/Pillow ist nicht verfügbar"
            )
        
        # Lade Original-Bild der Seite
        logger.info(f"Lade Original-Bild für Seite {page_id} (file_path: {page.file_path})")
        # Verwende ähnliche Logik wie in bbox_ocr.py
        if page.file_path:
            # Extrahierte Seite: Datei laden
            file_path = get_file_path(page.file_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"Seiten-Datei nicht gefunden: {file_path}"
                )
            
            is_img = (
                page.file_type
                and page.file_type.lower() in ("image/png", "image/jpeg", "image/jpg")
            ) or str(file_path).lower().endswith((".png", ".jpg", ".jpeg"))
            
            if is_img:
                full_image = Image.open(file_path).convert("RGB")
            else:
                # PDF-Seite
                try:
                    from pdf2image import convert_from_path
                except ImportError:
                    raise HTTPException(
                        status_code=503, detail="pdf2image ist für PDF-Extraktion nötig"
                    )
                
                convert_kwargs = {
                    "first_page": page.page_number,
                    "last_page": page.page_number,
                    "dpi": settings.pdf_extraction_dpi,
                }
                if settings.poppler_path:
                    pp = Path(settings.poppler_path)
                    if pp.exists():
                        convert_kwargs["poppler_path"] = str(pp)
                images = convert_from_path(str(file_path), **convert_kwargs)
                if not images:
                    raise HTTPException(
                        status_code=500, detail="PDF konnte nicht zu Bild konvertiert werden"
                    )
                full_image = images[0]
        else:
            # Virtuelle Seite: aus PDF extrahieren
            pdf_path = get_file_path(document.file_path)
            if not pdf_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"PDF nicht gefunden: {pdf_path}"
                )
            full_image = extract_page_as_image(
                str(pdf_path), page.page_number, dpi=settings.pdf_extraction_dpi
            )
        
        # Deskew anwenden falls gesetzt
        if page.deskew_angle is not None:
            from src.rotary_archiv.utils.image_utils import deskew_image
            full_image = deskew_image(full_image, page.deskew_angle)
        
        # Resize auf OCR-Bildgröße falls abweichend
        full_image_width, full_image_height = full_image.size
        if full_image_width != ocr_image_width or full_image_height != ocr_image_height:
            # Skaliere Bild auf OCR-Dimensionen
            full_image = full_image.resize(
                (ocr_image_width, ocr_image_height), Image.Resampling.LANCZOS
            )
            logger.info(
                f"Bild skaliert von {full_image_width}x{full_image_height} "
                f"auf {ocr_image_width}x{ocr_image_height}"
            )
        
        # Wende den gleichen X-Skalierungsfaktor an wie in bbox_ocr.py (0.7)
        # Dies korrigiert die X-Achsen-Ausrichtung für das Cropping
        # WICHTIG: Verwende ORIGINALE Koordinaten für die Box-Speicherung,
        # aber angepasste Koordinaten für das Cropping (wie bei +1 Box)
        bbox_pixel_adjusted = [
            int(x1_original * 0.7),  # x1 (wie in bbox_ocr.py)
            y1_original,  # y1 (unverändert)
            int(x2_original * 0.7),  # x2 (wie in bbox_ocr.py)
            y2_original,  # y2 (unverändert)
        ]
        
        region_width = x2_original - x1_original
        region_height = y2_original - y1_original
        
        logger.info(
            f"Add-Multiple-BBox: Original-Koordinaten (für Speicherung)=[{x1_original}, {y1_original}, {x2_original}, {y2_original}], "
            f"Region-Größe={region_width}x{region_height}, "
            f"Angepasste Koordinaten (für Cropping, X*0.7)=[{bbox_pixel_adjusted[0]}, {bbox_pixel_adjusted[1]}, {bbox_pixel_adjusted[2]}, {bbox_pixel_adjusted[3]}], "
            f"Crop-Größe={bbox_pixel_adjusted[2] - bbox_pixel_adjusted[0]}x{bbox_pixel_adjusted[3] - bbox_pixel_adjusted[1]}, "
            f"Bild-Größe={full_image.width}x{full_image.height}"
        )
        
        # Warnung wenn Region sehr schmal ist (kann zu OCR-Problemen führen)
        if region_height < 30:
            logger.warning(
                f"Add-Multiple-BBox: Region ist sehr schmal (Höhe={region_height} Pixel). "
                f"Das OCR-LLM könnte Probleme haben, Boxen korrekt zu erkennen. "
                f"Empfehlung: Mindestens 30-50 Pixel Höhe für bessere Ergebnisse."
            )
        
        # Stelle sicher, dass Koordinaten innerhalb Bildgrenzen liegen
        bbox_pixel_adjusted[0] = max(0, min(bbox_pixel_adjusted[0], full_image.width - 1))
        bbox_pixel_adjusted[1] = max(0, min(bbox_pixel_adjusted[1], full_image.height - 1))
        bbox_pixel_adjusted[2] = max(bbox_pixel_adjusted[0] + 1, min(bbox_pixel_adjusted[2], full_image.width))
        bbox_pixel_adjusted[3] = max(bbox_pixel_adjusted[1] + 1, min(bbox_pixel_adjusted[3], full_image.height))
        
        # Croppe Bild zu bbox_pixel Bereich
        logger.info(
            f"Croppe Bild: Original=[{x1_original}, {y1_original}, {x2_original}, {y2_original}], "
            f"Nach Clipping=[{bbox_pixel_adjusted[0]}, {bbox_pixel_adjusted[1]}, "
            f"{bbox_pixel_adjusted[2]}, {bbox_pixel_adjusted[3]}], "
            f"Crop-Größe={bbox_pixel_adjusted[2] - bbox_pixel_adjusted[0]}x{bbox_pixel_adjusted[3] - bbox_pixel_adjusted[1]}, "
            f"Bild-Größe={full_image.width}x{full_image.height}"
        )
        cropped_image = full_image.crop(
            (
                bbox_pixel_adjusted[0],
                bbox_pixel_adjusted[1],
                bbox_pixel_adjusted[2],
                bbox_pixel_adjusted[3],
            )
        )
        
        logger.info(f"Gecropptes Bild-Größe: {cropped_image.width}x{cropped_image.height}")
        
        # Speichere Crop im Projektordner, damit API und Worker dieselbe Datei finden
        # (Temp-Pfade können pro Prozess unterschiedlich oder nach Reboot weg sein)
        multibox_crops_dir = Path("data/multibox_crops")
        multibox_crops_dir.mkdir(parents=True, exist_ok=True)
        crop_filename = f"page_{page_id}_{uuid.uuid4().hex[:12]}.png"
        temp_crop_path = str((multibox_crops_dir / crop_filename).resolve())
        cropped_image.save(temp_crop_path, "PNG")
        logger.info(f"Gecropptes Bild gespeichert für Worker: {temp_crop_path}")
        
        # Erstelle sofort eine vorläufige Box - OCR wird vom Worker durchgeführt
        # Verwende ORIGINALE Koordinaten für die Box-Speicherung (wie bei add_new_bbox)
        logger.info(
            f"Erstelle vorläufige Multibox-Region für Bereich "
            f"[Original: {x1_original}, {y1_original}, {x2_original}, {y2_original}], "
            f"[Für Cropping: {x1}, {y1}, {x2}, {y2}]"
        )
        
        # Parse bbox_data
        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data.copy() if ocr_result.bbox_data else []
        
        # Berechne relative Koordinaten (0.0-1.0) bezogen auf OCR-Bild
        # Verwende ORIGINALE Koordinaten (wie bei add_new_bbox)
        bbox_normalized = []
        if ocr_image_width > 0 and ocr_image_height > 0:
            bbox_normalized = [
                x1_original / ocr_image_width,  # x_min (relativ)
                y1_original / ocr_image_height,  # y_min (relativ)
                x2_original / ocr_image_width,  # x_max (relativ)
                y2_original / ocr_image_height,  # y_max (relativ)
            ]
        
        # Erstelle vorläufige Box mit Marker für Multibox-Region
        # Verwende ORIGINALE Koordinaten für bbox_pixel (wie bei add_new_bbox)
        temp_bbox = {
            "text": "[Wird verarbeitet...]",  # Platzhalter-Text, wird durch Review-Job gefüllt
            "bbox": bbox_normalized,
            "bbox_pixel": [x1_original, y1_original, x2_original, y2_original],
            "review_status": "new",
            "reviewed_at": None,
            "reviewed_by": None,
            "ocr_results": None,
            "differences": [],
            "multibox_region": True,  # Marker: Dies ist eine Multibox-Region
            "multibox_crop_path": temp_crop_path,  # Pfad zum gecroppten Bild für den Worker
        }
        
        bbox_list.append(temp_bbox)
        
        # Speichere zurück
        ocr_result.bbox_data = bbox_list
        flag_modified(ocr_result, "bbox_data")
        db.commit()
        db.refresh(ocr_result)
        
        logger.info(
            f"Vorläufige Multibox-Region erstellt: "
            f"bbox_pixel=[{x1_original}, {y1_original}, {x2_original}, {y2_original}] "
            f"(Original), Gesamt-BBoxen: {len(bbox_list)}"
        )
        
        # Erstelle Review-Job für die vorläufige Box
        existing_job = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_page_id == page_id,
                OCRJob.job_type == "bbox_review",
                OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
            )
            .first()
        )
        
        job_id = None
        if not existing_job:
            from sqlalchemy import func
            
            min_priority = (
                db.query(func.min(OCRJob.priority))
                .filter(OCRJob.status == OCRJobStatus.PENDING)
                .scalar()
            ) or 0
            
            review_job = OCRJob(
                document_id=page.document_id,
                document_page_id=page_id,
                job_type="bbox_review",
                status=OCRJobStatus.PENDING,
                language="deu+eng",
                use_correction=False,
                progress=0.0,
                priority=min_priority - 1,  # Höchste Priorität
            )
            
            db.add(review_job)
            db.commit()
            db.refresh(review_job)
            job_id = review_job.id
        
        # Erstelle Quality-Job für die Seite
        _create_quality_job_if_needed(page_id, db)
        
        return {
            "success": True,
            "bboxes_added": 1,  # Eine vorläufige Box wurde erstellt
            "job_id": job_id,
            "message": "Vorläufige Box erstellt - OCR wird im Hintergrund durchgeführt",
        }
            
    except HTTPException:
        # HTTPExceptions werden direkt weitergegeben
        raise
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten der Multibox-Region: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Verarbeiten der Multibox-Region: {str(e)}"
        )
    finally:
        # Lösche temporäre Datei nur wenn sie nicht vom Worker verwendet wird
        # (Der Worker löscht sie selbst nach der Verarbeitung)
        # Hier löschen wir sie nur im Fehlerfall
        if 'temp_crop_path' in locals() and temp_crop_path:
            try:
                # Prüfe ob Datei existiert und ob sie noch verwendet wird
                crop_path = Path(temp_crop_path)
                if crop_path.exists():
                    # Im Erfolgsfall wird die Datei vom Worker verwendet, daher nicht löschen
                    # Nur im Fehlerfall löschen
                    pass  # Datei wird vom Worker gelöscht
            except Exception as e:
                logger.warning(f"Fehler beim Prüfen temporärer Datei: {e}")
