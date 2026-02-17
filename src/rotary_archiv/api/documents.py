"""
API Endpoints für Dokumente
"""

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
    DocumentResponse,
    DocumentUnitResponse,
    DocumentUpdate,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    DocumentUnit,
    OCRJob,
    OCRJobStatus,
)
from src.rotary_archiv.utils.file_handler import get_file_size, save_uploaded_file
from src.rotary_archiv.utils.pdf_utils import get_pdf_page_count

# Optional imports für OCR und NLP
try:
    from src.rotary_archiv.ocr.pipeline import OCRPipeline

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRPipeline = None

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

        # Für PDFs: Erstelle virtuelle Seiten und OCR-Jobs
        if (
            db_document.file_type.lower() == "application/pdf"
            or db_document.filename.lower().endswith(".pdf")
        ):
            try:
                # Ermittle Seitenzahl
                from src.rotary_archiv.utils.file_handler import get_file_path

                absolute_file_path = get_file_path(db_document.file_path)
                page_count = get_pdf_page_count(absolute_file_path)

                # Erstelle virtuelle DocumentPage-Objekte
                pages = []
                for page_num in range(1, page_count + 1):
                    db_page = DocumentPage(
                        document_id=db_document.id,
                        page_number=page_num,
                        file_path=None,  # Virtuell, keine Datei-Extraktion
                        file_type="pdf",
                        is_extracted=False,
                    )
                    db.add(db_page)
                    pages.append(db_page)

                db.commit()

                # Refresh für IDs
                for page in pages:
                    db.refresh(page)

                # Erstelle OCR-Jobs für jede Seite
                ocr_jobs = []
                for page in pages:
                    ocr_job = OCRJob(
                        document_id=db_document.id,
                        document_page_id=page.id,
                        status=OCRJobStatus.PENDING,
                        language="deu+eng",
                        use_correction=True,
                    )
                    db.add(ocr_job)
                    ocr_jobs.append(ocr_job)

                db.commit()

                # Refresh für IDs
                for ocr_job in ocr_jobs:
                    db.refresh(ocr_job)
                    # Jobs werden automatisch vom Worker-Prozess abgeholt

            except Exception as e:
                import logging

                logging.warning(
                    f"Fehler beim Erstellen von Seiten/OCR-Jobs für Dokument {db_document.id}: {e}"
                )
                # Fehler nicht kritisch - Dokument wurde bereits erstellt

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


@router.get("/{document_id}/units", response_model=list[DocumentUnitResponse])
def get_document_units(document_id: int, db: Session = Depends(get_db)):
    """
    Hole alle Content-Analyse-Einheiten (document_units) für ein Dokument.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )
    units = (
        db.query(DocumentUnit)
        .filter(DocumentUnit.document_id == document_id)
        .order_by(DocumentUnit.id)
        .all()
    )
    return [DocumentUnitResponse.model_validate(u) for u in units]


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


@router.post("/{document_id}/create-page-jobs", response_model=dict)
async def create_page_jobs(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Erstelle seitenweise OCR-Jobs für ein bestehendes PDF-Dokument nachträglich

    Erstellt virtuelle DocumentPage-Objekte und OCR-Jobs für jede Seite,
    falls diese noch nicht existieren.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Prüfe ob es ein PDF ist
    if (
        document.file_type.lower() != "application/pdf"
        and not document.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien können seitenweise verarbeitet werden",
        )

    try:
        # Ermittle Seitenzahl
        from src.rotary_archiv.utils.file_handler import get_file_path

        absolute_file_path = get_file_path(document.file_path)
        if not absolute_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Datei nicht gefunden: {absolute_file_path}",
            )

        page_count = get_pdf_page_count(absolute_file_path)

        # Prüfe welche Seiten bereits existieren
        existing_pages = (
            db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        )
        existing_page_numbers = {page.page_number for page in existing_pages}

        # Erstelle fehlende virtuelle DocumentPage-Objekte
        new_pages = []
        for page_num in range(1, page_count + 1):
            if page_num not in existing_page_numbers:
                db_page = DocumentPage(
                    document_id=document_id,
                    page_number=page_num,
                    file_path=None,  # Virtuell, keine Datei-Extraktion
                    file_type="pdf",
                    is_extracted=False,
                )
                db.add(db_page)
                new_pages.append(db_page)

        if new_pages:
            db.commit()
            # Refresh für IDs
            for page in new_pages:
                db.refresh(page)

        # Verwende alle Seiten (neu und bestehend)
        all_pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .all()
        )

        # Prüfe welche Jobs bereits existieren
        existing_jobs = (
            db.query(OCRJob)
            .filter(
                OCRJob.document_id == document_id,
                OCRJob.document_page_id.isnot(None),
            )
            .all()
        )
        existing_page_ids = {
            job.document_page_id for job in existing_jobs if job.document_page_id
        }

        # Erstelle OCR-Jobs für Seiten ohne bestehenden Job
        ocr_jobs = []
        for page in all_pages:
            if page.id not in existing_page_ids:
                ocr_job = OCRJob(
                    document_id=document_id,
                    document_page_id=page.id,
                    status=OCRJobStatus.PENDING,
                    language="deu+eng",
                    use_correction=True,
                )
                db.add(ocr_job)
                ocr_jobs.append(ocr_job)

        if ocr_jobs:
            db.commit()
            # Refresh für IDs
            for ocr_job in ocr_jobs:
                db.refresh(ocr_job)
                # Jobs werden automatisch vom Worker-Prozess abgeholt

        return {
            "document_id": document_id,
            "total_pages": page_count,
            "existing_pages": len(existing_pages),
            "new_pages": len(new_pages),
            "existing_jobs": len(existing_jobs),
            "new_jobs": len(ocr_jobs),
            "message": f"Erstellt: {len(new_pages)} neue Seiten, {len(ocr_jobs)} neue OCR-Jobs",
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback

        logging.error(
            f"Fehler beim Erstellen von Seiten/OCR-Jobs für Dokument {document_id}: {e}"
        )
        logging.error(traceback.format_exc())
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

    Dieses Endpoint verwendet das neue OCR-System mit OCRResult-Einträgen.
    Für Rückwärtskompatibilität wird das alte Format beibehalten.
    """
    from src.rotary_archiv.api.ocr import process_ocr as new_process_ocr

    # Verwende neues OCR-System
    ocr_results = await new_process_ocr(
        document_id=document_id,
        language=language,
        use_correction=use_correction,
        db=db,
    )

    # Hole Dokument mit aktualisiertem Status
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    db.refresh(document)

    # Für Rückwärtskompatibilität: Setze ocr_text auf bestes Ergebnis
    if ocr_results:
        # Verwende GPT-kombiniertes Ergebnis falls vorhanden, sonst Tesseract
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

    # Klassifizierung
    classifier = DocumentClassifier()
    classification = classifier.classify_document(document.ocr_text, document.filename)

    # Update Dokument
    document.document_type = classification.get("document_type")
    document.status = DocumentStatus.CLASSIFIED

    db.commit()
    db.refresh(document)

    return document
