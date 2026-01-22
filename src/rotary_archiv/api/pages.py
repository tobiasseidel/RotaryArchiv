"""
API Endpoints für Dokument-Seiten
"""

import logging
from pathlib import Path
import tempfile
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
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
