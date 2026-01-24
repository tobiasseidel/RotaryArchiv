"""
API Endpoints für OCR-Verarbeitung
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from src.rotary_archiv.api.schemas import (
    JobBatchError,
    JobBatchRequest,
    JobBatchResponse,
    OCRJobCreate,
    OCRJobResponse,
    OCRResultResponse,
    QueueStatusDocumentItem,
    QueueStatusJobItem,
    QueueStatusResponse,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentStatus,
    OCRJob,
    OCRJobStatus,
    OCRResult,
)

# Worker-Prozess verarbeitet Jobs automatisch - kein Import mehr nötig

# Optional imports für OCR
try:
    from src.rotary_archiv.ocr.pipeline import OCRPipeline

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRPipeline = None

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/documents/{document_id}/process", response_model=list[OCRResultResponse])
async def process_ocr(
    document_id: int,
    language: str = "deu+eng",  # Wird ignoriert, für Kompatibilität behalten
    use_correction: bool = False,  # Wird ignoriert, für Kompatibilität behalten
    db: Session = Depends(get_db),
):
    """
    Startet OCR-Verarbeitung für ein Dokument

    Erstellt OCRResult-Einträge mit Ollama Vision.
    """
    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR-Pipeline nicht verfügbar. Bitte Dependencies installieren.",
        )

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Update Status
    document.status = DocumentStatus.OCR_PENDING
    db.commit()

    try:
        # OCR Pipeline
        pipeline = OCRPipeline()
        ocr_results = await pipeline.process_document_with_db(
            db=db,
            document_id=document_id,
            file_path=document.file_path,
            language=language,
            use_correction=use_correction,
        )

        # Update Status
        document.status = DocumentStatus.OCR_DONE
        db.commit()

        return [OCRResultResponse.model_validate(r) for r in ocr_results]

    except Exception as e:
        document.status = DocumentStatus.UPLOADED  # Rollback
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Fehler: {e!s}",
        ) from e


@router.get("/documents/{document_id}/results", response_model=list[OCRResultResponse])
def get_ocr_results(document_id: int, db: Session = Depends(get_db)):
    """
    Liste aller OCRResult-Einträge für ein Dokument
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    ocr_results = (
        db.query(OCRResult)
        .filter(OCRResult.document_id == document_id)
        .order_by(OCRResult.created_at.desc())
        .all()
    )

    return [OCRResultResponse.model_validate(r) for r in ocr_results]


@router.get(
    "/documents/{document_id}/results/{result_id}", response_model=OCRResultResponse
)
def get_ocr_result(document_id: int, result_id: int, db: Session = Depends(get_db)):
    """
    Einzelnes OCRResult abrufen
    """
    ocr_result = (
        db.query(OCRResult)
        .filter(OCRResult.id == result_id, OCRResult.document_id == document_id)
        .first()
    )

    if not ocr_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCRResult nicht gefunden"
        )

    return OCRResultResponse.model_validate(ocr_result)


# Job-Management Endpoints
@router.post("/documents/{document_id}/jobs", response_model=OCRJobResponse)
def create_ocr_job(
    document_id: int,
    job_data: OCRJobCreate,
    db: Session = Depends(get_db),
):
    """
    Erstellt einen neuen OCR-Job (Status: PENDING)

    Der Job wird automatisch vom separaten Worker-Prozess verarbeitet.
    Starte den Worker mit: python -m src.rotary_archiv.ocr.worker

    Returns:
        OCRJobResponse mit Job-ID und Status
    """
    if not OCR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR-Pipeline nicht verfügbar. Bitte Dependencies installieren.",
        )

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Prüfe ob bereits ein aktiver Job existiert (für dieses Dokument, nicht seitenweise)
    existing_job = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_id == document_id,
            OCRJob.document_page_id.is_(None),  # Nur dokumentweite Jobs
            OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
        )
        .first()
    )
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bereits ein aktiver Job vorhanden (ID: {existing_job.id})",
        )

    # Erstelle neuen Job (Status: PENDING - wird vom Worker verarbeitet)
    ocr_job = OCRJob(
        document_id=document_id,
        status=OCRJobStatus.PENDING,
        language=job_data.language,
        use_correction=job_data.use_correction,
    )
    db.add(ocr_job)
    db.commit()
    db.refresh(ocr_job)

    # Job wird automatisch vom Worker-Prozess abgeholt
    # Keine BackgroundTasks mehr - saubere Trennung von API und Worker

    return OCRJobResponse.model_validate(ocr_job)


@router.get("/documents/{document_id}/jobs", response_model=list[OCRJobResponse])
def get_ocr_jobs(
    document_id: int,
    job_type: str | None = None,  # Filter nach job_type: "ocr" oder "bbox_review"
    db: Session = Depends(get_db),
):
    """
    Liste aller OCR-Jobs für ein Dokument

    Args:
        document_id: ID des Dokuments
        job_type: Optionaler Filter nach Job-Typ ("ocr" oder "bbox_review")
    """
    query = db.query(OCRJob).filter(OCRJob.document_id == document_id)

    # Filter nach job_type falls angegeben
    if job_type:
        query = query.filter(OCRJob.job_type == job_type)

    jobs = query.order_by(OCRJob.created_at.desc()).all()
    return [OCRJobResponse.model_validate(job) for job in jobs]


@router.post("/jobs/{job_id}/prioritize")
def prioritize_job(job_id: int, db: Session = Depends(get_db)):
    """
    Setze einen Job als nächstes auszuführen (höchste Priorität)

    Args:
        job_id: ID des Jobs

    Returns:
        OCRJobResponse mit aktualisierter Priorität
    """
    job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job nicht gefunden"
        )

    if job.status != OCRJobStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PENDING-Jobs können priorisiert werden",
        )

    # Finde die niedrigste aktuelle Priorität (höchste Priorität = niedrigste Zahl)
    min_priority = (
        db.query(func.min(OCRJob.priority))
        .filter(OCRJob.status == OCRJobStatus.PENDING)
        .scalar()
    ) or 0

    # Setze Priorität auf niedrigste - 1 (höchste Priorität)
    job.priority = min_priority - 1
    db.commit()
    db.refresh(job)

    return OCRJobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=OCRJobResponse)
def get_ocr_job(job_id: int, db: Session = Depends(get_db)):
    """
    Hole einen einzelnen OCR-Job
    """
    job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR-Job nicht gefunden"
        )
    return OCRJobResponse.model_validate(job)


@router.get("/jobs", response_model=list[OCRJobResponse])
def list_ocr_jobs(
    status: OCRJobStatus | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Liste aller OCR-Jobs (optional gefiltert nach Status)
    """
    query = db.query(OCRJob)
    if status:
        query = query.filter(OCRJob.status == status)
    jobs = query.order_by(OCRJob.created_at.desc()).limit(limit).all()
    return [OCRJobResponse.model_validate(job) for job in jobs]


@router.get("/queue-status", response_model=QueueStatusResponse)
def get_queue_status(
    job_type: str = "all",  # "all" | "ocr" | "bbox_review"
    db: Session = Depends(get_db),
):
    """
    Gemeinsames Statuspaket für die Job-Queue (ein Request statt vieler).

    Liefert alle PDF-Dokumente mit Status uploaded/ocr_pending/ocr_done und deren
    OCR-Jobs inkl. page_number. Filter job_type: all | ocr | bbox_review.
    """
    # PDF-Dokumente mit relevantem Status
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
            or_(
                Document.file_type.ilike("%pdf%"),
                Document.filename.ilike("%.pdf"),
            ),
        )
        .all()
    )
    doc_ids = [d.id for d in docs]
    if not doc_ids:
        return QueueStatusResponse(documents=[])

    # Jobs für diese Dokumente, mit DocumentPage für page_number
    # ARCHIVED-Jobs werden nicht in der Queue angezeigt
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
        jobs_query = jobs_query.filter(OCRJob.job_type == job_type)

    jobs = jobs_query.all()
    doc_ids_with_jobs = {j.document_id for j in jobs}

    # Nur Dokumente mit mindestens einem Job
    docs_with_jobs = [d for d in docs if d.id in doc_ids_with_jobs]

    def to_job_item(job: OCRJob) -> QueueStatusJobItem:
        page_number = job.document_page.page_number if job.document_page else None
        return QueueStatusJobItem(
            id=job.id,
            document_id=job.document_id,
            document_page_id=job.document_page_id,
            page_number=page_number,
            job_type=job.job_type or "ocr",
            status=job.status,
            language=job.language,
            use_correction=job.use_correction,
            priority=job.priority or 0,
            progress=job.progress or 0.0,
            current_step=job.current_step,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )

    result = []
    for doc in docs_with_jobs:
        doc_jobs = [to_job_item(j) for j in jobs if j.document_id == doc.id]
        result.append(
            QueueStatusDocumentItem(
                id=doc.id,
                filename=doc.filename,
                title=doc.title,
                status=doc.status,
                file_type=doc.file_type,
                jobs=doc_jobs,
            )
        )

    return QueueStatusResponse(documents=result)


@router.post("/jobs/batch", response_model=JobBatchResponse)
def batch_update_jobs(
    request: JobBatchRequest,
    db: Session = Depends(get_db),
):
    """
    Batch-Operationen auf mehreren Jobs: Abbrechen, Neustart, Pausieren, Fortsetzen, Archivieren.

    Args:
        request: JobBatchRequest mit job_ids und action

    Returns:
        JobBatchResponse mit Anzahl aktualisierter Jobs und Fehlerliste
    """
    updated_count = 0
    errors: list[JobBatchError] = []

    # Hole alle Jobs
    jobs = db.query(OCRJob).filter(OCRJob.id.in_(request.job_ids)).all()
    job_dict = {job.id: job for job in jobs}

    # Validiere Aktion
    valid_actions = {"cancel", "restart", "pause", "resume", "archive"}
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültige Aktion: {request.action}. Erlaubt: {', '.join(valid_actions)}",
        )

    # Verarbeite jeden Job
    for job_id in request.job_ids:
        job = job_dict.get(job_id)
        if not job:
            errors.append(JobBatchError(job_id=job_id, reason="Job nicht gefunden"))
            continue

        current_status = job.status

        # Prüfe gültige Übergänge und führe Aktion aus
        try:
            if request.action == "cancel":
                # cancel: PENDING, RUNNING, PAUSED -> CANCELLED
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
                        JobBatchError(
                            job_id=job_id,
                            reason=f"Job hat Status {current_status.value}, kann nicht abgebrochen werden",
                        )
                    )

            elif request.action == "restart":
                # restart: FAILED, CANCELLED -> PENDING (reset)
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
                        JobBatchError(
                            job_id=job_id,
                            reason=f"Job hat Status {current_status.value}, kann nicht neu gestartet werden",
                        )
                    )

            elif request.action == "pause":
                # pause: PENDING -> PAUSED
                if current_status == OCRJobStatus.PENDING:
                    job.status = OCRJobStatus.PAUSED
                    updated_count += 1
                else:
                    errors.append(
                        JobBatchError(
                            job_id=job_id,
                            reason=f"Job hat Status {current_status.value}, kann nicht pausiert werden (nur PENDING)",
                        )
                    )

            elif request.action == "resume":
                # resume: PAUSED -> PENDING
                if current_status == OCRJobStatus.PAUSED:
                    job.status = OCRJobStatus.PENDING
                    updated_count += 1
                else:
                    errors.append(
                        JobBatchError(
                            job_id=job_id,
                            reason=f"Job hat Status {current_status.value}, kann nicht fortgesetzt werden (nur PAUSED)",
                        )
                    )

            elif request.action == "archive":
                # archive: COMPLETED, FAILED, CANCELLED -> ARCHIVED
                if current_status in [
                    OCRJobStatus.COMPLETED,
                    OCRJobStatus.FAILED,
                    OCRJobStatus.CANCELLED,
                ]:
                    job.status = OCRJobStatus.ARCHIVED
                    updated_count += 1
                else:
                    errors.append(
                        JobBatchError(
                            job_id=job_id,
                            reason=f"Job hat Status {current_status.value}, kann nicht archiviert werden",
                        )
                    )

        except Exception as e:
            errors.append(
                JobBatchError(job_id=job_id, reason=f"Fehler bei Verarbeitung: {e!s}")
            )

    # Commit alle Änderungen
    if updated_count > 0:
        db.commit()

    return JobBatchResponse(updated=updated_count, errors=errors)
