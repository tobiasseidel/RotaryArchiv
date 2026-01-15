"""
API Endpoints für Dokument-Seiten
"""
import traceback
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pathlib import Path

from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import Document, DocumentPage
from src.rotary_archiv.api.schemas import DocumentResponse
from src.rotary_archiv.utils.pdf_splitter import PDFSplitter, PDF2IMAGE_AVAILABLE
from src.rotary_archiv.utils.file_handler import get_file_path
from src.rotary_archiv.config import settings

router = APIRouter(prefix="/api/pages", tags=["pages"])


class MergePagesRequest(BaseModel):
    """Request für Seiten-Zusammenführung"""
    page_ids: List[int]
    title: Optional[str] = None


@router.post("/document/{document_id}/extract")
def extract_pages(
    document_id: int,
    output_format: str = "image",  # Standard: "image" für Vorschau
    db: Session = Depends(get_db)
):
    """
    Extrahiere Seiten aus einem PDF-Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    if document.file_type.lower() != "application/pdf" and not document.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien können in Seiten extrahiert werden"
        )
    
    try:
        # Prüfe ob Datei existiert
        file_path = get_file_path(document.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Datei nicht gefunden: {file_path}"
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
                file_type=page_info["file_type"]
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
                    "file_type": page.file_type
                }
                for page in created_pages
            ],
            "total_pages": len(created_pages)
        }
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logging.error(f"Datei nicht gefunden: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei nicht gefunden: {str(e)}"
        )
    except MemoryError:
        logging.error("Nicht genug Speicher für große PDF-Datei")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF-Datei ist zu groß. Bitte verwende eine kleinere Datei oder reduziere die DPI-Einstellung."
        )
    except TimeoutError:
        logging.error("Timeout bei PDF-Verarbeitung")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="PDF-Verarbeitung dauerte zu lange. Bitte versuche es mit einer kleineren Datei."
        )
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Seiten-Extraktion Fehler: {error_msg}")
        logging.error(traceback.format_exc())
        db.rollback()
        
        # Spezifische Fehlermeldungen
        if "poppler" in error_msg.lower() or "pdftoppm" in error_msg.lower():
            detail = f"Poppler-Fehler: {error_msg}\nBitte prüfe die Poppler-Installation und POPPLER_PATH in .env"
        elif "memory" in error_msg.lower() or "speicher" in error_msg.lower():
            detail = f"Speicherfehler: Die PDF-Datei ist möglicherweise zu groß. {error_msg}"
        else:
            detail = f"Fehler beim Extrahieren der Seiten: {error_msg}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


@router.get("/document/{document_id}")
def get_document_pages(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Hole alle Seiten eines Dokuments
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id
    ).order_by(DocumentPage.page_number).all()
    
    return {
        "document_id": document_id,
        "pages": [
            {
                "id": page.id,
                "page_number": page.page_number,
                "file_path": page.file_path,
                "file_type": page.file_type,
                "ocr_text": page.ocr_text,
                "created_at": page.created_at.isoformat()
            }
            for page in pages
        ]
    }


@router.get("/{page_id}/preview")
def get_page_preview(
    page_id: int,
    thumbnail: bool = False,
    db: Session = Depends(get_db)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seite nicht gefunden"
        )
    
    file_path = get_file_path(page.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Seiten-Datei nicht gefunden: {file_path}"
        )
    
    # Wenn es ein PDF ist, konvertiere zu Bild für Vorschau
    if page.file_type == "pdf" or str(file_path).endswith(".pdf"):
        try:
            # Versuche PDF zu Bild zu konvertieren
            if PDF2IMAGE_AVAILABLE:
                from pdf2image import convert_from_path
                # Verwende benutzerdefinierten Poppler-Pfad falls konfiguriert
                convert_kwargs = {
                    "first_page": page.page_number,
                    "last_page": page.page_number,
                    "dpi": 150
                }
                if settings.poppler_path:
                    poppler_path = Path(settings.poppler_path)
                    if poppler_path.exists():
                        convert_kwargs["poppler_path"] = str(poppler_path)
                
                images = convert_from_path(str(file_path), **convert_kwargs)
                if images:
                    img = images[0]
                    
                    # Wenn Thumbnail gewünscht
                    if thumbnail:
                        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                    
                    # Speichere temporär
                    import tempfile
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    img.save(temp_file.name, "PNG")
                    temp_file.close()
                    
                    return FileResponse(
                        path=temp_file.name,
                        media_type="image/png",
                        filename=f"page_{page.page_number}.png"
                    )
        except Exception as e:
            logging.warning(f"PDF zu Bild Konvertierung fehlgeschlagen: {e}")
            # Fallback: PDF direkt zurückgeben
            return FileResponse(
                path=str(file_path),
                media_type="application/pdf",
                filename=f"page_{page.page_number}.pdf"
            )
    
    # Bestimme Media-Type für Bilder
    if page.file_type in ["png", "jpg", "jpeg"]:
        media_type = f"image/{page.file_type}"
        
        # Wenn Thumbnail gewünscht und es ein Bild ist
        if thumbnail:
            try:
                from PIL import Image
                img = Image.open(file_path)
                # Erstelle Thumbnail (max 400px)
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                
                # Speichere Thumbnail temporär
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                img.save(temp_file.name, "PNG")
                temp_file.close()
                
                return FileResponse(
                    path=temp_file.name,
                    media_type="image/png",
                    filename=f"page_{page.page_number}_thumb.png"
                )
            except ImportError:
                # PIL nicht verfügbar, verwende Original
                pass
            except Exception as e:
                logging.warning(f"Thumbnail-Erstellung fehlgeschlagen: {e}, verwende Original")
    else:
        media_type = "application/pdf"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"page_{page.page_number}.{page.file_type}"
    )


@router.post("/merge")
def merge_pages(
    request: MergePagesRequest,
    db: Session = Depends(get_db)
):
    """
    Füge mehrere Seiten zu einem Dokument zusammen
    
    Args:
        page_ids: Liste von Seiten-IDs die zusammengefügt werden sollen
        title: Optional: Titel für das zusammengesetzte Dokument
    """
    if not request.page_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mindestens eine Seite muss angegeben werden"
        )
    
    # Hole Seiten
    pages = db.query(DocumentPage).filter(
        DocumentPage.id.in_(request.page_ids)
    ).order_by(DocumentPage.page_number).all()
    
    if len(pages) != len(request.page_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nicht alle Seiten gefunden"
        )
    
    # Erstelle zusammengesetztes Dokument
    # Für jetzt: Wir verknüpfen die Seiten nur, später können wir ein neues PDF erstellen
    from src.rotary_archiv.utils.file_handler import ensure_documents_dir
    import uuid
    from datetime import datetime
    
    # Erstelle neues Dokument (Platzhalter)
    composite_doc = Document(
        filename=request.title or f"Zusammengefügtes_Dokument_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        file_path=f"composite/{uuid.uuid4()}.pdf",  # Platzhalter
        file_type="application/pdf",
        is_composite=1,
        title=request.title
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
            page_number=idx
        )
        db.add(page_doc)
    
    db.commit()
    
    return {
        "composite_document_id": composite_doc.id,
        "title": composite_doc.title or composite_doc.filename,
        "pages_count": len(pages),
        "page_ids": request.page_ids
    }
