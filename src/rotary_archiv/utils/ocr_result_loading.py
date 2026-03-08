"""
Zentrale Ladelogik für das „beste“ OCRResult mit bbox_data pro Seite.
Bevorzugt OLLAMA_VISION, dann PDF_NATIVE, sonst neuestes nach created_at.
"""

import json

from sqlalchemy import case
from sqlalchemy.orm import Session

from src.rotary_archiv.core.models import OCRResult, OCRSource


def get_best_ocr_result_with_bbox_for_page(
    db: Session, page_id: int
) -> OCRResult | None:
    """
    Hole das bevorzugte OCRResult mit bbox_data für eine Seite.
    Priorität: OLLAMA_VISION > PDF_NATIVE > neuestes (created_at).
    """
    source_priority = case(
        (OCRResult.source == OCRSource.OLLAMA_VISION, 0),
        (OCRResult.source == OCRSource.PDF_NATIVE, 1),
        else_=2,
    )
    return (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.bbox_data.isnot(None),
        )
        .order_by(source_priority.asc(), OCRResult.created_at.desc())
        .limit(1)
        .first()
    )


def get_pdf_native_text_for_page(db: Session, page_id: int) -> str | None:
    """
    Hole den nativen PDF-Seitentext (eine Box pro Seite) für Auto-Review.
    Returns None wenn kein PDF_NATIVE-Result mit bbox_data existiert.
    """
    ocr_result = (
        db.query(OCRResult)
        .filter(
            OCRResult.document_page_id == page_id,
            OCRResult.source == OCRSource.PDF_NATIVE,
            OCRResult.bbox_data.isnot(None),
        )
        .first()
    )
    if not ocr_result or not ocr_result.bbox_data:
        return None
    raw = ocr_result.bbox_data
    if isinstance(raw, list):
        bbox_data = raw
    elif isinstance(raw, str):
        try:
            bbox_data = json.loads(raw)
        except (TypeError, ValueError):
            return None
    else:
        return None
    if not bbox_data or not isinstance(bbox_data, list):
        return None
    text = bbox_data[0].get("text", "") if isinstance(bbox_data[0], dict) else ""
    return text.strip() or None
