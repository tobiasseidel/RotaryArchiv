"""
CRUD-Hilfsfunktionen für BBox Tabelle.
Ersetzt die JSON-basierte bbox_data Speicherung.
"""

from datetime import datetime
import json
from typing import Any

from sqlalchemy.orm import Session

from src.rotary_archiv.core.models import BBox, OCRResult

# =============================================================================
# KONFIGURATION: Lesestellen nutzen neue Tabelle (False = alte bbox_data)
# =============================================================================
USE_BBOX_TABLE_FOR_READS = True  # Auf False setzen für Rollback auf bbox_data


def save_bboxes(
    ocr_result_id: int,
    bbox_list: list[dict],
    db: Session,
    update_bbox_data: bool = True,
    image_width: int | None = None,
) -> list[BBox]:
    """
    Schreibt BBox-Liste in Tabelle mit berechneten Metriken.
    
    Args:
        ocr_result_id: ID der OCRResult
        bbox_list: Liste von BBox-Dicts
        db: Datenbank-Session
        update_bbox_data: Wenn True, auch bbox_data Column aktualisieren (für Kompatibilität)
        image_width: Seitenbreite für Prozentberechnung
    
    Returns:
        Liste der erstellten BBox Objekte
    """
    # Alte Einträge löschen
    db.query(BBox).filter(BBox.ocr_result_id == ocr_result_id).delete()

    bboxes = []
    for item in bbox_list:
        if not isinstance(item, dict):
            continue

        bbox = BBox(
            ocr_result_id=ocr_result_id,
            box_type=item.get("box_type", "ocr"),
            bbox=item.get("bbox"),
            bbox_pixel=item.get("bbox_pixel"),
            text=item.get("text"),
            review_status=item.get("review_status"),
            reviewed_at=_parse_datetime(item.get("reviewed_at")),
            reviewed_by=item.get("reviewed_by"),
            ocr_results_data=item.get("ocr_results"),
            differences=item.get("differences"),
            deskew_angle=item.get("deskew_angle"),
            note_author=item.get("note_author"),
            note_text=item.get("note_text"),
            note_created_at=item.get("note_created_at"),
        )
        
        # Metriken berechnen und setzen
        update_bbox_with_metrics(bbox, item, image_width)
        # black_pixels und black_pixels_per_char aus item übernehmen (falls vorhanden)
        bbox.black_pixels = item.get("black_pixels")
        bbox.black_pixels_per_char = item.get("black_pixels_per_char")
        
        db.add(bbox)
        bboxes.append(bbox)

    # Parallel in bbox_data schreiben (für Kompatibilität während Übergang)
    if update_bbox_data:
        ocr_result = db.query(OCRResult).filter(OCRResult.id == ocr_result_id).first()
        if ocr_result:
            ocr_result.bbox_data = bbox_list

    db.flush()
    return bboxes


def get_bboxes(ocr_result_id: int, db: Session) -> list[dict]:
    """
    Liest alle BBox-Einträge für eine OCRResult.

    Returns:
        Liste von BBox-Dicts (kompatibel zu altem bbox_data Format)
    """
    bboxes = (
        db.query(BBox)
        .filter(BBox.ocr_result_id == ocr_result_id)
        .order_by(BBox.id)
        .all()
    )
    return [b.to_dict() for b in bboxes]


def get_bboxes_by_type(
    ocr_result_id: int,
    box_type: str,
    db: Session,
) -> list[dict]:
    """
    Args:
        bbox_item: BBox Dict

    Returns:
        True wenn OCR durchgeführt werden soll
    """
    box_type = bbox_item.get("box_type")
    # Kein box_type oder "ocr" = verarbeiten
    return box_type is None or box_type == "ocr"


def calculate_bbox_metrics(bbox_item: dict, image_width: int | None) -> dict:
    """
    Berechnet Qualitätsmetriken für eine BBox.
    
    Args:
        bbox_item: BBox-Dict mit bbox_pixel und text
        image_width: Seitenbreite in Pixeln (für Prozentberechnung)
    
    Returns:
        Dict mit char_count, chars_per_1k_px, area_px, left_pct, right_pct, width_pct
    """
    result = {}
    
    # Text-Länge
    text = bbox_item.get("reviewed_text") or bbox_item.get("text") or ""
    if not isinstance(text, str):
        text = str(text) if text else ""
    result["char_count"] = len(text)
    
    # Pixel-Koordinaten
    bbox_pixel = bbox_item.get("bbox_pixel")
    if bbox_pixel and isinstance(bbox_pixel, (list, tuple)) and len(bbox_pixel) >= 4:
        x1, y1, x2, y2 = [int(v) if v is not None else 0 for v in bbox_pixel]
        width = max(0, x2 - x1)
        height = max(0, y2 - y1)
        result["area_px"] = width * height
        
        # Prozentuale Positionen
        if image_width and image_width > 0:
            result["left_pct"] = round((x1 / image_width) * 100, 2)
            result["right_pct"] = round((x2 / image_width) * 100, 2)
            result["width_pct"] = round((width / image_width) * 100, 2)
    
    # chars_per_1k_px
    area_px = result.get("area_px", 0)
    if area_px and area_px > 0 and result.get("char_count", 0) > 0:
        result["chars_per_1k_px"] = round(1000 * result["char_count"] / area_px, 2)
    else:
        result["chars_per_1k_px"] = None
    
    return result


def update_bbox_with_metrics(bbox: "BBox", bbox_item: dict, image_width: int | None) -> None:
    """
    Aktualisiert ein BBox-Objekt mit berechneten Metriken.
    
    Args:
        bbox: BBox SQLAlchemy Objekt
        bbox_item: BBox-Dict mit bbox_pixel und text
        image_width: Seitenbreite in Pixeln
    """
    metrics = calculate_bbox_metrics(bbox_item, image_width)
    bbox.char_count = metrics.get("char_count")
    bbox.chars_per_1k_px = metrics.get("chars_per_1k_px")
    bbox.area_px = metrics.get("area_px")
    bbox.left_pct = metrics.get("left_pct")
    bbox.right_pct = metrics.get("right_pct")
    bbox.width_pct = metrics.get("width_pct")
