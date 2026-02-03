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

# Gleicher X-Skalierungsfaktor wie in bbox_ocr.py und review.py crop-preview
BBOX_CROP_X_SCALE = 0.7


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
            logger.debug("Ungültige bbox_pixel in BBox: %s", bbox_item)
            continue

        x1, y1, x2, y2 = bbox_pixel

        # Clippe Koordinaten auf Bildgrenzen
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))

        # Stelle sicher, dass x1 < x2 und y1 < y2
        if x1 >= x2 or y1 >= y2:
            logger.debug(
                "Ungültige BBox-Dimensionen (übersprungen): (%s, %s, %s, %s)",
                x1,
                y1,
                x2,
                y2,
            )
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
            logger.debug("Ungültige bbox_pixel in BBox %s: %s", idx, bbox_item)
            continue

        x1, y1, x2, y2 = bbox_pixel

        # Berechne Fläche
        area_px = abs((x2 - x1) * (y2 - y1))
        if area_px == 0:
            logger.debug("BBox %s hat Fläche 0, verwende 1: %s", idx, bbox_pixel)
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


def compute_black_pixels_per_char(
    image: "Image.Image",
    bbox_list: list[dict[str, Any]],
    dark_threshold: int = 200,
    crop_padding: int = 5,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Berechnet pro Box: Schwarze (dunkle) Pixel in der Box im Verhältnis zur Zeichenzahl.

    Crop-Logik ist identisch mit der Dialog-Vorschau (review crop-preview / bbox_ocr):
    - X-Koordinaten werden mit BBOX_CROP_X_SCALE (0.7) skaliert
    - crop_bbox_from_image mit gleichem Padding

    Metrik: black_pixels_per_char = Anzahl dunkler Pixel in der Box / Zeichenanzahl im Text.

    Args:
        image: PIL Image (RGB oder Graustufen)
        bbox_list: Liste von Dicts mit 'bbox_pixel' [x1, y1, x2, y2] und 'text'
        dark_threshold: Schwellwert für „dunkel“ (0-255, Standard: 200)
        crop_padding: Padding in Pixeln wie bei crop_bbox_from_image (Standard: 5)

    Returns:
        Tuple von:
        - Liste pro Box: {index, black_pixels, char_count, black_pixels_per_char, text_preview}
        - Summary: {min_black_pixels_per_char, max_black_pixels_per_char, bbox_count_with_chars}
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")
    if not NUMPY_AVAILABLE:
        raise ImportError("NumPy ist nicht installiert")

    try:
        from src.rotary_archiv.utils.image_utils import crop_bbox_from_image
    except ImportError:
        crop_bbox_from_image = None

    result_bboxes: list[dict[str, Any]] = []
    black_per_char_list: list[float] = []

    for idx, bbox_item in enumerate(bbox_list):
        bbox_pixel = bbox_item.get("bbox_pixel")
        if not bbox_pixel or len(bbox_pixel) != 4:
            logger.debug("Ungültige bbox_pixel in BBox %s: %s", idx, bbox_item)
            continue

        x1, y1, x2, y2 = bbox_pixel
        # Gleiche Anpassung wie Dialog-Vorschau und bbox_ocr: X-Koordinaten * 0.7
        x1_adj = int(x1 * BBOX_CROP_X_SCALE)
        x2_adj = int(x2 * BBOX_CROP_X_SCALE)
        bbox_pixel_adjusted = [x1_adj, y1, x2_adj, y2]

        if crop_bbox_from_image is not None:
            # Exakt gleicher Crop wie in der Dialog-Vorschau (crop_bbox_from_image mit Padding)
            try:
                cropped_pil = crop_bbox_from_image(
                    image, bbox_pixel_adjusted, padding=crop_padding
                )
            except (ValueError, Exception):
                logger.debug(
                    "Crop fehlgeschlagen für BBox %s: %s", idx, bbox_pixel_adjusted
                )
                continue
            gray_crop = (
                cropped_pil.convert("L") if cropped_pil.mode != "L" else cropped_pil
            )
            crop_array = np.array(gray_crop, dtype=np.uint8)
        else:
            # Fallback: direkter Slice mit angepassten Koordinaten (ohne Padding)
            w, h = image.size
            x1_clip = max(0, min(x1_adj, w))
            y1_clip = max(0, min(y1, h))
            x2_clip = max(0, min(x2_adj, w))
            y2_clip = max(0, min(y2, h))
            if x1_clip >= x2_clip or y1_clip >= y2_clip:
                logger.debug("Ungültige BBox-Dimensionen (übersprungen) in %s", idx)
                continue
            gray_img = image.convert("L") if image.mode != "L" else image
            gray_array = np.array(gray_img, dtype=np.uint8)
            crop_array = gray_array[y1_clip:y2_clip, x1_clip:x2_clip]

        dark_pixels = crop_array < dark_threshold
        black_pixels = int(np.sum(dark_pixels))

        text = bbox_item.get("reviewed_text") or bbox_item.get("text") or ""
        char_count = len(text)
        text_preview = text[:50] + ("..." if len(text) > 50 else "")

        if char_count > 0:
            black_pixels_per_char = black_pixels / char_count
            black_per_char_list.append(black_pixels_per_char)
        else:
            black_pixels_per_char = None  # keine Zeichen → Verhältnis undefiniert

        result_bboxes.append(
            {
                "index": idx,
                "black_pixels": black_pixels,
                "char_count": char_count,
                "black_pixels_per_char": float(black_pixels_per_char)
                if black_pixels_per_char is not None
                else None,
                "text_preview": text_preview,
            }
        )

    if black_per_char_list:
        summary = {
            "min_black_pixels_per_char": float(min(black_per_char_list)),
            "max_black_pixels_per_char": float(max(black_per_char_list)),
            "bbox_count_with_chars": len(black_per_char_list),
        }
    else:
        summary = {
            "min_black_pixels_per_char": None,
            "max_black_pixels_per_char": None,
            "bbox_count_with_chars": 0,
        }

    return result_bboxes, summary
