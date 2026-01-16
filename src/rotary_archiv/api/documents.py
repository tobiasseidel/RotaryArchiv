"""
API Endpoints für Dokumente
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import (
    DocumentResponse,
    DocumentUpdate,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import Document, DocumentStatus
from src.rotary_archiv.utils.file_handler import get_file_size, save_uploaded_file

# Optional imports für OCR und NLP
try:
    from src.rotary_archiv.ocr.pipeline import OCRPipeline

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRPipeline = None

try:
    from src.rotary_archiv.nlp.classification import DocumentClassifier

    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    DocumentClassifier = None

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Lade neues Dokument hoch
    """
    import traceback

    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kein Dateiname angegeben",
            )

        # Lese Datei-Inhalt
        file_content = await file.read()

        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Datei ist leer"
            )

        # Speichere Datei
        file_path = save_uploaded_file(file_content, file.filename)
        file_size = get_file_size(file_path)

        # Erstelle Dokument in DB
        db_document = Document(
            filename=file.filename,
            file_path=file_path,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            status=DocumentStatus.UPLOADED,
            is_composite=0,  # Explizit setzen
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        return db_document

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"Upload Fehler: {e!s}")
        logging.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Hochladen: {e!s}",
        ) from e


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    status_filter: DocumentStatus | None = None,
    db: Session = Depends(get_db),
):
    """
    Liste alle Dokumente
    """
    query = db.query(Document)

    if status_filter:
        query = query.filter(Document.status == status_filter)

    documents = query.offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Hole einzelnes Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int, document_update: DocumentUpdate, db: Session = Depends(get_db)
):
    """
    Aktualisiere Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Update Felder
    update_data = document_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Lösche Dokument und alle zugehörigen Daten

    Löscht:
    - Hauptdatei
    - Alle extrahierten Seiten (DocumentPage) und deren Dateien
    - Alle Metadaten (automatisch durch Cascade)
    - Alle Annotationen (automatisch durch Cascade)
    - Alle Child-Dokumente (falls Composite-Dokument)
    """
    import logging

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    try:
        # Lösche alle zugehörigen Seiten und deren Dateien
        from src.rotary_archiv.core.models import DocumentPage
        from src.rotary_archiv.utils.file_handler import delete_file

        pages = (
            db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        )
        logging.info(f"Lösche {len(pages)} Seiten für Dokument {document_id}")

        for page in pages:
            # Lösche Seiten-Datei
            try:
                delete_file(page.file_path)
                logging.info(f"Seiten-Datei gelöscht: {page.file_path}")
            except Exception as e:
                logging.warning(
                    f"Konnte Seiten-Datei nicht löschen {page.file_path}: {e}"
                )

        # Lösche Child-Dokumente (falls Composite-Dokument)
        if document.is_composite:
            child_docs = (
                db.query(Document)
                .filter(Document.parent_document_id == document_id)
                .all()
            )
            logging.info(
                f"Lösche {len(child_docs)} Child-Dokumente für Composite-Dokument {document_id}"
            )

            for child_doc in child_docs:
                # Lösche Child-Dokument Datei
                try:
                    delete_file(child_doc.file_path)
                except Exception as e:
                    logging.warning(
                        f"Konnte Child-Dokument-Datei nicht löschen {child_doc.file_path}: {e}"
                    )

        # Lösche Hauptdatei
        try:
            delete_file(document.file_path)
            logging.info(f"Hauptdatei gelöscht: {document.file_path}")
        except Exception as e:
            logging.warning(
                f"Konnte Hauptdatei nicht löschen {document.file_path}: {e}"
            )

        # Lösche Dokument aus Datenbank (Cascade löscht automatisch Metadaten, Annotationen, Pages)
        db.delete(document)
        db.commit()

        logging.info(
            f"Dokument {document_id} '{document.filename}' erfolgreich gelöscht"
        )
        return None

    except Exception as e:
        logging.error(f"Fehler beim Löschen von Dokument {document_id}: {e}")
        import traceback

        logging.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Löschen des Dokuments: {e!s}",
        ) from e


@router.post("/{document_id}/ocr", response_model=DocumentResponse)
async def process_ocr(
    document_id: int,
    language: str = "deu+eng",
    use_correction: bool = True,
    db: Session = Depends(get_db),
):
    """
    Führe OCR auf Dokument aus
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Update Status
    document.status = DocumentStatus.OCR_PENDING
    db.commit()

    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR-Pipeline nicht verfügbar. Bitte Dependencies installieren.",
        )

    try:
        # OCR Pipeline
        pipeline = OCRPipeline()
        ocr_result = await pipeline.process_document(
            document.file_path, language=language, use_correction=use_correction
        )

        # Speichere Ergebnisse
        document.ocr_text = ocr_result["text"]
        document.ocr_text_tesseract = ocr_result["tesseract"].get("text")
        document.ocr_text_ollama = ocr_result["ollama_vision"].get("text")
        document.ocr_confidence = str(
            ocr_result.get("tesseract", {}).get("confidence", 0)
        )
        document.status = DocumentStatus.OCR_DONE

        db.commit()
        db.refresh(document)

        return document

    except Exception as e:
        document.status = DocumentStatus.UPLOADED  # Rollback
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Fehler: {e!s}",
        ) from e


@router.post("/{document_id}/classify", response_model=DocumentResponse)
def classify_document(document_id: int, db: Session = Depends(get_db)):
    """
    Klassifiziere Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    if not document.ocr_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dokument muss zuerst OCR durchlaufen",
        )

    if not CLASSIFIER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klassifizierung nicht verfügbar. Bitte Dependencies installieren.",
        )

    # Klassifizierung
    classifier = DocumentClassifier()
    classification = classifier.classify_document(document.ocr_text, document.filename)

    # Update Dokument
    document.document_type = classification.get("document_type")
    document.status = DocumentStatus.CLASSIFIED

    db.commit()
    db.refresh(document)

    return document
