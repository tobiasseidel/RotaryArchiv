"""
API Endpoints für OCR-Verarbeitung
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
from src.rotary_archiv.core.models import OCRJob, OCRJobStatus
from src.rotary_archiv.services import ocr_service
from src.rotary_archiv.services.ocr_service import (
    DocumentNotFoundError,
    InvalidActionError,
    InvalidJobStateError,
    JobConflictError,
    JobNotFoundError,
    OCRPipelineUnavailableError,
    OCRResultNotFoundError,
)

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/documents/{document_id}/process", response_model=list[OCRResultResponse])
async def process_ocr(
    document_id: int,
    language: str = "deu+eng",
    use_correction: bool = False,
    db: Session = Depends(get_db),
):
    """
    Startet OCR-Verarbeitung für ein Dokument

    Erstellt OCRResult-Einträge mit Ollama Vision.
    """
    try:
        ocr_results = ocr_service.process_document(
            db, document_id, language=language, use_correction=use_correction
        )
        return [OCRResultResponse.model_validate(r) for r in ocr_results]
    except OCRPipelineUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Fehler: {e!s}",
        ) from e


@router.get("/documents/{document_id}/results", response_model=list[OCRResultResponse])
def get_ocr_results(document_id: int, db: Session = Depends(get_db)):
    """
    Liste aller OCRResult-Einträge für ein Dokument
    """
    try:
        results = ocr_service.get_ocr_results(db, document_id)
        return [OCRResultResponse.model_validate(r) for r in results]
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/documents/{document_id}/results/{result_id}", response_model=OCRResultResponse
)
def get_ocr_result(document_id: int, result_id: int, db: Session = Depends(get_db)):
    """
    Einzelnes OCRResult abrufen
    """
    try:
        ocr_result = ocr_service.get_ocr_result(db, document_id, result_id)
        return OCRResultResponse.model_validate(ocr_result)
    except OCRResultNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


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
    try:
        ocr_job = ocr_service.create_ocr_job(db, document_id, job_data)
        return OCRJobResponse.model_validate(ocr_job)
    except OCRPipelineUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except JobConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get("/documents/{document_id}/jobs", response_model=list[OCRJobResponse])
def get_ocr_jobs(
    document_id: int,
    job_type: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Liste aller OCR-Jobs für ein Dokument

    Args:
        document_id: ID des Dokuments
        job_type: Optionaler Filter nach Job-Typ ("ocr" oder "bbox_review")
    """
    jobs = ocr_service.get_ocr_jobs(db, document_id, job_type=job_type)
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
    try:
        job = ocr_service.prioritize_job(db, job_id)
        return OCRJobResponse.model_validate(job)
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except InvalidJobStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


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
    jobs = ocr_service.list_ocr_jobs(db, status=status, limit=limit)
    return [OCRJobResponse.model_validate(job) for job in jobs]


@router.get("/queue-status", response_model=QueueStatusResponse)
def get_queue_status(
    job_type: str = "all",
    db: Session = Depends(get_db),
):
    """
    Gemeinsames Statuspaket für die Job-Queue (ein Request statt vieler).

    Liefert alle PDF-Dokumente mit Status uploaded/ocr_pending/ocr_done und deren
    OCR-Jobs inkl. page_number. Filter job_type: all | ocr | bbox_review.
    """
    raw = ocr_service.get_queue_status(db, job_type=job_type)

    documents = []
    for doc_data in raw.get("documents", []):
        doc_jobs = [QueueStatusJobItem(**j) for j in doc_data.get("jobs", [])]
        documents.append(
            QueueStatusDocumentItem(
                id=doc_data["id"],
                filename=doc_data["filename"],
                title=doc_data["title"],
                status=doc_data["status"],
                file_type=doc_data["file_type"],
                jobs=doc_jobs,
            )
        )

    return QueueStatusResponse(documents=documents)


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
    try:
        raw = ocr_service.batch_update_jobs(db, request.job_ids, request.action)
    except InvalidActionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    errors = [JobBatchError(**err) for err in raw.get("errors", [])]
    return JobBatchResponse(updated=raw["updated"], errors=errors)
