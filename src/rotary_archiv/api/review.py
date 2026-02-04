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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


class SaveReviewedBBoxRequest(BaseModel):
    """Request-Schema für gespeicherte Review-BBox"""

    reviewed_text: str


class AddBBoxRequest(BaseModel):
    """Request-Schema für neu hinzugefügte BBox"""

    bbox_pixel: list[int]  # [x1, y1, x2, y2] Pixel-Koordinaten


class BBoxRef(BaseModel):
    """Referenz auf eine BBox"""

    page_id: int
    bbox_index: int


class BatchChangeStatusRequest(BaseModel):
    """Request-Schema für Batch-Status-Änderung"""

    bboxes: list[BBoxRef]
    new_status: str  # pending, confirmed, rejected, auto_confirmed, ignored, new


class BatchDiscardAndRecalcRequest(BaseModel):
    """Request-Schema für Batch-OCR verwerfen und neu berechnen"""

    bboxes: list[BBoxRef]


class BatchDeleteRequest(BaseModel):
    """Request-Schema für Batch-BBoxen löschen"""

    bboxes: list[BBoxRef]


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

    # Gruppiere BBoxen nach page_id für effiziente DB-Zugriffe
    from collections import defaultdict

    bboxes_by_page = defaultdict(list)
    for bbox_ref in request.bboxes:
        bboxes_by_page[bbox_ref.page_id].append(bbox_ref.bbox_index)

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
        request: Liste von BBox-Referenzen

    Returns:
        {"success": True, "discarded": int, "jobs_created": int, "jobs_existing": int, "errors": [...]}
    """
    discarded = 0
    errors = []
    jobs_created = 0
    jobs_existing = 0

    # Gruppiere BBoxen nach page_id
    from collections import defaultdict

    bboxes_by_page = defaultdict(list)
    for bbox_ref in request.bboxes:
        bboxes_by_page[bbox_ref.page_id].append(bbox_ref.bbox_index)

    # Schritt 1: Verwerfen
    for page_id, bbox_indices in bboxes_by_page.items():
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

        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data.copy()

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
            # Erstelle neuen Review-Job
            review_job = OCRJob(
                document_id=page.document_id,
                document_page_id=page_id,
                job_type="bbox_review",
                status=OCRJobStatus.PENDING,
                language="deu+eng",
                use_correction=False,
                progress=0.0,
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

    # Gruppiere BBoxen nach page_id
    from collections import defaultdict

    bboxes_by_page = defaultdict(list)
    for bbox_ref in request.bboxes:
        bboxes_by_page[bbox_ref.page_id].append(bbox_ref.bbox_index)

    for page_id, bbox_indices in bboxes_by_page.items():
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

        if isinstance(ocr_result.bbox_data, str):
            bbox_list = json.loads(ocr_result.bbox_data)
        else:
            bbox_list = ocr_result.bbox_data.copy()

        # Sortiere Indizes in umgekehrter Reihenfolge, damit Löschung von hinten nach vorne erfolgt
        sorted_indices = sorted(set(bbox_indices), reverse=True)
        valid_indices = [idx for idx in sorted_indices if 0 <= idx < len(bbox_list)]

        if len(valid_indices) != len(sorted_indices):
            invalid = set(sorted_indices) - set(valid_indices)
            for idx in invalid:
                errors.append(
                    {
                        "page_id": page_id,
                        "bbox_index": idx,
                        "error": "BBox-Index außerhalb des Bereichs",
                    }
                )

        # Lösche BBoxen (von hinten nach vorne)
        for bbox_index in valid_indices:
            bbox_list.pop(bbox_index)
            deleted += 1

        if valid_indices:
            ocr_result.bbox_data = bbox_list
            flag_modified(ocr_result, "bbox_data")
            db.commit()

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
    from pathlib import Path
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

    # Suche zuerst nach gespeichertem Debug-Crop
    debug_dir = Path(settings.debug_bbox_crops_path)
    if debug_dir.exists():
        # Suche nach Crop-Bildern für diese BBox (neuestes zuerst)
        debug_files = sorted(
            debug_dir.glob(f"page_{page_id}_bbox_{bbox_index}_*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if debug_files:
            # Verwende das neueste Crop-Bild
            return FileResponse(
                path=str(debug_files[0]),
                media_type="image/png",
                filename=f"bbox_{bbox_index}_crop.png",
            )

    # Falls kein Debug-Crop vorhanden, erstelle es on-the-fly
    # Verwende die GLEICHE Logik wie in bbox_ocr.py
    try:
        from src.rotary_archiv.utils.file_handler import get_file_path
        from src.rotary_archiv.utils.image_utils import crop_bbox_from_image
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

        # Croppe BBox aus Bild (OHNE padding, genau wie in bbox_ocr.py Zeile 309)
        cropped_image = crop_bbox_from_image(page_image, bbox_pixel_adjusted)

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

    # Erstelle Review-Job
    review_job = OCRJob(
        document_id=page.document_id,
        document_page_id=page_id,
        job_type="bbox_review",
        status=OCRJobStatus.PENDING,
        language="deu+eng",
        use_correction=False,  # Review-Jobs benötigen keine GPT-Korrektur
        progress=0.0,
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
