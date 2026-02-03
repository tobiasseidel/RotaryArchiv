"""
Image-Utilities für Bildbearbeitung (Cropping, Skew/Deskew, etc.)
"""

import logging
import math
from pathlib import Path

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

logger = logging.getLogger(__name__)


def detect_skew_angle(image: "Image.Image") -> float:
    """
    Erkennt den Schrägwinkel (Skew) eines Dokumentbildes per Hough-Transformation.

    Drehpunkt für spätere Koordinatentransformation: obere linke Ecke (0,0).

    Args:
        image: PIL Image (Graustufen oder RGB)

    Returns:
        Winkel in Grad (typ. -10 bis +10). 0.0 bei zu wenig Linien oder wenn
        OpenCV nicht verfügbar.

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
    """
    debug_info = detect_skew_angle_debug(image)
    return debug_info["angle"]


def detect_skew_angle_debug(image: "Image.Image") -> dict:
    """
    Erkennt den Schrägwinkel (Skew) mit detaillierten Debug-Informationen.

    Args:
        image: PIL Image (Graustufen oder RGB)

    Returns:
        Dictionary mit:
        - angle: Winkel in Grad (float)
        - total_lines: Anzahl aller erkannten Linien (int)
        - valid_angles: Liste aller gültigen Winkel (list[float])
        - angle_stats: Statistiken (min, max, median, mean, std) (dict)
        - lines_info: Liste mit Details zu jeder Linie (list[dict])
        - canny_params: Parameter für Canny-Edge-Detection (dict)
        - hough_params: Parameter für Hough-Transformation (dict)

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")
    if not CV2_AVAILABLE:
        logger.warning("OpenCV nicht verfügbar, detect_skew_angle liefert 0.0")
        return {
            "angle": 0.0,
            "total_lines": 0,
            "valid_angles": [],
            "angle_stats": {},
            "lines_info": [],
            "canny_params": {"low": 50, "high": 150},
            "hough_params": {
                "threshold": 80,
                "minLineLength": 50,
                "maxLineGap": 10,
            },
            "error": "OpenCV nicht verfügbar",
        }

    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    # Canny-Edge-Detection
    canny_low = 50
    canny_high = 150
    edges = cv2.Canny(gray, canny_low, canny_high)

    # Hough-Transformation
    hough_threshold = 80
    hough_min_line_length = 50
    hough_max_line_gap = 10
    lines = cv2.HoughLinesP(
        edges,
        1,
        math.pi / 180,
        threshold=hough_threshold,
        minLineLength=hough_min_line_length,
        maxLineGap=hough_max_line_gap,
    )

    total_lines = len(lines) if lines is not None else 0
    lines_info = []
    angles: list[float] = []

    if lines is None or len(lines) == 0:
        return {
            "angle": 0.0,
            "total_lines": 0,
            "valid_angles": [],
            "angle_stats": {},
            "lines_info": [],
            "canny_params": {"low": canny_low, "high": canny_high},
            "hough_params": {
                "threshold": hough_threshold,
                "minLineLength": hough_min_line_length,
                "maxLineGap": hough_max_line_gap,
            },
        }

    for idx, line in enumerate(lines):
        x1, y1, x2, y2 = line[0]
        # Berechne Winkel vor Normalisierung
        raw_angle = math.degrees(math.atan2(y2 - y1, x2 - x1 + 1e-6))
        line_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Normiere auf ca. [-45, 45]; für Skew zählen vor allem nahe 0° und 90°
        normalized_angle = raw_angle
        if raw_angle > 45:
            normalized_angle = raw_angle - 90
        elif raw_angle < -45:
            normalized_angle = raw_angle + 90

        is_valid = -15 <= normalized_angle <= 15  # typischer Skew-Bereich

        line_info = {
            "index": idx,
            "x1": int(x1),
            "y1": int(y1),
            "x2": int(x2),
            "y2": int(y2),
            "length": float(line_length),
            "raw_angle": float(raw_angle),
            "normalized_angle": float(normalized_angle),
            "is_valid": is_valid,
        }
        lines_info.append(line_info)

        if is_valid:
            angles.append(normalized_angle)

    # Berechne Statistiken
    angle_stats = {}
    if angles:
        angle_stats = {
            "min": float(np.min(angles)),
            "max": float(np.max(angles)),
            "median": float(np.median(angles)),
            "mean": float(np.mean(angles)),
            "std": float(np.std(angles)),
            "count": len(angles),
        }
        final_angle = float(np.median(angles))
    else:
        final_angle = 0.0

    return {
        "angle": final_angle,
        "total_lines": total_lines,
        "valid_angles": [float(a) for a in angles],
        "angle_stats": angle_stats,
        "lines_info": lines_info,
        "canny_params": {"low": canny_low, "high": canny_high},
        "hough_params": {
            "threshold": hough_threshold,
            "minLineLength": hough_min_line_length,
            "maxLineGap": hough_max_line_gap,
        },
    }


def deskew_image(
    image: "Image.Image",
    angle: float,
    *,
    expand: bool = True,
    fill_color: int | tuple[int, ...] = 255,
) -> "Image.Image":
    """
    Dreht ein Bild um den angegebenen Winkel (Deskew).

    Drehpunkt ist immer die obere linke Ecke (0,0). bbox_pixel-Koordinaten
    beziehen sich auf das Ausgabebild.

    Args:
        image: PIL Image
        angle: Winkel in Grad (positiv = gegen Uhrzeigersinn)
        expand: Bei True wird das Canvas vergrößert, damit das gedrehte Bild
            vollständig sichtbar ist.
        fill_color: Farbe für neue Ränder (Standard: 255 = weiß). Bei RGB:
            (255, 255, 255).

    Returns:
        Gedrehtes PIL Image

    Raises:
        ImportError: Wenn PIL oder OpenCV nicht verfügbar
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow ist nicht installiert")
    if not CV2_AVAILABLE:
        raise ImportError("OpenCV (opencv-python-headless) für deskew_image nötig")

    if abs(angle) < 0.01:
        return image.copy()

    img = np.array(image)
    h, w = img.shape[:2]
    # Rotation um (0,0) = obere linke Ecke
    # angle ist der erkannte Schrägwinkel
    # cv2.getRotationMatrix2D: positiver Winkel = gegen Uhrzeigersinn
    # Wenn angle positiv ist (z.B. +2° = nach rechts geneigt),
    # müssen wir -angle drehen (im Uhrzeigersinn) um zu begradigen
    # Da die aktuelle Implementierung das Problem verstärkt, verwenden wir angle statt -angle
    # (Das bedeutet: der erkannte Winkel gibt bereits die Korrekturrichtung an)
    correction_angle = angle  # Verwende angle direkt (statt -angle)
    m = cv2.getRotationMatrix2D((0.0, 0.0), correction_angle, 1.0)
    # m ist 2x3: [a,b,tx; c,d,ty]. Reine Rotation: tx=ty=0.

    if expand:
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        # Anwenden der 2x3-Matrix: (x,y) -> m[:,:2]@[x;y] + m[:,2]
        rotated = (corners @ m[:, :2].T) + m[:, 2]
        min_x, min_y = rotated.min(axis=0)
        max_x, max_y = rotated.max(axis=0)
        out_w = int(math.ceil(max_x - min_x))
        out_h = int(math.ceil(max_y - min_y))
        m[0, 2] -= min_x
        m[1, 2] -= min_y
    else:
        out_w, out_h = w, h

    if len(img.shape) == 2:
        fill = fill_color if isinstance(fill_color, int) else 255
    else:
        fill = fill_color if isinstance(fill_color, (tuple, list)) else (255,) * 3
    out = cv2.warpAffine(
        img, m, (out_w, out_h), flags=cv2.INTER_LANCZOS4, borderValue=fill
    )
    return Image.fromarray(out)


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
