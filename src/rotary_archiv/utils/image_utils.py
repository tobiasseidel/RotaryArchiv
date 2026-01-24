"""
Image-Utilities für Bildbearbeitung (Cropping, etc.)
"""

import logging
from pathlib import Path

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


logger = logging.getLogger(__name__)


def crop_bbox_from_image(
    image: Image.Image, bbox_pixel: list[int], padding: int = 5
) -> Image.Image:
    """
    Schneidet Bounding Box aus Bild aus

    Args:
        image: PIL Image
        bbox_pixel: [x1, y1, x2, y2] Pixel-Koordinaten
        padding: Padding in Pixeln um die Box

    Returns:
        Ausgeschnittenes PIL Image

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
        ValueError: Wenn bbox_pixel ungültig ist
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")

    if len(bbox_pixel) != 4:
        raise ValueError("bbox_pixel muss genau 4 Werte haben: [x1, y1, x2, y2]")

    x1, y1, x2, y2 = bbox_pixel

    # Stelle sicher, dass min < max
    x_min = min(x1, x2)
    x_max = max(x1, x2)
    y_min = min(y1, y2)
    y_max = max(y1, y2)

    # Hole Bild-Dimensionen
    img_width, img_height = image.size

    # Debug-Logging
    logger.debug(
        f"BBox-Cropping: Original-Koordinaten: {bbox_pixel}, "
        f"Bild-Dimensionen: {img_width}x{img_height}, "
        f"Normalisiert: x_min={x_min}, y_min={y_min}, x_max={x_max}, y_max={y_max}"
    )

    # Füge Padding hinzu und stelle sicher, dass Koordinaten innerhalb des Bildes bleiben
    x_min_padded = max(0, x_min - padding)
    y_min_padded = max(0, y_min - padding)
    x_max_padded = min(img_width, x_max + padding)
    y_max_padded = min(img_height, y_max + padding)

    logger.debug(
        f"BBox-Cropping: Nach Padding: x_min={x_min_padded}, y_min={y_min_padded}, "
        f"x_max={x_max_padded}, y_max={y_max_padded}, "
        f"Crop-Bereich: {x_max_padded - x_min_padded}x{y_max_padded - y_min_padded}"
    )

    # Schneide aus
    cropped = image.crop((x_min_padded, y_min_padded, x_max_padded, y_max_padded))

    logger.debug(
        f"BBox-Cropping: Ausgeschnittenes Bild: {cropped.size[0]}x{cropped.size[1]}"
    )

    return cropped


def crop_bbox_from_image_file(
    image_path: str | Path, bbox_pixel: list[int], padding: int = 5
) -> Image.Image:
    """
    Lädt Bild aus Datei und schneidet Bounding Box aus

    Args:
        image_path: Pfad zur Bilddatei
        bbox_pixel: [x1, y1, x2, y2] Pixel-Koordinaten
        padding: Padding in Pixeln um die Box

    Returns:
        Ausgeschnittenes PIL Image

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
        FileNotFoundError: Wenn Bilddatei nicht gefunden wird
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")

    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        raise FileNotFoundError(f"Bilddatei nicht gefunden: {image_path}")

    image = Image.open(image_path_obj)
    return crop_bbox_from_image(image, bbox_pixel, padding)
