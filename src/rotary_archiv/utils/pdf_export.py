"""
PDF-Export: Seite als PDF mit Original-Hintergrund und durchsuchbarem,
transparentem Text-Overlay aus den OCR-Textboxen.
"""

import io
import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.colors import Color
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except ImportError:
    pass

if TYPE_CHECKING:
    from PIL import Image

# DPI für PDF-Seitengröße (muss mit dem DPI der Bild-Erzeugung übereinstimmen können)
EXPORT_DPI = 150
DEFAULT_TEXT_OPACITY = 0.0  # 0 = voll durchsichtig (Text nur selektierbar/durchsuchbar)
MIN_FONT_SIZE_PT = 6
# X-Skalierung wie im Leaflet Frontend: (mapImageWidth/ocrImageWidth)*0.7
SCALE_X_FACTOR = 0.7
# Zeilenhöhe relativ zur Schriftgröße
LINE_HEIGHT_FACTOR = 1.2


def _wrap_text(
    c: "canvas.Canvas",
    text: str,
    width_pt: float,
    font_name: str = "Helvetica",
    font_size_pt: float = 10,
) -> list[str]:
    """
    Bricht Text in Zeilen um, die in width_pt (Punkt) passen.
    Bestehende Zeilenumbrüche (\\n) werden beibehalten.
    """
    if not text or width_pt <= 0:
        return []
    lines_out: list[str] = []
    paragraphs = text.replace("\r", "\n").split("\n")
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        words = para.split()
        current: list[str] = []
        current_width = 0.0
        for word in words:
            w = c.stringWidth(word + " ", font_name, font_size_pt)
            if current_width + w > width_pt and current:
                lines_out.append(" ".join(current))
                current = [word]
                current_width = c.stringWidth(word + " ", font_name, font_size_pt)
            else:
                current.append(word)
                current_width += w
        if current:
            lines_out.append(" ".join(current))
    return lines_out


def build_page_pdf(
    page_image: "Image.Image",
    bbox_items: list[dict[str, Any]],
    ocr_width: int,
    ocr_height: int,
    dpi: int = EXPORT_DPI,
    text_opacity: float = DEFAULT_TEXT_OPACITY,
) -> io.BytesIO:
    """
    Erstellt ein einseitiges PDF: Hintergrundbild + Text-Overlay (durchsuchbar, transparent).

    Args:
        page_image: PIL Image der Seite (Hintergrund).
        bbox_items: Liste von BBox-Dicts mit 'text', 'bbox_pixel' [x1,y1,x2,y2], optional 'box_type'.
        ocr_width: Breite des OCR-Bildes (für Skalierung von bbox_pixel).
        ocr_height: Höhe des OCR-Bildes.
        dpi: DPI für PDF-Seitengröße (Punkt = Pixel * 72 / dpi).
        text_opacity: Deckkraft des Textes 0.0-1.0 (z. B. 0.5 = 50 %).

    Returns:
        BytesIO mit PDF-Inhalt.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "ReportLab ist nicht installiert. Bitte installieren: pip install reportlab"
        )

    export_w, export_h = page_image.size
    width_pt = export_w * 72 / dpi
    height_pt = export_h * 72 / dpi

    # Wie Leaflet: X mit 0.7-Faktor, Y 1:1
    scale_x = (export_w / ocr_width * SCALE_X_FACTOR) if ocr_width else SCALE_X_FACTOR
    scale_y = export_h / ocr_height if ocr_height else 1.0

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width_pt, height_pt))
    c.setPageSize((width_pt, height_pt))

    # Hintergrundbild
    img_buffer = io.BytesIO()
    page_image.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    c.drawImage(ImageReader(img_buffer), 0, 0, width=width_pt, height=height_pt)

    # Text-Overlay: nur Boxen mit Text, keine ignore_region
    for item in bbox_items:
        box_type = (item.get("box_type") or "").strip().lower()
        if box_type == "ignore_region":
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        pixel = item.get("bbox_pixel")
        if not pixel or len(pixel) < 4:
            continue
        x1_ocr, y1_ocr = float(pixel[0]), float(pixel[1])
        x2_ocr, y2_ocr = float(pixel[2]), float(pixel[3])
        x1 = min(x1_ocr, x2_ocr) * scale_x
        x2 = max(x1_ocr, x2_ocr) * scale_x
        y1 = min(y1_ocr, y2_ocr) * scale_y
        y2 = max(y1_ocr, y2_ocr) * scale_y
        box_w_px = max(1, x2 - x1)
        box_h_px = max(1, y2 - y1)
        box_width_pt = box_w_px * 72 / dpi
        box_height_pt = box_h_px * 72 / dpi
        left_pt = x1 * 72 / dpi
        bottom_pt_box = (export_h - y2) * 72 / dpi
        # Schriftgröße skaliert mit Boxhöhe; wird verkleinert bis der ganze Text in die Box passt
        font_size_pt = max(MIN_FONT_SIZE_PT, box_h_px * 72 / dpi * 0.85)
        text_limited = (text.replace("\r", "\n") or "")[:2000]
        while font_size_pt >= MIN_FONT_SIZE_PT:
            lines = _wrap_text(c, text_limited, box_width_pt, "Helvetica", font_size_pt)
            line_height_pt = font_size_pt * LINE_HEIGHT_FACTOR
            max_lines_fit = box_height_pt / line_height_pt
            if len(lines) <= max_lines_fit:
                break
            font_size_pt = max(MIN_FONT_SIZE_PT, font_size_pt * 0.85)
        line_height_pt = font_size_pt * LINE_HEIGHT_FACTOR
        c.setFont("Helvetica", font_size_pt)
        c.setFillColor(Color(0, 0, 0, alpha=text_opacity))
        # Von oben nach unten zeichnen (obere Zeile zuerst; PDF-Y nach unten)
        top_baseline = bottom_pt_box + box_height_pt - font_size_pt
        for i, line in enumerate(lines):
            c.drawString(left_pt, top_baseline - i * line_height_pt, line)

    c.save()
    buf.seek(0)
    return buf
