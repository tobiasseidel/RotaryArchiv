"""
API Endpoints für Dokument-Seiten
"""

import logging
from pathlib import Path
import tempfile
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.rotary_archiv.api.schemas import OCRResultResponse, PageInspectResponse
from src.rotary_archiv.config import settings
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    OCRResult,
)
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.utils.image_utils import deskew_image, detect_skew_angle
from src.rotary_archiv.utils.pdf_splitter import PDF2IMAGE_AVAILABLE, PDFSplitter
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

router = APIRouter(prefix="/api/pages", tags=["pages"])


class MergePagesRequest(BaseModel):
    """Request für Seiten-Zusammenführung"""

    page_ids: list[int]
    title: str | None = None


@router.post("/document/{document_id}/extract")
def extract_pages(
    document_id: int,
    output_format: str = "image",  # Standard: "image" für Vorschau
    db: Session = Depends(get_db),
):
    """
    Extrahiere Seiten aus einem PDF-Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    if (
        document.file_type.lower() != "application/pdf"
        and not document.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien können in Seiten extrahiert werden",
        )

    try:
        # Prüfe ob Datei existiert
        file_path = get_file_path(document.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Datei nicht gefunden: {file_path}",
            )

        # Extrahiere Seiten
        splitter = PDFSplitter()
        pages_info = splitter.extract_pages(str(file_path), output_format)

        # Speichere Seiten in Datenbank
        created_pages = []
        for page_info in pages_info:
            db_page = DocumentPage(
                document_id=document_id,
                page_number=page_info["page_number"],
                file_path=page_info["file_path"],
                file_type=page_info["file_type"],
            )
            db.add(db_page)
            created_pages.append(db_page)

        db.commit()

        # Refresh für IDs
        for page in created_pages:
            db.refresh(page)

        return {
            "document_id": document_id,
            "pages": [
                {
                    "id": page.id,
                    "page_number": page.page_number,
                    "file_path": page.file_path,
                    "file_type": page.file_type,
                }
                for page in created_pages
            ],
            "total_pages": len(created_pages),
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logging.error(f"Datei nicht gefunden: {e!s}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Datei nicht gefunden: {e!s}"
        ) from e
    except MemoryError as e:
        logging.error("Nicht genug Speicher für große PDF-Datei")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF-Datei ist zu groß. Bitte verwende eine kleinere Datei oder reduziere die DPI-Einstellung.",
        ) from e
    except TimeoutError as e:
        logging.error("Timeout bei PDF-Verarbeitung")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="PDF-Verarbeitung dauerte zu lange. Bitte versuche es mit einer kleineren Datei.",
        ) from e
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Seiten-Extraktion Fehler: {error_msg}")
        logging.error(traceback.format_exc())
        db.rollback()

        # Spezifische Fehlermeldungen
        if "poppler" in error_msg.lower() or "pdftoppm" in error_msg.lower():
            detail = f"Poppler-Fehler: {error_msg}\nBitte prüfe die Poppler-Installation und POPPLER_PATH in .env"
        elif "memory" in error_msg.lower() or "speicher" in error_msg.lower():
            detail = (
                f"Speicherfehler: Die PDF-Datei ist möglicherweise zu groß. {error_msg}"
            )
        else:
            detail = f"Fehler beim Extrahieren der Seiten: {error_msg}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        ) from e


@router.get("/deskew-overview")
def get_deskew_overview(
    document_id: int | None = Query(
        None, description="Optional: nur Seiten dieses Dokuments"
    ),
    db: Session = Depends(get_db),
):
    """
    Übersicht aller Seiten mit Deskew-Winkel (und optional Anteil BBoxen mit Winkelkorrektur).

    Returns:
        Liste: page_id, document_id, document_title, page_number, deskew_angle,
               bbox_count, bbox_with_deskew_count, bbox_with_deskew_pct
    """
    import json

    query = (
        db.query(DocumentPage)
        .join(Document, Document.id == DocumentPage.document_id)
        .order_by(DocumentPage.document_id, DocumentPage.page_number)
    )
    if document_id is not None:
        query = query.filter(DocumentPage.document_id == document_id)
    pages = query.all()

    result = []
    for page in pages:
        doc = page.document
        document_title = (
            (doc.title or doc.filename or f"Dokument #{page.document_id}")
            if doc
            else f"Dokument #{page.document_id}"
        )

        # Neuestes OCRResult mit bbox_data für BBox-Statistik
        ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_page_id == page.id,
                OCRResult.bbox_data.isnot(None),
            )
            .order_by(OCRResult.created_at.desc())
            .first()
        )
        bbox_count = 0
        bbox_with_deskew_count = 0
        if ocr_result and ocr_result.bbox_data:
            bbox_list = (
                ocr_result.bbox_data
                if isinstance(ocr_result.bbox_data, list)
                else json.loads(ocr_result.bbox_data)
                if isinstance(ocr_result.bbox_data, str)
                else []
            )

            # Nur BBoxen mit gültigen Koordinaten zählen (wie in Page Inspect dargestellt)
            def _has_valid_coords(b):
                bp = (
                    b.get("bbox_pixel")
                    if isinstance(b.get("bbox_pixel"), (list, tuple))
                    else None
                )
                br = b.get("bbox") if isinstance(b.get("bbox"), (list, tuple)) else None
                return (bp and len(bp) >= 4) or (br and len(br) >= 4)

            bbox_count_total = len(bbox_list)
            bbox_list_valid = [b for b in bbox_list if _has_valid_coords(b)]
            bbox_count = len(bbox_list_valid)
            bbox_with_deskew_count = sum(
                1 for b in bbox_list_valid if b.get("deskew_angle") is not None
            )
        else:
            bbox_count_total = 0
            bbox_count = 0
            bbox_with_deskew_count = 0
        bbox_with_deskew_pct = (
            round(bbox_with_deskew_count / bbox_count * 100.0, 1)
            if bbox_count
            else None
        )

        result.append(
            {
                "page_id": page.id,
                "document_id": page.document_id,
                "document_title": document_title,
                "page_number": page.page_number,
                "deskew_angle": round(page.deskew_angle, 2)
                if page.deskew_angle is not None
                else None,
                "bbox_count": bbox_count,
                "bbox_count_total": bbox_count_total,
                "bbox_with_deskew_count": bbox_with_deskew_count,
                "bbox_with_deskew_pct": bbox_with_deskew_pct,
            }
        )

    return {"pages": result}


@router.post("/measure-deskew-batch")
def measure_deskew_batch(
    document_id: int | None = Query(
        None, description="Optional: nur Seiten dieses Dokuments"
    ),
    db: Session = Depends(get_db),
):
    """
    Misst den Seitenwinkel (Skew) für alle Seiten, die noch keinen deskew_angle haben,
    und speichert den Winkel in DocumentPage.deskew_angle.
    """
    query = (
        db.query(DocumentPage)
        .filter(DocumentPage.deskew_angle.is_(None))
        .order_by(DocumentPage.document_id, DocumentPage.page_number)
    )
    if document_id is not None:
        query = query.filter(DocumentPage.document_id == document_id)
    pages = query.all()

    measured = []
    errors = []

    for page in pages:
        try:
            img = _load_page_as_pil(page, db, dpi=200)
            angle = detect_skew_angle(img)
            page.deskew_angle = round(angle, 4)
            measured.append({"page_id": page.id, "angle": page.deskew_angle})
        except Exception as e:
            errors.append({"page_id": page.id, "error": str(e)})
            logging.warning("Deskew messen Seite %s: %s", page.id, e)

    if measured:
        db.commit()

    return {
        "measured": len(measured),
        "page_ids": [m["page_id"] for m in measured],
        "errors": errors,
    }


@router.get("/document/{document_id}")
def get_document_pages(document_id: int, db: Session = Depends(get_db)):
    """
    Hole alle Seiten eines Dokuments
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )

    return {
        "document_id": document_id,
        "pages": [
            {
                "id": page.id,
                "page_number": page.page_number,
                "file_path": page.file_path,
                "file_type": page.file_type,
                "ocr_text": page.ocr_text,
                "created_at": page.created_at.isoformat(),
            }
            for page in pages
        ],
    }


@router.get("/review")
def get_review_pages(db: Session = Depends(get_db)):
    """
    Hole alle verarbeiteten Seiten mit OCR-Ergebnissen für Review

    Returns:
        Liste von Seiten mit Dokument-Info und OCR-Status
    """
    import logging

    from sqlalchemy import func

    try:
        # Vereinfachte Abfrage: Hole alle Seiten, die OCR-Ergebnisse haben
        # Verwende eine Subquery für bessere Performance
        pages_with_ocr = (
            db.query(DocumentPage)
            .join(Document, DocumentPage.document_id == Document.id)
            .join(OCRResult, OCRResult.document_page_id == DocumentPage.id)
            .group_by(DocumentPage.id)
            .having(func.count(OCRResult.id) > 0)
            .order_by(DocumentPage.created_at.desc())
            .all()
        )

        result = []
        for page in pages_with_ocr:
            # Hole Dokument-Info
            document = (
                db.query(Document).filter(Document.id == page.document_id).first()
            )
            if not document:
                continue

            # Zähle OCR-Ergebnisse für diese Seite
            ocr_results = (
                db.query(OCRResult).filter(OCRResult.document_page_id == page.id).all()
            )
            ocr_count = len(ocr_results)

            # Finde letztes OCR-Datum
            last_ocr_at = None
            if ocr_results:
                last_ocr_at = max(r.created_at for r in ocr_results)

            # Prüfe ob BBox-Daten vorhanden sind
            has_bbox = any(r.bbox_data is not None for r in ocr_results)

            result.append(
                {
                    "page_id": page.id,
                    "document_id": page.document_id,
                    "document_title": document.title or document.filename,
                    "page_number": page.page_number,
                    "ocr_result_count": ocr_count,
                    "has_bbox": has_bbox,
                    "last_ocr_at": last_ocr_at.isoformat() if last_ocr_at else None,
                    "created_at": page.created_at.isoformat(),
                }
            )

        logging.info(
            f"Review-Endpoint: {len(result)} Seiten mit OCR-Ergebnissen gefunden"
        )
        return {"pages": result}

    except Exception as e:
        logging.error(f"Fehler im Review-Endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Review-Seiten: {e!s}",
        ) from None


@router.get("/{page_id}/preview")
def get_page_preview(
    page_id: int, thumbnail: bool = False, db: Session = Depends(get_db)
):
    """
    Hole Vorschau-Bild einer Seite

    Args:
        page_id: ID der Seite
        thumbnail: Wenn True, erstelle kleineres Thumbnail (400x400px)
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )

    # Wenn deskew_angle gesetzt: laden, begradigen (Drehpunkt 0,0), ggf. Thumbnail, ausliefern
    if page.deskew_angle is not None:
        img = _load_page_as_pil(page, db, dpi=150)
        img = deskew_image(img, page.deskew_angle)
        if thumbnail and PIL_AVAILABLE:
            from src.rotary_archiv.utils.pdf_utils import create_page_thumbnail

            img = create_page_thumbnail(img, size=(200, 200))
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            img.save(f.name, "PNG")
            return FileResponse(
                path=f.name,
                media_type="image/png",
                filename=f"page_{page.page_number}.png",
            )

    # Prüfe ob Seite ein file_path hat (extrahierte Seite) oder virtuell ist
    if page.file_path:
        # Normale Seite mit extrahierter Datei
        file_path = get_file_path(page.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seiten-Datei nicht gefunden: {file_path}",
            )

        # Wenn es ein Bild ist, direkt zurückgeben
        if page.file_type and page.file_type.lower() in [
            "image/png",
            "image/jpeg",
            "image/jpg",
        ]:
            return FileResponse(
                path=str(file_path),
                media_type=page.file_type,
                filename=f"page_{page.page_number}.{file_path.suffix[1:]}",
            )
    else:
        # Virtuelle Seite - extrahiere direkt aus PDF
        document = db.query(Document).filter(Document.id == page.document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
            )

        pdf_path = get_file_path(document.file_path)
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF-Datei nicht gefunden: {pdf_path}",
            )

        # Extrahiere Seite direkt aus PDF
        try:
            if not PDF2IMAGE_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="pdf2image ist nicht verfügbar. Bitte installieren: pip install pdf2image",
                )

            from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

            img = extract_page_as_image(str(pdf_path), page.page_number, dpi=150)

            # Wenn Thumbnail gewünscht
            if thumbnail and PIL_AVAILABLE:
                from src.rotary_archiv.utils.pdf_utils import create_page_thumbnail

                thumbnail_size = 200
                img = create_page_thumbnail(img, size=(thumbnail_size, thumbnail_size))

            # Speichere temporär
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                img.save(temp_file.name, "PNG")
                temp_path = temp_file.name

            return FileResponse(
                path=temp_path,
                media_type="image/png",
                filename=f"page_{page.page_number}.png",
            )
        except Exception as e:
            logging.error(
                f"Fehler beim Extrahieren der Seite aus PDF: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fehler beim Extrahieren der Seite: {e!s}",
            ) from None

    # Wenn es ein PDF ist (extrahierte PDF-Seite), konvertiere zu Bild für Vorschau
    if page.file_type == "pdf" or str(file_path).endswith(".pdf"):
        try:
            # Versuche PDF zu Bild zu konvertieren
            if PDF2IMAGE_AVAILABLE:
                from pdf2image import convert_from_path

                # Verwende benutzerdefinierten Poppler-Pfad falls konfiguriert
                convert_kwargs = {
                    "first_page": page.page_number,
                    "last_page": page.page_number,
                    "dpi": 150,
                }
                if settings.poppler_path:
                    poppler_path = Path(settings.poppler_path)
                    if poppler_path.exists():
                        convert_kwargs["poppler_path"] = str(poppler_path)

                images = convert_from_path(str(file_path), **convert_kwargs)
                if images:
                    img = images[0]

                    # Wenn Thumbnail gewünscht
                    if thumbnail and PIL_AVAILABLE:
                        from src.rotary_archiv.utils.pdf_utils import (
                            create_page_thumbnail,
                        )

                        thumbnail_size = 200
                        img = create_page_thumbnail(
                            img, size=(thumbnail_size, thumbnail_size)
                        )

                    # Speichere temporär
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".png"
                    ) as temp_file:
                        img.save(temp_file.name, "PNG")
                        temp_path = temp_file.name

                    return FileResponse(
                        path=temp_path,
                        media_type="image/png",
                        filename=f"page_{page.page_number}.png",
                    )
        except Exception as e:
            logging.warning(f"PDF zu Bild Konvertierung fehlgeschlagen: {e}")
            # Fallback: PDF direkt zurückgeben
            return FileResponse(
                path=str(file_path),
                media_type="application/pdf",
                filename=f"page_{page.page_number}.pdf",
            )

    # Bestimme Media-Type für Bilder
    if page.file_type in ["png", "jpg", "jpeg"]:
        media_type = f"image/{page.file_type}"

        # Wenn Thumbnail gewünscht und es ein Bild ist
        if thumbnail and PIL_AVAILABLE:
            try:
                img = Image.open(file_path)
                # Erstelle Thumbnail (200x200px)
                from src.rotary_archiv.utils.pdf_utils import create_page_thumbnail

                thumbnail_size = 200
                img = create_page_thumbnail(img, size=(thumbnail_size, thumbnail_size))

                # Speichere Thumbnail temporär
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png"
                ) as temp_file:
                    img.save(temp_file.name, "PNG")
                    temp_path = temp_file.name

                return FileResponse(
                    path=temp_path,
                    media_type="image/png",
                    filename=f"page_{page.page_number}_thumb.png",
                )
            except ImportError:
                # PIL nicht verfügbar, verwende Original
                pass
            except Exception as e:
                logging.warning(
                    f"Thumbnail-Erstellung fehlgeschlagen: {e}, verwende Original"
                )
    else:
        media_type = "application/pdf"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"page_{page.page_number}.{page.file_type}",
    )


def _load_page_as_pil(page: DocumentPage, db: Session, dpi: int = 150) -> "Image.Image":
    """Lädt eine DocumentPage als PIL Image. Erfordert PIL; bei PDF pdf2image."""
    if not PIL_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PIL/Pillow ist nicht verfügbar",
        )
    if not page.file_path:
        document = db.query(Document).filter(Document.id == page.document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
            )
        pdf_path = get_file_path(document.file_path)
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF nicht gefunden: {pdf_path}",
            )
        if not PDF2IMAGE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="pdf2image ist für PDF-Extraktion nötig",
            )
        return extract_page_as_image(str(pdf_path), page.page_number, dpi=dpi)
    fp = get_file_path(page.file_path)
    if not fp.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Seiten-Datei nicht gefunden: {fp}",
        )
    is_img = (
        page.file_type
        and page.file_type.lower() in ("image/png", "image/jpeg", "image/jpg")
    ) or str(fp).lower().endswith((".png", ".jpg", ".jpeg"))
    if is_img:
        return Image.open(fp).convert("RGB")
    if str(fp).lower().endswith(".pdf") or (
        page.file_type and "pdf" in (page.file_type or "").lower()
    ):
        if not PDF2IMAGE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="pdf2image ist für PDF-Konvertierung nötig",
            )
        from pdf2image import convert_from_path

        convert_kwargs = {
            "first_page": page.page_number,
            "last_page": page.page_number,
            "dpi": dpi,
        }
        if settings.poppler_path:
            pp = Path(settings.poppler_path)
            if pp.exists():
                convert_kwargs["poppler_path"] = str(pp)
        images = convert_from_path(str(fp), **convert_kwargs)
        if not images:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF konnte nicht zu Bild konvertiert werden",
            )
        return images[0]
    return Image.open(fp).convert("RGB")


@router.get("/{page_id}/skew")
def get_page_skew(page_id: int, db: Session = Depends(get_db)):
    """
    Misst den Schrägwinkel (Skew) einer Seite per Hough-Transformation.

    Drehpunkt bei Koordinatentransformation: obere linke Ecke (0,0).
    Response: angle / angle_deg in Grad.
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )
    img = _load_page_as_pil(page, db, dpi=200)
    angle = detect_skew_angle(img)
    return {"angle": angle, "angle_deg": angle}


@router.get("/{page_id}/skew/debug")
def get_page_skew_debug(page_id: int, db: Session = Depends(get_db)):
    """
    Misst den Schrägwinkel (Skew) mit detaillierten Debug-Informationen.

    Gibt zurück:
    - angle: Erkannte Winkel in Grad
    - total_lines: Anzahl aller erkannten Linien
    - valid_angles: Liste aller gültigen Winkel
    - angle_stats: Statistiken (min, max, median, mean, std, count)
    - lines_info: Details zu jeder erkannten Linie
    - canny_params: Parameter für Canny-Edge-Detection
    - hough_params: Parameter für Hough-Transformation
    """
    from src.rotary_archiv.utils.image_utils import detect_skew_angle_debug

    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )
    img = _load_page_as_pil(page, db, dpi=200)
    debug_info = detect_skew_angle_debug(img)
    return debug_info


@router.get("/{page_id}/deskewed-image")
def get_deskewed_page_image(page_id: int, db: Session = Depends(get_db)):
    """
    Gibt das begradigte (deskewed) Bild einer Seite zurück.

    Falls deskew_angle in der DocumentPage gesetzt ist, wird dieser verwendet.
    Andernfalls wird der Winkel automatisch erkannt.
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )

    img = _load_page_as_pil(page, db, dpi=200)

    # Verwende gespeicherten Winkel oder erkenne automatisch
    if page.deskew_angle is not None:
        angle = page.deskew_angle
    else:
        angle = detect_skew_angle(img)
        if abs(angle) < 0.1:
            # Keine nennenswerte Schräge, gebe Original zurück
            angle = 0.0

    if abs(angle) > 0.1:
        img = deskew_image(img, angle)

    # Speichere als temporäre Datei und gebe zurück
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        img.save(tmp_file.name, "PNG")
        return FileResponse(
            tmp_file.name,
            media_type="image/png",
            filename=f"page_{page_id}_deskewed.png",
        )


@router.get("/{page_id}/skew/lines")
def get_page_skew_lines(page_id: int, db: Session = Depends(get_db)):
    """
    Gibt die erkannten Linien für die Schräglagen-Erkennung zurück.

    Returns:
        Dictionary mit:
        - lines: Liste der Linien mit Koordinaten (im Bild-Koordinatensystem)
        - image_width: Breite des Bildes
        - image_height: Höhe des Bildes
        - angle: Erkannte Winkel
    """
    from src.rotary_archiv.utils.image_utils import detect_skew_angle_debug

    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )
    img = _load_page_as_pil(page, db, dpi=200)
    debug_info = detect_skew_angle_debug(img)

    # Konvertiere Linien-Info in einfaches Format für Frontend
    lines = []
    if debug_info.get("lines_info"):
        for line_info in debug_info["lines_info"]:
            # Nur gültige Linien zurückgeben (oder alle, je nach Präferenz)
            if line_info.get("is_valid", False):
                lines.append(
                    {
                        "x1": line_info["x1"],
                        "y1": line_info["y1"],
                        "x2": line_info["x2"],
                        "y2": line_info["y2"],
                        "angle": line_info["normalized_angle"],
                        "length": line_info["length"],
                    }
                )

    return {
        "lines": lines,
        "image_width": img.width,
        "image_height": img.height,
        "angle": debug_info["angle"],
        "total_lines": debug_info["total_lines"],
        "valid_lines": len(lines),
    }


@router.post("/merge")
def merge_pages(request: MergePagesRequest, db: Session = Depends(get_db)):
    """
    Füge mehrere Seiten zu einem Dokument zusammen

    Args:
        page_ids: Liste von Seiten-IDs die zusammengefügt werden sollen
        title: Optional: Titel für das zusammengesetzte Dokument
    """
    if not request.page_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mindestens eine Seite muss angegeben werden",
        )

    # Hole Seiten
    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.id.in_(request.page_ids))
        .order_by(DocumentPage.page_number)
        .all()
    )

    if len(pages) != len(request.page_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nicht alle Seiten gefunden"
        )

    # Erstelle zusammengesetztes Dokument
    # Für jetzt: Wir verknüpfen die Seiten nur, später können wir ein neues PDF erstellen
    from datetime import datetime
    import uuid

    # Erstelle neues Dokument (Platzhalter)
    composite_doc = Document(
        filename=f"Zusammengefügtes_Dokument_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        file_path=f"composite/{uuid.uuid4()}.pdf",  # Platzhalter
        file_type="application/pdf",
        is_composite=1,
        title=request.title,  # Kann None sein
        status=DocumentStatus.UPLOADED,  # Setze Status explizit
    )

    db.add(composite_doc)
    db.commit()
    db.refresh(composite_doc)

    # Verknüpfe Seiten mit zusammengesetztem Dokument
    for idx, page in enumerate(pages, start=1):
        # Erstelle Referenz-Dokument für jede Seite
        page_doc = Document(
            filename=f"{composite_doc.filename}_Seite_{idx}",
            file_path=page.file_path,
            file_type=page.file_type,
            parent_document_id=composite_doc.id,
            is_composite=0,
            page_number=idx,
        )
        db.add(page_doc)

    db.commit()

    return {
        "composite_document_id": composite_doc.id,
        "title": composite_doc.title or composite_doc.filename,
        "pages_count": len(pages),
        "page_ids": request.page_ids,
    }


@router.get("/{page_id}/inspect", response_model=PageInspectResponse)
def get_page_inspect(page_id: int, db: Session = Depends(get_db)):
    """
    Hole Page Inspect Daten mit Bounding Boxes für Leaflet-View

    Returns:
        PageInspectResponse mit Bild-URL, Dimensionen und OCR-Ergebnissen mit BBoxes
    """
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seite nicht gefunden"
        )

    # Lade Dokument für PDF-Pfad falls nötig
    document = db.query(Document).filter(Document.id == page.document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Ermittle Bild-Dimensionen
    image_width = 0
    image_height = 0

    try:
        # Wenn Seite bereits ein Bild ist
        if page.file_path and page.file_type in ["png", "jpg", "jpeg"]:
            file_path = get_file_path(page.file_path)
            if file_path.exists() and PIL_AVAILABLE:
                img = Image.open(file_path)
                image_width, image_height = img.size
        else:
            # Extrahiere Seite aus PDF als Bild
            # Verwende die gleichen Dimensionen wie beim OCR (falls verfügbar)
            pdf_path = get_file_path(document.file_path)
            if pdf_path.exists():
                # Prüfe ob OCR-Ergebnisse vorhanden sind und verwende deren Dimensionen
                ocr_results = (
                    db.query(OCRResult)
                    .filter(OCRResult.document_page_id == page_id)
                    .order_by(OCRResult.created_at.desc())
                    .limit(1)
                    .all()
                )

                if (
                    ocr_results
                    and ocr_results[0].image_width
                    and ocr_results[0].image_height
                ):
                    # Verwende OCR-Bild-Dimensionen (wichtig für korrekte BBox-Positionierung)
                    image_width = ocr_results[0].image_width
                    image_height = ocr_results[0].image_height
                    logging.info(
                        f"Verwende OCR-Bild-Dimensionen für Preview: {image_width}x{image_height}"
                    )
                else:
                    # Fallback: Extrahiere Seite und ermittle Dimensionen
                    img = extract_page_as_image(str(pdf_path), page.page_number)
                    image_width, image_height = img.size
    except Exception as e:
        logging.warning(f"Konnte Bild-Dimensionen nicht ermitteln: {e}")

    # Lade OCR-Ergebnisse mit BBox-Daten
    ocr_results = (
        db.query(OCRResult)
        .filter(OCRResult.document_page_id == page_id)
        .order_by(OCRResult.created_at.desc())
        .all()
    )

    # Konvertiere zu Response-Schemas
    from src.rotary_archiv.api.schemas import BBoxItem

    ocr_result_responses = []
    for ocr_result in ocr_results:
        # Konvertiere bbox_data JSON zu BBoxItem-Liste
        bbox_items = None
        if ocr_result.bbox_data:
            try:
                bbox_items = [
                    BBoxItem(
                        text=item.get("text", ""),
                        bbox=item.get("bbox", []),
                        bbox_pixel=item.get("bbox_pixel", []),
                        review_status=item.get("review_status", "pending"),
                        reviewed_at=item.get("reviewed_at"),
                        reviewed_by=item.get("reviewed_by"),
                        ocr_results=item.get("ocr_results"),
                        differences=item.get("differences", []),
                    )
                    for item in ocr_result.bbox_data
                ]
            except Exception as e:
                logging.warning(f"Fehler beim Konvertieren von bbox_data: {e}")

        # Erstelle Response mit konvertierten BBox-Daten
        ocr_dict = {
            "id": ocr_result.id,
            "document_id": ocr_result.document_id,
            "document_page_id": ocr_result.document_page_id,
            "source": ocr_result.source,
            "engine_version": ocr_result.engine_version,
            "text": ocr_result.text,
            "confidence": ocr_result.confidence,
            "confidence_details": ocr_result.confidence_details,
            "processing_time_ms": ocr_result.processing_time_ms,
            "language": ocr_result.language,
            "error_message": ocr_result.error_message,
            "created_at": ocr_result.created_at,
            "bbox_data": bbox_items,
            "image_width": ocr_result.image_width,
            "image_height": ocr_result.image_height,
        }
        ocr_result_responses.append(OCRResultResponse(**ocr_dict))

    # Bild-URL (verwende preview endpoint)
    image_url = f"/api/pages/{page_id}/preview"

    # Verwende OCR-Bild-Dimensionen falls verfügbar (genauer für BBox-Koordinaten)
    # Falls keine OCR-Ergebnisse vorhanden, verwende die ermittelten Dimensionen
    if ocr_result_responses:
        # Verwende Dimensionen aus dem ersten OCR-Result (sollten alle gleich sein)
        ocr_result = ocr_result_responses[0]
        if ocr_result.image_width and ocr_result.image_height:
            image_width = ocr_result.image_width
            image_height = ocr_result.image_height
            logging.info(
                f"Verwende OCR-Bild-Dimensionen: {image_width}x{image_height} für Seite {page_id}"
            )

    return PageInspectResponse(
        page_id=page.id,
        document_id=page.document_id,
        page_number=page.page_number,
        image_url=image_url,
        image_width=image_width,
        image_height=image_height,
        ocr_results=ocr_result_responses,
    )
