"""
Qualitätsmetriken für OCR-Ergebnisse

Berechnet Coverage (Abdeckung dunkler Pixel) und Density (Zeichendichte pro Box).
"""

import logging
from typing import Any

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)


def compute_coverage(
    image: "Image.Image",
    bbox_list: list[dict[str, Any]],
    image_width: int | None = None,
    image_height: int | None = None,
    dark_threshold: int = 200,
) -> dict[str, Any]:
    """
    Berechnet die Coverage-Metrik: Anteil dunkler Pixel, die von BBoxen abgedeckt sind.

    Args:
        image: PIL Image (RGB oder Graustufen)
        bbox_list: Liste von Dicts mit 'bbox_pixel' [x1, y1, x2, y2]
        image_width: Erwartete Bildbreite (für Validierung)
        image_height: Erwartete Bildhöhe (für Validierung)
        dark_threshold: Schwellwert für "dunkel" (0-255, Standard: 200)

    Returns:
        Dict mit:
        - uncovered_dark_pixels: Anzahl dunkler Pixel außerhalb von BBoxen
        - total_dark_pixels: Gesamtanzahl dunkler Pixel
        - coverage_ratio: Anteil abgedeckter dunkler Pixel (0.0-1.0)
        - uncovered_ratio: Anteil unbedeckter dunkler Pixel (0.0-1.0)

    Raises:
        ImportError: Wenn PIL oder NumPy nicht verfügbar
        ValueError: Wenn bbox_pixel ungültig ist
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")
    if not NUMPY_AVAILABLE:
        raise ImportError("NumPy ist nicht installiert")

    # Konvertiere zu Graustufen
    gray_img = image.convert("L") if image.mode != "L" else image

    # Konvertiere zu NumPy-Array
    gray_array = np.array(gray_img, dtype=np.uint8)
    h, w = gray_array.shape

    # Validiere Bildgröße falls angegeben
    if image_width and image_height and (w != image_width or h != image_height):
        logger.warning(
            f"Bildgröße ({w}x{h}) weicht von erwarteter Größe ({image_width}x{image_height}) ab. "
            "BBox-Koordinaten könnten nicht passen."
        )

    # Erstelle Maske für abgedeckte Bereiche (anfangs alle False)
    mask_covered = np.zeros((h, w), dtype=bool)

    # Markiere alle BBox-Bereiche als abgedeckt
    for bbox_item in bbox_list:
        bbox_pixel = bbox_item.get("bbox_pixel")
        if not bbox_pixel or len(bbox_pixel) != 4:
            logger.warning(f"Ungültige bbox_pixel in BBox: {bbox_item}")
            continue

        x1, y1, x2, y2 = bbox_pixel

        # Clippe Koordinaten auf Bildgrenzen
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))

        # Stelle sicher, dass x1 < x2 und y1 < y2
        if x1 >= x2 or y1 >= y2:
            logger.warning(f"Ungültige BBox-Dimensionen: ({x1}, {y1}, {x2}, {y2})")
            continue

        # Markiere Bereich als abgedeckt
        mask_covered[y1:y2, x1:x2] = True

    # Identifiziere dunkle Pixel
    dark_pixels = gray_array < dark_threshold

    # Zähle dunkle Pixel
    total_dark_pixels = int(np.sum(dark_pixels))

    # Zähle unbedeckte dunkle Pixel
    uncovered_dark_pixels = int(np.sum(dark_pixels & ~mask_covered))

    # Berechne Coverage-Ratio
    if total_dark_pixels == 0:
        coverage_ratio = 1.0
        uncovered_ratio = 0.0
    else:
        coverage_ratio = 1.0 - (uncovered_dark_pixels / total_dark_pixels)
        uncovered_ratio = uncovered_dark_pixels / total_dark_pixels

    return {
        "uncovered_dark_pixels": uncovered_dark_pixels,
        "total_dark_pixels": total_dark_pixels,
        "coverage_ratio": float(coverage_ratio),
        "uncovered_ratio": float(uncovered_ratio),
    }


def compute_density(
    bbox_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Berechnet die Density-Metrik: Zeichendichte pro Box.

    Args:
        bbox_list: Liste von Dicts mit 'bbox_pixel' [x1, y1, x2, y2] und 'text'

    Returns:
        Tuple von:
        - Liste von Dicts pro Box: {index, char_count, area_px, chars_per_area, chars_per_1k_px, text_preview}
        - Summary-Dict: {median_chars_per_1k_px, min_chars_per_1k_px, max_chars_per_1k_px, bbox_count}
    """
    bbox_densities: list[dict[str, Any]] = []
    chars_per_1k_px_list: list[float] = []

    for idx, bbox_item in enumerate(bbox_list):
        bbox_pixel = bbox_item.get("bbox_pixel")
        if not bbox_pixel or len(bbox_pixel) != 4:
            logger.warning(f"Ungültige bbox_pixel in BBox {idx}: {bbox_item}")
            continue

        x1, y1, x2, y2 = bbox_pixel

        # Berechne Fläche
        area_px = abs((x2 - x1) * (y2 - y1))
        if area_px == 0:
            logger.warning(f"BBox {idx} hat Fläche 0: {bbox_pixel}")
            area_px = 1  # Vermeide Division durch 0

        # Hole Text (reviewed_text hat Vorrang, sonst text)
        text = bbox_item.get("reviewed_text") or bbox_item.get("text") or ""
        char_count = len(text)

        # Berechne Dichten
        chars_per_area = char_count / area_px
        chars_per_1k_px = 1000 * char_count / area_px

        # Text-Vorschau (max 50 Zeichen)
        text_preview = text[:50] + ("..." if len(text) > 50 else "")

        bbox_densities.append(
            {
                "index": idx,
                "char_count": char_count,
                "area_px": area_px,
                "chars_per_area": float(chars_per_area),
                "chars_per_1k_px": float(chars_per_1k_px),
                "text_preview": text_preview,
            }
        )

        chars_per_1k_px_list.append(chars_per_1k_px)

    # Berechne Summary
    if chars_per_1k_px_list:
        summary = {
            "median_chars_per_1k_px": float(np.median(chars_per_1k_px_list)),
            "min_chars_per_1k_px": float(min(chars_per_1k_px_list)),
            "max_chars_per_1k_px": float(max(chars_per_1k_px_list)),
            "bbox_count": len(bbox_densities),
        }
    else:
        summary = {
            "median_chars_per_1k_px": 0.0,
            "min_chars_per_1k_px": 0.0,
            "max_chars_per_1k_px": 0.0,
            "bbox_count": 0,
        }

    return bbox_densities, summary
