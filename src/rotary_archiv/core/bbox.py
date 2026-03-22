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
) -> list[BBox]:
    """
    Schreibt BBox-Liste in Tabelle.

    Args:
        ocr_result_id: ID der OCRResult
        bbox_list: Liste von BBox-Dicts
        db: Datenbank-Session
        update_bbox_data: Wenn True, auch bbox_data Column aktualisieren (für Kompatibilität)

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
    Liest BBox-Einträge gefiltert nach Typ.
    Nutzt den Index auf box_type - sehr schnell!

    Returns:
        Liste von BBox-Dicts
    """
    bboxes = (
        db.query(BBox)
        .filter(BBox.ocr_result_id == ocr_result_id)
        .filter(BBox.box_type == box_type)
        .order_by(BBox.id)
        .all()
    )
    return [b.to_dict() for b in bboxes]


def get_bboxes_except_types(
    ocr_result_id: int,
    exclude_types: list[str],
    db: Session,
) -> list[dict]:
    """
    Liest alle BBox-Einträge außer bestimmten Typen.

    Returns:
        Liste von BBox-Dicts
    """
    bboxes = (
        db.query(BBox)
        .filter(BBox.ocr_result_id == ocr_result_id)
        .filter(BBox.box_type.notin_(exclude_types))
        .order_by(BBox.id)
        .all()
    )
    return [b.to_dict() for b in bboxes]


def delete_bboxes(ocr_result_id: int, db: Session) -> int:
    """
    Löscht alle BBox-Einträge für eine OCRResult.

    Returns:
        Anzahl gelöschter Einträge
    """
    count = db.query(BBox).filter(BBox.ocr_result_id == ocr_result_id).delete()
    return count


def update_bbox(
    bbox_id: int,
    updates: dict[str, Any],
    db: Session,
) -> BBox | None:
    """
    Aktualisiert eine einzelne BBox.

    Args:
        bbox_id: ID der BBox
        updates: Dict mit zu aktualisierenden Feldern
        db: Datenbank-Session

    Returns:
        Das aktualisierte BBox Objekt oder None
    """
    bbox = db.query(BBox).filter(BBox.id == bbox_id).first()
    if not bbox:
        return None

    allowed_fields = {
        "box_type",
        "bbox",
        "bbox_pixel",
        "text",
        "review_status",
        "reviewed_at",
        "reviewed_by",
        "ocr_results_data",
        "differences",
        "deskew_angle",
        "note_author",
        "note_text",
        "note_created_at",
    }

    for key, value in updates.items():
        if key in allowed_fields and hasattr(bbox, key):
            if key == "reviewed_at" and isinstance(value, str):
                value = _parse_datetime(value)
            setattr(bbox, key, value)

    db.flush()
    return bbox


def get_bbox(bbox_id: int, db: Session) -> BBox | None:
    """Holt eine einzelne BBox nach ID."""
    return db.query(BBox).filter(BBox.id == bbox_id).first()


def get_notes_page(
    document_id: int | None = None,
    search: str | None = None,
    db: Session = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Holt Notizen mit Paginierung und Suche.
    Optimiert für den Notes-Tab im Erschließungs-Overview.

    Returns:
        Liste von Dicts mit note_text, page_id, document_id
    """
    from src.rotary_archiv.core.models import DocumentPage

    query = (
        db.query(BBox, DocumentPage.document_id)
        .join(DocumentPage, BBox.ocr_result_id == DocumentPage.id)
        .filter(BBox.box_type == "note")
    )

    if document_id is not None:
        query = query.filter(DocumentPage.document_id == document_id)

    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(BBox.note_text.ilike(search_term))

    query = query.order_by(BBox.id.desc()).limit(limit).offset(offset)

    results = []
    for bbox, doc_id in query.all():
        results.append(
            {
                "note_text": bbox.note_text or "",
                "page_id": bbox.ocr_result_id,  # document_page_id
                "document_id": doc_id,
            }
        )

    return results


def _parse_datetime(value: Any) -> datetime | None:
    """Hilfsfunktion zum Parsen von Datetime-Werten."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # ISO Format
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    return None


# =============================================================================
# Lesestellen-Hilfsfunktionen (ersetzen ocr_result.bbox_data Zugriffe)
# =============================================================================


def get_bbox_list_from_ocr_result(ocr_result: OCRResult, db: Session) -> list[dict]:
    """
    Holt BBox-Liste für eine OCRResult.

    Verwendet neue bboxes Tabelle wenn USE_BBOX_TABLE_FOR_READS = True,
    sonst alte bbox_data Spalte.

    Args:
        ocr_result: OCRResult Objekt
        db: Datenbank-Session (nur benötigt für neue Tabelle)

    Returns:
        Liste von BBox-Dicts
    """
    if USE_BBOX_TABLE_FOR_READS and db:
        # NEU: Aus bboxes Tabelle lesen (mit Index - schneller)
        return get_bboxes(ocr_result.id, db)
    else:
        # ALT: Aus bbox_data JSON lesen (Rollback-Option)
        bbox_data = ocr_result.bbox_data
        if not bbox_data:
            return []
        if isinstance(bbox_data, str):
            return json.loads(bbox_data)
        return list(bbox_data)


def has_bboxes(ocr_result: OCRResult, db: Session) -> bool:
    """
    Prüft ob eine OCRResult BBox-Daten hat.

    Args:
        ocr_result: OCRResult Objekt
        db: Datenbank-Session

    Returns:
        True wenn BBox-Daten vorhanden
    """
    if USE_BBOX_TABLE_FOR_READS and db:
        # NEU: Aus bboxes Tabelle prüfen
        count = db.query(BBox).filter(BBox.ocr_result_id == ocr_result.id).count()
        return count > 0
    else:
        # ALT: Aus bbox_data prüfen
        return bool(ocr_result.bbox_data)


def get_bbox_list_filtered_by_type(
    ocr_result: OCRResult,
    exclude_types: list[str],
    db: Session,
) -> list[dict]:
    """
    Holt BBox-Liste gefiltert nach Typ (ausschließen).

    Args:
        ocr_result: OCRResult Objekt
        exclude_types: Liste von Box-Typen die ausgeschlossen werden sollen
        db: Datenbank-Session

    Returns:
        Liste von BBox-Dicts (ohne ausgeschlossene Typen)
    """
    if USE_BBOX_TABLE_FOR_READS and db:
        # NEU: Aus bboxes Tabelle filtern (mit Index)
        return get_bboxes_except_types(ocr_result.id, exclude_types, db)
    else:
        # ALT: In Python filtern
        bbox_list = get_bbox_list_from_ocr_result(ocr_result, db)
        return [b for b in bbox_list if b.get("box_type") not in exclude_types]


def should_process_bbox_for_ocr(bbox_item: dict) -> bool:
    """
    Prüft ob eine BBox für OCR verarbeitet werden soll.

    Args:
        bbox_item: BBox Dict

    Returns:
        True wenn OCR durchgeführt werden soll
    """
    box_type = bbox_item.get("box_type")
    # Kein box_type oder "ocr" = verarbeiten
    return box_type is None or box_type == "ocr"
