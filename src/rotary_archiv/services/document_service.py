"""Document Service - Business-Logic für Dokument-Management."""

import logging

from sqlalchemy.orm import Session

from src.rotary_archiv.core.models import (
    Document,
    DocumentPage,
    DocumentStatus,
    DocumentUnit,
    OCRJob,
    OCRJobStatus,
)
from src.rotary_archiv.ocr.job_processor import get_unit_text_in_reading_order
from src.rotary_archiv.utils.file_handler import (
    delete_file,
    get_file_size,
    save_uploaded_file,
)
from src.rotary_archiv.utils.pdf_utils import (
    create_pdf_native_ocr_result_for_page,
    get_pdf_page_count,
)

# ─── Exceptions ──────────────────────────────────────────────────────────────


class DocumentServiceError(Exception):
    """Basis-Exception für Document-Service."""


class DocumentNotFoundError(DocumentServiceError):
    def __init__(self, document_id: int):
        self.document_id = document_id
        super().__init__(f"Dokument {document_id} nicht gefunden")


class InvalidPageError(DocumentServiceError):
    def __init__(self, document_id: int, page_id: int):
        self.document_id = document_id
        self.page_id = page_id
        super().__init__(f"Seite {page_id} gehört nicht zum Dokument {document_id}")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _require_document(db: Session, document_id: int) -> Document:
    """Holt ein Dokument oder wirft DocumentNotFoundError."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise DocumentNotFoundError(document_id)
    return document


def _document_page_ids_for_document(db: Session, document_id: int) -> set[int]:
    """Set aller DocumentPage-IDs die zu diesem Dokument gehören."""
    rows = (
        db.query(DocumentPage.id).filter(DocumentPage.document_id == document_id).all()
    )
    return {r[0] for r in rows}


# ─── Service Functions ───────────────────────────────────────────────────────


def create_document(
    db: Session,
    file_content: bytes,
    filename: str,
    content_type: str,
) -> Document:
    """Lade neues Dokument hoch. Für PDFs: erstelle virtuelle Pages + OCR-Jobs."""
    if not filename:
        raise DocumentServiceError("Kein Dateiname angegeben")
    if len(file_content) == 0:
        raise DocumentServiceError("Datei ist leer")

    file_path = save_uploaded_file(file_content, filename)
    file_size = get_file_size(file_path)

    db_document = Document(
        filename=filename,
        file_path=file_path,
        file_type=content_type or "application/octet-stream",
        file_size=file_size,
        status=DocumentStatus.UPLOADED,
        is_composite=0,
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
            from src.rotary_archiv.utils.file_handler import get_file_path

            absolute_file_path = get_file_path(db_document.file_path)
            page_count = get_pdf_page_count(absolute_file_path)

            pages = []
            for page_num in range(1, page_count + 1):
                db_page = DocumentPage(
                    document_id=db_document.id,
                    page_number=page_num,
                    file_path=None,
                    file_type="pdf",
                    is_extracted=False,
                )
                db.add(db_page)
                pages.append(db_page)

            db.commit()
            for page in pages:
                db.refresh(page)

            for page in pages:
                try:
                    create_pdf_native_ocr_result_for_page(
                        db,
                        db_document.id,
                        page.id,
                        absolute_file_path,
                        page.page_number,
                    )
                except Exception as e:
                    logging.warning(
                        "PDF-Native-Text für Seite %s (Doc %s) übersprungen: %s",
                        page.page_number,
                        db_document.id,
                        e,
                    )

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
            for ocr_job in ocr_jobs:
                db.refresh(ocr_job)

        except Exception as e:
            logging.warning(
                "Fehler beim Erstellen von Seiten/OCR-Jobs für Dokument %s: %s",
                db_document.id,
                e,
            )

    return db_document


def list_documents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status_filter: DocumentStatus | None = None,
) -> list[Document]:
    """Liste alle Dokumente mit optionalem Status-Filter."""
    query = db.query(Document)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    return query.offset(skip).limit(limit).all()


def list_documents_summary(
    db: Session,
    skip: int = 0,
    limit: int = 500,
    status_filter: DocumentStatus | None = None,
) -> list[dict]:
    """Leichte Liste (id, filename, title, status)."""
    query = db.query(Document)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    rows = query.offset(skip).limit(limit).all()
    return [
        {"id": d.id, "filename": d.filename, "title": d.title, "status": d.status}
        for d in rows
    ]


def get_document(db: Session, document_id: int) -> Document:
    """Hole einzelnes Dokument."""
    return _require_document(db, document_id)


def get_document_units(db: Session, document_id: int) -> list[DocumentUnit]:
    """Hole alle Content-Analyse-Einheiten für ein Dokument."""
    _require_document(db, document_id)
    return (
        db.query(DocumentUnit)
        .filter(DocumentUnit.document_id == document_id)
        .order_by(DocumentUnit.id)
        .all()
    )


def get_unassigned_pages(db: Session, document_id: int) -> list[dict]:
    """Seiten des Dokuments, die noch keiner DocumentUnit zugeordnet sind."""
    _require_document(db, document_id)
    all_pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )
    units = db.query(DocumentUnit).filter(DocumentUnit.document_id == document_id).all()
    assigned_ids: set[int] = set()
    for u in units:
        for pid in u.page_ids or []:
            assigned_ids.add(pid)
    unassigned = [p for p in all_pages if p.id not in assigned_ids]
    result = []
    for p in unassigned:
        full_text = get_unit_text_in_reading_order(db, [p.id], page_separator="\n\n")
        result.append(
            {
                "page_id": p.id,
                "page_number": p.page_number,
                "full_text": full_text,
            }
        )
    return result


def create_document_unit(db: Session, document_id: int, data) -> DocumentUnit:
    """Einheit manuell anlegen (Seiten auswählen)."""
    _require_document(db, document_id)
    allowed_ids = _document_page_ids_for_document(db, document_id)
    for pid in data.page_ids:
        if pid not in allowed_ids:
            raise InvalidPageError(document_id, pid)

    unit = DocumentUnit(
        document_id=document_id,
        page_ids=data.page_ids,
        belongs_with_next=getattr(data, "belongs_with_next", False),
        is_public=getattr(data, "is_public", False),
        document_type=getattr(data, "document_type", None),
        title=getattr(data, "title", None),
        date=getattr(data, "date", None),
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_document_unit(
    db: Session, document_id: int, unit_id: int, data
) -> DocumentUnit:
    """Einheit bearbeiten (Seiten/Inhalt)."""
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.id == unit_id,
            DocumentUnit.document_id == document_id,
        )
        .first()
    )
    if not unit:
        raise DocumentNotFoundError(document_id)

    update_data = data.model_dump(exclude_unset=True)
    if "page_ids" in update_data:
        allowed_ids = _document_page_ids_for_document(db, document_id)
        for pid in update_data["page_ids"]:
            if pid not in allowed_ids:
                raise InvalidPageError(document_id, pid)

    for field, value in update_data.items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


def delete_document_unit(db: Session, document_id: int, unit_id: int) -> None:
    """Einheit löschen."""
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.id == unit_id,
            DocumentUnit.document_id == document_id,
        )
        .first()
    )
    if not unit:
        raise DocumentNotFoundError(document_id)
    db.delete(unit)
    db.commit()


def get_composed_overview(db: Session, document_id: int) -> list[dict]:
    """Übersicht der zusammengesetzten Dokument-Einheiten inkl. Volltext."""
    _require_document(db, document_id)
    units = (
        db.query(DocumentUnit)
        .filter(DocumentUnit.document_id == document_id)
        .order_by(DocumentUnit.id)
        .all()
    )
    result = []
    for u in units:
        page_numbers = []
        for pid in u.page_ids:
            page = db.query(DocumentPage).filter(DocumentPage.id == pid).first()
            page_numbers.append(page.page_number if page else 0)
        full_text = get_unit_text_in_reading_order(
            db, u.page_ids, page_separator="\n\n"
        )
        result.append(
            {
                "id": u.id,
                "document_id": u.document_id,
                "page_ids": u.page_ids,
                "page_numbers": page_numbers,
                "full_text": full_text,
                "belongs_with_next": u.belongs_with_next,
                "is_public": u.is_public,
                "document_type": u.document_type,
                "title": u.title,
                "date": u.date,
                "summary": u.summary,
                "persons": u.persons or [],
                "topic": u.topic,
                "place": u.place,
                "event_date": u.event_date,
                "extracted_phrases": u.extracted_phrases or [],
                "extracted_names": u.extracted_names or [],
                "created_at": u.created_at,
                "updated_at": u.updated_at,
            }
        )
    return result


def delete_document(db: Session, document_id: int) -> None:
    """Lösche Dokument und alle zugehörigen Daten (Pages, Files, Child-Docs)."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise DocumentNotFoundError(document_id)

    try:
        pages = (
            db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        )
        for page in pages:
            try:
                delete_file(page.file_path)
            except Exception as e:
                logging.warning(
                    "Konnte Seiten-Datei nicht löschen %s: %s", page.file_path, e
                )

        if document.is_composite:
            child_docs = (
                db.query(Document)
                .filter(Document.parent_document_id == document_id)
                .all()
            )
            for child_doc in child_docs:
                try:
                    delete_file(child_doc.file_path)
                except Exception as e:
                    logging.warning(
                        "Konnte Child-Dokument-Datei nicht löschen %s: %s",
                        child_doc.file_path,
                        e,
                    )

        try:
            delete_file(document.file_path)
        except Exception as e:
            logging.warning(
                "Konnte Hauptdatei nicht löschen %s: %s", document.file_path, e
            )

        db.delete(document)
        db.commit()
    except Exception as e:
        logging.error("Fehler beim Löschen von Dokument %s: %s", document_id, e)
        db.rollback()
        raise


def create_page_jobs(db: Session, document_id: int) -> dict:
    """Erstelle seitenweise OCR-Jobs für ein bestehendes PDF-Dokument nachträglich."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise DocumentNotFoundError(document_id)

    if (
        document.file_type.lower() != "application/pdf"
        and not document.filename.lower().endswith(".pdf")
    ):
        raise DocumentServiceError(
            "Nur PDF-Dateien können seitenweise verarbeitet werden"
        )

    try:
        from src.rotary_archiv.utils.file_handler import get_file_path

        absolute_file_path = get_file_path(document.file_path)
        if not absolute_file_path.exists():
            raise DocumentNotFoundError(document_id)

        page_count = get_pdf_page_count(absolute_file_path)

        existing_pages = (
            db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        )
        existing_page_numbers = {page.page_number for page in existing_pages}

        new_pages = []
        for page_num in range(1, page_count + 1):
            if page_num not in existing_page_numbers:
                db_page = DocumentPage(
                    document_id=document_id,
                    page_number=page_num,
                    file_path=None,
                    file_type="pdf",
                    is_extracted=False,
                )
                db.add(db_page)
                new_pages.append(db_page)

        if new_pages:
            db.commit()
            for page in new_pages:
                db.refresh(page)

        all_pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .all()
        )

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
            for ocr_job in ocr_jobs:
                db.refresh(ocr_job)

        return {
            "document_id": document_id,
            "total_pages": page_count,
            "existing_pages": len(existing_pages),
            "new_pages": len(new_pages),
            "existing_jobs": len(existing_jobs),
            "new_jobs": len(ocr_jobs),
            "message": f"Erstellt: {len(new_pages)} neue Seiten, {len(ocr_jobs)} neue OCR-Jobs",
        }

    except DocumentNotFoundError:
        raise
    except Exception as e:
        logging.error(
            "Fehler beim Erstellen von Seiten/OCR-Jobs für Dokument %s: %s",
            document_id,
            e,
        )
        db.rollback()
        raise DocumentServiceError(f"Fehler beim Erstellen der Jobs: {e!s}") from e
