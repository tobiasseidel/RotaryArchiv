"""OCR Service - Business-Logic für OCR-Verarbeitung, Job-Management und Queue-Status."""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.rotary_archiv.core.models import (
    Document,
    DocumentStatus,
    OCRJob,
    OCRJobStatus,
    OCRResult,
)

# Optional OCR Pipeline
try:
    from src.rotary_archiv.ocr.pipeline import OCRPipeline

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRPipeline = None  # type: ignore[assignment,misc]


# ─── Exceptions ──────────────────────────────────────────────────────────────


class OCRServiceError(Exception):
    """Basis-Exception für OCR-Service."""


class DocumentNotFoundError(OCRServiceError):
    def __init__(self, document_id: int):
        self.document_id = document_id
        super().__init__(f"Dokument {document_id} nicht gefunden")


class OCRResultNotFoundError(OCRServiceError):
    def __init__(self, document_id: int, result_id: int):
        self.document_id = document_id
        self.result_id = result_id
        super().__init__(
            f"OCRResult {result_id} für Dokument {document_id} nicht gefunden"
        )


class JobNotFoundError(OCRServiceError):
    def __init__(self, job_id: int):
        self.job_id = job_id
        super().__init__(f"Job {job_id} nicht gefunden")


class JobConflictError(OCRServiceError):
    def __init__(self, existing_job_id: int):
        self.existing_job_id = existing_job_id
        super().__init__(f"Bereits ein aktiver Job vorhanden (ID: {existing_job_id})")


class InvalidJobStateError(OCRServiceError):
    def __init__(self, current_status: str, action: str):
        self.current_status = current_status
        self.action = action
        super().__init__(
            f"Job hat Status '{current_status}', kann nicht '{action}' werden"
        )


class InvalidActionError(OCRServiceError):
    def __init__(self, action: str):
        self.action = action
        super().__init__(f"Ungültige Aktion: {action}")


class OCRPipelineUnavailableError(OCRServiceError):
    def __init__(self):
        super().__init__(
            "OCR-Pipeline nicht verfügbar. Bitte Dependencies installieren."
        )


# ─── Service Functions ───────────────────────────────────────────────────────


def _require_document(db: Session, document_id: int) -> Document:
    """Holt ein Dokument oder wirft DocumentNotFoundError."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise DocumentNotFoundError(document_id)
    return document


def process_document(
    db: Session,
    document_id: int,
    language: str = "deu+eng",
    use_correction: bool = False,
) -> list[OCRResult]:
    """Startet OCR-Verarbeitung für ein Dokument über die OCR-Pipeline."""
    if not OCR_AVAILABLE:
        raise OCRPipelineUnavailableError()

    document = _require_document(db, document_id)
    document.status = DocumentStatus.OCR_PENDING
    db.commit()

    try:
        pipeline = OCRPipeline()
        ocr_results = pipeline.process_document_with_db(
            db=db,
            document_id=document_id,
            file_path=document.file_path,
            language=language,
            use_correction=use_correction,
        )
        document.status = DocumentStatus.OCR_DONE
        db.commit()
        return list(ocr_results)
    except Exception:
        document.status = DocumentStatus.UPLOADED
        db.commit()
        raise


def get_ocr_results(db: Session, document_id: int) -> list[OCRResult]:
    """Hole alle OCR-Ergebnisse für ein Dokument."""
    _require_document(db, document_id)
    return (
        db.query(OCRResult)
        .filter(OCRResult.document_id == document_id)
        .order_by(OCRResult.created_at.desc())
        .all()
    )


def get_ocr_result(db: Session, document_id: int, result_id: int) -> OCRResult:
    """Hole ein einzelnes OCR-Ergebnis."""
    ocr_result = (
        db.query(OCRResult)
        .filter(OCRResult.id == result_id, OCRResult.document_id == document_id)
        .first()
    )
    if not ocr_result:
        raise OCRResultNotFoundError(document_id, result_id)
    return ocr_result


def create_ocr_job(db: Session, document_id: int, job_data) -> OCRJob:
    """Erstellt einen neuen OCR-Job mit Status PENDING."""
    if not OCR_AVAILABLE:
        raise OCRPipelineUnavailableError()

    _require_document(db, document_id)

    existing_job = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_id == document_id,
            OCRJob.document_page_id.is_(None),
            OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
        )
        .first()
    )
    if existing_job:
        raise JobConflictError(existing_job.id)

    job_type = (getattr(job_data, "job_type", None) or "ocr").strip() or "ocr"
    document_page_id = None
    if job_type in ("content_analysis", "boundary_analysis", "unit_content_analysis"):
        document_page_id = None

    ocr_job = OCRJob(
        document_id=document_id,
        document_page_id=document_page_id,
        job_type=job_type,
        status=OCRJobStatus.PENDING,
        language=getattr(job_data, "language", "deu+eng") or "deu+eng",
        use_correction=getattr(job_data, "use_correction", False),
    )
    db.add(ocr_job)
    db.commit()
    db.refresh(ocr_job)
    return ocr_job


def get_ocr_jobs(
    db: Session, document_id: int, job_type: str | None = None
) -> list[OCRJob]:
    """Liste aller OCR-Jobs für ein Dokument, optional gefiltert nach Typ."""
    query = db.query(OCRJob).filter(OCRJob.document_id == document_id)
    if job_type:
        query = query.filter(OCRJob.job_type == job_type)
    return query.order_by(OCRJob.created_at.desc()).all()


def prioritize_job(db: Session, job_id: int) -> OCRJob:
    """Setzt einen PENDING-Job auf höchste Priorität (min - 1)."""
    job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
    if not job:
        raise JobNotFoundError(job_id)

    if job.status != OCRJobStatus.PENDING:
        raise InvalidJobStateError(job.status.value, "prioritize")

    min_priority = (
        db.query(func.min(OCRJob.priority))
        .filter(OCRJob.status == OCRJobStatus.PENDING)
        .scalar()
    ) or 0

    job.priority = min_priority - 1
    db.commit()
    db.refresh(job)
    return job


def list_ocr_jobs(
    db: Session,
    status: OCRJobStatus | None = None,
    limit: int = 50,
) -> list[OCRJob]:
    """Liste aller OCR-Jobs, optional gefiltert nach Status."""
    query = db.query(OCRJob)
    if status:
        query = query.filter(OCRJob.status == status)
    return query.order_by(OCRJob.created_at.desc()).limit(limit).all()


def batch_update_jobs(db: Session, job_ids: list[int], action: str) -> dict:
    """Batch-Operationen: cancel, restart, pause, resume, archive, delete."""
    valid_actions = {"cancel", "restart", "pause", "resume", "archive", "delete"}
    if action not in valid_actions:
        raise InvalidActionError(action)

    updated_count = 0
    errors: list[dict] = []

    jobs = db.query(OCRJob).filter(OCRJob.id.in_(job_ids)).all()
    job_dict = {job.id: job for job in jobs}

    for jid in job_ids:
        job = job_dict.get(jid)
        if not job:
            errors.append({"job_id": jid, "reason": "Job nicht gefunden"})
            continue

        current_status = job.status

        try:
            if action == "cancel":
                if current_status in [
                    OCRJobStatus.PENDING,
                    OCRJobStatus.RUNNING,
                    OCRJobStatus.PAUSED,
                ]:
                    job.status = OCRJobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    updated_count += 1
                else:
                    errors.append(
                        {
                            "job_id": jid,
                            "reason": f"Job hat Status {current_status.value}, kann nicht abgebrochen werden",
                        }
                    )
            elif action == "restart":
                if current_status in [OCRJobStatus.FAILED, OCRJobStatus.CANCELLED]:
                    job.status = OCRJobStatus.PENDING
                    job.progress = 0.0
                    job.error_message = None
                    job.started_at = None
                    job.completed_at = None
                    job.current_step = None
                    updated_count += 1
                else:
                    errors.append(
                        {
                            "job_id": jid,
                            "reason": f"Job hat Status {current_status.value}, kann nicht neu gestartet werden",
                        }
                    )
            elif action == "pause":
                if current_status == OCRJobStatus.PENDING:
                    job.status = OCRJobStatus.PAUSED
                    updated_count += 1
                else:
                    errors.append(
                        {
                            "job_id": jid,
                            "reason": f"Job hat Status {current_status.value}, kann nicht pausiert werden (nur PENDING)",
                        }
                    )
            elif action == "resume":
                if current_status == OCRJobStatus.PAUSED:
                    job.status = OCRJobStatus.PENDING
                    updated_count += 1
                else:
                    errors.append(
                        {
                            "job_id": jid,
                            "reason": f"Job hat Status {current_status.value}, kann nicht fortgesetzt werden (nur PAUSED)",
                        }
                    )
            elif action == "archive":
                if current_status in [
                    OCRJobStatus.COMPLETED,
                    OCRJobStatus.FAILED,
                    OCRJobStatus.CANCELLED,
                ]:
                    job.status = OCRJobStatus.ARCHIVED
                    updated_count += 1
                else:
                    errors.append(
                        {
                            "job_id": jid,
                            "reason": f"Job hat Status {current_status.value}, kann nicht archiviert werden",
                        }
                    )
            elif action == "delete":
                if current_status == OCRJobStatus.RUNNING:
                    errors.append(
                        {
                            "job_id": jid,
                            "reason": "Laufenden Job kann man nicht löschen (erst pausieren/abbrechen)",
                        }
                    )
                else:
                    db.delete(job)
                    updated_count += 1
                    del job_dict[jid]
        except Exception as e:
            errors.append({"job_id": jid, "reason": f"Fehler bei Verarbeitung: {e!s}"})

    if updated_count > 0:
        db.commit()

    return {"updated": updated_count, "errors": errors}


def get_queue_status(db: Session, job_type: str = "all") -> dict:
    """Gemeinsames Statuspaket für die Job-Queue."""
    docs = (
        db.query(Document)
        .filter(
            Document.status.in_(
                [
                    DocumentStatus.UPLOADED,
                    DocumentStatus.OCR_PENDING,
                    DocumentStatus.OCR_DONE,
                ]
            ),
            (Document.file_type.ilike("%pdf%")) | (Document.filename.ilike("%.pdf")),
        )
        .all()
    )
    doc_ids = [d.id for d in docs]
    if not doc_ids:
        return {"documents": []}

    jobs_query = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_id.in_(doc_ids),
            OCRJob.status != OCRJobStatus.ARCHIVED,
        )
        .options(joinedload(OCRJob.document_page))
        .order_by(OCRJob.created_at.desc())
    )
    if job_type and job_type != "all":
        if job_type == "review":
            jobs_query = jobs_query.filter(
                OCRJob.job_type.in_(["bbox_review", "llm_sight"])
            )
        else:
            jobs_query = jobs_query.filter(OCRJob.job_type == job_type)

    jobs = jobs_query.all()
    doc_ids_with_jobs = {j.document_id for j in jobs}
    docs_with_jobs = [d for d in docs if d.id in doc_ids_with_jobs]

    result = []
    for doc in docs_with_jobs:
        doc_jobs = []
        for j in jobs:
            if j.document_id == doc.id:
                page_number = j.document_page.page_number if j.document_page else None
                doc_jobs.append(
                    {
                        "id": j.id,
                        "document_id": j.document_id,
                        "document_page_id": j.document_page_id,
                        "page_number": page_number,
                        "job_type": j.job_type or "ocr",
                        "status": j.status,
                        "language": j.language,
                        "use_correction": j.use_correction,
                        "priority": j.priority or 0,
                        "progress": j.progress or 0.0,
                        "current_step": j.current_step,
                        "error_message": j.error_message,
                        "created_at": j.created_at,
                        "started_at": j.started_at,
                        "completed_at": j.completed_at,
                    }
                )
        result.append(
            {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title,
                "status": doc.status,
                "file_type": doc.file_type,
                "jobs": doc_jobs,
            }
        )

    return {"documents": result}
