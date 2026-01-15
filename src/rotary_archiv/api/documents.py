"""
API Endpoints für Dokumente
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import Document, DocumentStatus, DocumentType
from src.rotary_archiv.api.schemas import (
    DocumentCreate, DocumentUpdate, DocumentResponse
)
from src.rotary_archiv.utils.file_handler import save_uploaded_file, get_file_size

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
async def create_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Lade neues Dokument hoch
    """
    try:
        # Lese Datei-Inhalt
        file_content = await file.read()
        
        # Speichere Datei
        file_path = save_uploaded_file(file_content, file.filename)
        file_size = get_file_size(file_path)
        
        # Erstelle Dokument in DB
        db_document = Document(
            filename=file.filename,
            file_path=file_path,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            status=DocumentStatus.UPLOADED
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return db_document
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Hochladen: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[DocumentStatus] = None,
    db: Session = Depends(get_db)
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
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Hole einzelnes Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """
    Aktualisiere Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    # Update Felder
    update_data = document_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Lösche Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    # Lösche Datei
    from src.rotary_archiv.utils.file_handler import delete_file
    delete_file(document.file_path)
    
    db.delete(document)
    db.commit()
    
    return None


@router.post("/{document_id}/ocr", response_model=DocumentResponse)
async def process_ocr(
    document_id: int,
    language: str = "deu+eng",
    use_correction: bool = True,
    db: Session = Depends(get_db)
):
    """
    Führe OCR auf Dokument aus
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    # Update Status
    document.status = DocumentStatus.OCR_PENDING
    db.commit()
    
    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR-Pipeline nicht verfügbar. Bitte Dependencies installieren."
        )
    
    try:
        # OCR Pipeline
        pipeline = OCRPipeline()
        ocr_result = await pipeline.process_document(
            document.file_path,
            language=language,
            use_correction=use_correction
        )
        
        # Speichere Ergebnisse
        document.ocr_text = ocr_result["text"]
        document.ocr_text_tesseract = ocr_result["tesseract"].get("text")
        document.ocr_text_ollama = ocr_result["ollama_vision"].get("text")
        document.ocr_confidence = str(ocr_result.get("tesseract", {}).get("confidence", 0))
        document.status = DocumentStatus.OCR_DONE
        
        db.commit()
        db.refresh(document)
        
        return document
        
    except Exception as e:
        document.status = DocumentStatus.UPLOADED  # Rollback
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Fehler: {str(e)}"
        )


@router.post("/{document_id}/classify", response_model=DocumentResponse)
def classify_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Klassifiziere Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden"
        )
    
    if not document.ocr_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dokument muss zuerst OCR durchlaufen"
        )
    
    if not CLASSIFIER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Klassifizierung nicht verfügbar. Bitte Dependencies installieren."
        )
    
    # Klassifizierung
    classifier = DocumentClassifier()
    classification = classifier.classify_document(
        document.ocr_text,
        document.filename
    )
    
    # Update Dokument
    document.document_type = classification.get("document_type")
    document.status = DocumentStatus.CLASSIFIED
    
    db.commit()
    db.refresh(document)
    
    return document
