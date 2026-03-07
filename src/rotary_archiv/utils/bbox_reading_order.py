"""
Lesereihenfolge von Bounding Boxen: oben→unten, links→rechts.

Wird für die Inhaltsanalyse verwendet, damit der Text in logischer Reihenfolge
an das LLM übergeben wird. Die gespeicherte bbox_data-Reihenfolge wird nicht geändert.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Geschätzte Zeilenhöhe in Pixel (Toleranz für "gleiche Zeile")
# Boxen mit y1 innerhalb dieser Toleranz werden als eine Zeile sortiert (dann nach x1).
DEFAULT_LINE_TOLERANCE = 15


def sort_bboxes_reading_order(
    bbox_list: list[dict[str, Any]],
    *,
    line_tolerance: int | None = None,
) -> list[dict[str, Any]]:
    """
    Sortiert BBoxen in Lesereihenfolge: oben→unten, links→rechts.

    Zeilen mit ähnlicher Y-Position (innerhalb line_tolerance) werden als eine Zeile
    behandelt und nach x1 sortiert.

    Args:
        bbox_list: Liste von BBox-Dicts mit mindestens "bbox_pixel" [x1, y1, x2, y2].
        line_tolerance: Pixel-Toleranz für "gleiche Zeile" (y1). Default: DEFAULT_LINE_TOLERANCE.

    Returns:
        Neue Liste derselben BBox-Dicts in Lesereihenfolge. BBoxen ohne gültiges
        bbox_pixel werden ans Ende gestellt.
    """
    if not bbox_list:
        return []

    tol = line_tolerance if line_tolerance is not None else DEFAULT_LINE_TOLERANCE

    def sort_key(item: dict[str, Any]) -> tuple[int, int, int]:
        bp = item.get("bbox_pixel")
        if not bp or len(bp) != 4:
            return (999999, 999999, 999999)  # ans Ende
        x1, y1, _, _ = bp[0], bp[1], bp[2], bp[3]
        # Zeilengruppe: y1 auf Toleranz-Breite runden
        line_group = (y1 // tol) * tol if tol > 0 else y1
        return (line_group, x1, y1)

    return sorted(bbox_list, key=sort_key)


def get_reading_order_indices(
    bbox_list: list[dict[str, Any]],
    *,
    line_tolerance: int | None = None,
) -> list[int]:
    """
    Liefert die Indizes von bbox_list in Lesereihenfolge (oben→unten, links→rechts).

    Nützlich, um für einen gegebenen Index idx die „Nachbarn“ in Lesereihenfolge
    zu ermitteln (z. B. für Kontext bei der KI-Sichtung).
    """
    if not bbox_list:
        return []
    tol = line_tolerance if line_tolerance is not None else DEFAULT_LINE_TOLERANCE

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        _i, b = item
        bp = b.get("bbox_pixel")
        if not bp or len(bp) != 4:
            return (999999, 999999, 999999)
        x1, y1, _, _ = bp[0], bp[1], bp[2], bp[3]
        line_group = (y1 // tol) * tol if tol > 0 else y1
        return (line_group, x1, y1)

    sorted_pairs = sorted(enumerate(bbox_list), key=sort_key)
    return [i for i, _ in sorted_pairs]


# Platzhalter-Texte für persistente Multibox-Regionen (reine Hüll-Boxen)
# und Ignore-Bereiche. Diese sollen nicht in Lesetext / Export erscheinen.
REGION_PLACEHOLDER_PREFIX = "[Region - "
IGNORE_BEREICH_PREFIX = "[Ignore-Bereich]"


def _should_skip_bbox_text(b: dict[str, Any], text: str) -> bool:
    """True wenn diese BBox nicht in Lesetext/Export erscheinen soll."""
    if not text:
        return True
    if b.get("box_type") in ("ignore_region", "note"):
        return True
    if text.startswith(REGION_PLACEHOLDER_PREFIX) or text.startswith(
        IGNORE_BEREICH_PREFIX
    ):
        return True
    return False


def get_text_in_reading_order(
    bbox_list: list[dict[str, Any]],
    *,
    line_tolerance: int | None = None,
    separator: str = "\n",
) -> str:
    """
    Liefert den konkatenierten Text aller BBoxen in Lesereihenfolge.

    Pro BBox wird (reviewed_text or text) verwendet.
    Region-Platzhalter (z. B. "[Region - OCR abgeschlossen]"), Ignore-Bereiche
    (box_type ignore_region / "[Ignore-Bereich]") und Notiz-Boxen werden ausgelassen.

    Args:
        bbox_list: Liste von BBox-Dicts (mit text, reviewed_text, bbox_pixel, optional box_type).
        line_tolerance: Wie in sort_bboxes_reading_order.
        separator: Zwischen den BBox-Texten (z. B. " " oder "\\n").

    Returns:
        Ein zusammengefügter String in Lesereihenfolge.
    """
    sorted_boxes = sort_bboxes_reading_order(bbox_list, line_tolerance=line_tolerance)
    parts = []
    for b in sorted_boxes:
        text = (b.get("reviewed_text") or b.get("text") or "").strip()
        if not _should_skip_bbox_text(b, text):
            parts.append(text)
    return separator.join(parts)
