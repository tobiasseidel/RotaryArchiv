"""
API Endpoints für Dokumente
"""

import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import (
    ComposedUnitOverviewItem,
    DocumentListEntry,
    DocumentResponse,
    DocumentUnitCreate,
    DocumentUnitResponse,
    DocumentUnitSuggestionResponse,
    DocumentUnitUpdate,
    DocumentUpdate,
    UnassignedPageItem,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentStatus,
    DocumentUnit,
    DocumentUnitSuggestion,
)
from src.rotary_archiv.services import document_service
from src.rotary_archiv.services.document_service import (
    DocumentNotFoundError,
    DocumentServiceError,
    InvalidPageError,
)

# NOTE: NLP-Klassifikation vorerst nicht verwendet
CLASSIFIER_AVAILABLE = False
DocumentClassifier = None

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Lade neues Dokument hoch
    """
    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kein Dateiname angegeben",
            )

        file_content = await file.read()

        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Datei ist leer"
            )

        db_document = document_service.create_document(
            db,
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )
        return db_document

    except HTTPException:
        raise
    except DocumentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logging.error("Upload Fehler: %s", e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Hochladen: {e!s}",
        ) from e


@router.get("/summary", response_model=list[DocumentListEntry])
def list_documents_summary(
    skip: int = 0,
    limit: int = 500,
    status_filter: DocumentStatus | None = None,
    db: Session = Depends(get_db),
):
    """
    Leichte Liste aller Dokumente (id, filename, title, status) für Dropdowns.
    Kein OCR-Text, keine Relationships - schnell und kleine Antwort.
    """
    rows = document_service.list_documents_summary(
        db, skip=skip, limit=limit, status_filter=status_filter
    )
    return [
        DocumentListEntry(
            id=d["id"], filename=d["filename"], title=d["title"], status=d["status"]
        )
        for d in rows
    ]


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    status_filter: DocumentStatus | None = None,
    db: Session = Depends(get_db),
):
    """
    Liste alle Dokumente (vollständige Response inkl. Metadaten).
    Für Dropdowns/Listen bevorzugen: GET /api/documents/summary
    """
    return document_service.list_documents(
        db, skip=skip, limit=limit, status_filter=status_filter
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Hole einzelnes Dokument
    """
    try:
        return document_service.get_document(db, document_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{document_id}/units", response_model=list[DocumentUnitResponse])
def get_document_units(document_id: int, db: Session = Depends(get_db)):
    """
    Hole alle Content-Analyse-Einheiten (document_units) für ein Dokument.
    """
    try:
        units = document_service.get_document_units(db, document_id)
        return [DocumentUnitResponse.model_validate(u) for u in units]
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/{document_id}/units/{unit_id}",
    response_model=DocumentUnitResponse,
)
def get_document_unit(document_id: int, unit_id: int, db: Session = Depends(get_db)):
    """Hole eine einzelne Content-Analyse-Einheit."""
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.id == unit_id,
            DocumentUnit.document_id == document_id,
        )
        .first()
    )
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Einheit nicht gefunden"
        )
    return DocumentUnitResponse.model_validate(unit)


@router.get(
    "/{document_id}/unassigned-pages",
    response_model=list[UnassignedPageItem],
)
def get_unassigned_pages(document_id: int, db: Session = Depends(get_db)):
    """
    Seiten des Dokuments, die noch keiner DocumentUnit zugeordnet sind.
    Pro Seite wird full_text (BBox-Inhalt in Lesereihenfolge) mitgeliefert
    für manuelle Grenzen-Zuordnung.
    """
    try:
        pages = document_service.get_unassigned_pages(db, document_id)
        return [
            UnassignedPageItem(
                page_id=p["page_id"],
                page_number=p["page_number"],
                full_text=p["full_text"],
            )
            for p in pages
        ]
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/{document_id}/unit-suggestions",
    response_model=list[DocumentUnitSuggestionResponse],
)
def get_unit_suggestions(document_id: int, db: Session = Depends(get_db)):
    """Liste aller Einheiten-Vorschläge für das Dokument."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )
    suggestions = (
        db.query(DocumentUnitSuggestion)
        .filter(DocumentUnitSuggestion.document_id == document_id)
        .order_by(DocumentUnitSuggestion.id)
        .all()
    )
    return [DocumentUnitSuggestionResponse.model_validate(s) for s in suggestions]


@router.post(
    "/{document_id}/unit-suggestions/accept-all",
    response_model=list[DocumentUnitResponse],
)
def accept_all_unit_suggestions(document_id: int, db: Session = Depends(get_db)):
    """Alle Vorschläge des Dokuments in DocumentUnits überführen und Vorschläge löschen."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )
    suggestions = (
        db.query(DocumentUnitSuggestion)
        .filter(DocumentUnitSuggestion.document_id == document_id)
        .order_by(DocumentUnitSuggestion.id)
        .all()
    )
    created = []
    for s in suggestions:
        unit = DocumentUnit(
            document_id=document_id,
            page_ids=s.page_ids,
            belongs_with_next=s.belongs_with_next,
        )
        db.add(unit)
        db.flush()
        created.append(unit)
    for s in suggestions:
        db.delete(s)
    db.commit()
    for u in created:
        db.refresh(u)
    return [DocumentUnitResponse.model_validate(u) for u in created]


@router.post(
    "/{document_id}/unit-suggestions/{suggestion_id}/accept",
    response_model=DocumentUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
def accept_unit_suggestion(
    document_id: int, suggestion_id: int, db: Session = Depends(get_db)
):
    """Einen Vorschlag in eine DocumentUnit überführen und Vorschlag löschen."""
    suggestion = (
        db.query(DocumentUnitSuggestion)
        .filter(
            DocumentUnitSuggestion.id == suggestion_id,
            DocumentUnitSuggestion.document_id == document_id,
        )
        .first()
    )
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vorschlag nicht gefunden",
        )
    unit = DocumentUnit(
        document_id=document_id,
        page_ids=suggestion.page_ids,
        belongs_with_next=suggestion.belongs_with_next,
    )
    db.add(unit)
    db.delete(suggestion)
    db.commit()
    db.refresh(unit)
    return DocumentUnitResponse.model_validate(unit)


@router.delete(
    "/{document_id}/unit-suggestions/{suggestion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reject_unit_suggestion(
    document_id: int, suggestion_id: int, db: Session = Depends(get_db)
):
    """Einzelnen Vorschlag verwerfen."""
    suggestion = (
        db.query(DocumentUnitSuggestion)
        .filter(
            DocumentUnitSuggestion.id == suggestion_id,
            DocumentUnitSuggestion.document_id == document_id,
        )
        .first()
    )
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vorschlag nicht gefunden",
        )
    db.delete(suggestion)
    db.commit()
    return None


@router.post(
    "/{document_id}/units",
    response_model=DocumentUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document_unit(
    document_id: int, body: DocumentUnitCreate, db: Session = Depends(get_db)
):
    """Einheit manuell anlegen (Seiten auswählen)."""
    try:
        unit = document_service.create_document_unit(db, document_id, body)
        return DocumentUnitResponse.model_validate(unit)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except InvalidPageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.put(
    "/{document_id}/units/{unit_id}",
    response_model=DocumentUnitResponse,
)
def update_document_unit(
    document_id: int,
    unit_id: int,
    body: DocumentUnitUpdate,
    db: Session = Depends(get_db),
):
    """Einheit bearbeiten (Seiten/Inhalt)."""
    try:
        unit = document_service.update_document_unit(db, document_id, unit_id, body)
        return DocumentUnitResponse.model_validate(unit)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except InvalidPageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.delete(
    "/{document_id}/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document_unit(document_id: int, unit_id: int, db: Session = Depends(get_db)):
    """Einheit löschen."""
    try:
        document_service.delete_document_unit(db, document_id, unit_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/{document_id}/composed-overview",
    response_model=list[ComposedUnitOverviewItem],
)
def get_composed_overview(document_id: int, db: Session = Depends(get_db)):
    """
    Übersicht der zusammengesetzten Dokument-Einheiten inkl. Volltext (BBox-Inhalt
    in Lesereihenfolge) zur geordneten Analyse.
    """
    try:
        raw = document_service.get_composed_overview(db, document_id)
        return [ComposedUnitOverviewItem(**item) for item in raw]
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


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
    """
    try:
        document_service.delete_document(db, document_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logging.error("Fehler beim Löschen von Dokument %s: %s", document_id, e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Löschen des Dokuments: {e!s}",
        ) from e


@router.post("/{document_id}/create-page-jobs", response_model=dict)
async def create_page_jobs(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Erstelle seitenweise OCR-Jobs für ein bestehendes PDF-Dokument nachträglich
    """
    try:
        return document_service.create_page_jobs(db, document_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except DocumentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logging.error(
            "Fehler beim Erstellen von Seiten/OCR-Jobs für Dokument %s: %s",
            document_id,
            e,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Erstellen der Jobs: {e!s}",
        ) from e


@router.post("/{document_id}/ocr", response_model=DocumentResponse)
async def process_ocr(
    document_id: int,
    language: str = "deu+eng",
    use_correction: bool = True,
    db: Session = Depends(get_db),
):
    """
    Führe OCR auf Dokument aus (DEPRECATED: Verwende /api/ocr/documents/{id}/process)
    """
    from src.rotary_archiv.api.ocr import process_ocr as new_process_ocr

    ocr_results = await new_process_ocr(
        document_id=document_id,
        language=language,
        use_correction=use_correction,
        db=db,
    )

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    db.refresh(document)

    if ocr_results:
        best_result = next(
            (r for r in ocr_results if r.source.value == "combined"), None
        )
        if not best_result:
            best_result = next(
                (r for r in ocr_results if r.source.value == "tesseract"), None
            )
        if best_result:
            document.ocr_text = best_result.text

    return document


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

    classifier = DocumentClassifier()
    classification = classifier.classify_document(document.ocr_text, document.filename)

    document.document_type = classification.get("document_type")
    document.status = DocumentStatus.CLASSIFIED

    db.commit()
    db.refresh(document)

    return document
