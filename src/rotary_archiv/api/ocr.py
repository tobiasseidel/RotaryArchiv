"""
API Endpoints für OCR-Verarbeitung und Review
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import (
    OCRComparisonResponse,
    OCRJobCreate,
    OCRJobResponse,
    OCRResultResponse,
    OCRReviewCreate,
    OCRReviewResponse,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    Document,
    DocumentStatus,
    OCRJob,
    OCRJobStatus,
    OCRResult,
    OCRReview,
    OCRReviewStatus,
)
from src.rotary_archiv.ocr.job_processor import process_ocr_job

# Optional imports für OCR
try:
    from src.rotary_archiv.ocr.comparison import (
        check_auto_review,
        compare_ocr_results,
        suggest_best_result,
    )
    from src.rotary_archiv.ocr.pipeline import OCRPipeline

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRPipeline = None
    check_auto_review = None
    compare_ocr_results = None
    suggest_best_result = None

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/documents/{document_id}/process", response_model=list[OCRResultResponse])
async def process_ocr(
    document_id: int,
    language: str = "deu+eng",
    use_correction: bool = True,
    db: Session = Depends(get_db),
):
    """
    Startet OCR-Verarbeitung für ein Dokument

    Erstellt OCRResult-Einträge für Tesseract, Ollama Vision und optional GPT-Korrektur.
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


@router.post("/documents/{document_id}/review", response_model=OCRReviewResponse)
def create_review(
    document_id: int,
    review_data: OCRReviewCreate,
    db: Session = Depends(get_db),
):
    """
    Erstellt Review für OCR-Ergebnisse

    User wählt ein OCRResult oder gibt manuell Text ein.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Prüfe ob OCRResult existiert (falls angegeben)
    reviewed_ocr_result = None
    if review_data.reviewed_ocr_result_id:
        reviewed_ocr_result = (
            db.query(OCRResult)
            .filter(
                OCRResult.id == review_data.reviewed_ocr_result_id,
                OCRResult.document_id == document_id,
            )
            .first()
        )
        if not reviewed_ocr_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCRResult nicht gefunden",
            )

    # Bestimme finalen Text
    if review_data.final_text:
        final_text = review_data.final_text
    elif reviewed_ocr_result:
        final_text = reviewed_ocr_result.text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entweder final_text oder reviewed_ocr_result_id muss angegeben werden",
        )

    # Hole vorheriges Review für review_round
    previous_review = (
        db.query(OCRReview)
        .filter(OCRReview.document_id == document_id)
        .order_by(OCRReview.review_round.desc())
        .first()
    )
    review_round = (previous_review.review_round + 1) if previous_review else 1

    # Erstelle Review
    ocr_review = OCRReview(
        document_id=document_id,
        status=OCRReviewStatus.APPROVED,  # Standard: approved, kann später geändert werden
        reviewed_ocr_result_id=review_data.reviewed_ocr_result_id,
        final_text=final_text,
        reviewer_name=review_data.reviewer_name,
        review_notes=review_data.review_notes,
        review_round=review_round,
        previous_review_id=previous_review.id if previous_review else None,
    )

    db.add(ocr_review)
    db.commit()
    db.refresh(ocr_review)

    # Update Document
    document.ocr_text_final = final_text
    document.ocr_review_id = ocr_review.id
    document.status = DocumentStatus.REVIEWED
    db.commit()
    db.refresh(document)

    return OCRReviewResponse.model_validate(ocr_review)


@router.get("/documents/{document_id}/review", response_model=OCRReviewResponse | None)
def get_review(document_id: int, db: Session = Depends(get_db)):
    """
    Aktuelles Review für ein Dokument abrufen
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Hole aktuelles Review (höchste review_round)
    ocr_review = (
        db.query(OCRReview)
        .filter(OCRReview.document_id == document_id)
        .order_by(OCRReview.review_round.desc())
        .first()
    )

    if not ocr_review:
        return None

    return OCRReviewResponse.model_validate(ocr_review)


@router.post("/documents/{document_id}/compare", response_model=OCRComparisonResponse)
def compare_ocr(
    document_id: int,
    result_ids: list[int] | None = None,
    db: Session = Depends(get_db),
):
    """
    Vergleiche mehrere OCRResult-Einträge

    Falls result_ids nicht angegeben, werden alle OCRResults des Dokuments verglichen.
    """
    if not OCR_AVAILABLE or compare_ocr_results is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR-Vergleich nicht verfügbar. Bitte Dependencies installieren.",
        )

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Hole OCRResults
    if result_ids:
        ocr_results = (
            db.query(OCRResult)
            .filter(
                OCRResult.document_id == document_id,
                OCRResult.id.in_(result_ids),
            )
            .all()
        )
    else:
        ocr_results = (
            db.query(OCRResult).filter(OCRResult.document_id == document_id).all()
        )

    if not ocr_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine OCRResults zum Vergleichen gefunden",
        )

    # Vergleich durchführen
    comparison = compare_ocr_results(ocr_results)

    return OCRComparisonResponse(**comparison)


@router.post("/documents/{document_id}/auto-review", response_model=dict)
def auto_review(document_id: int, db: Session = Depends(get_db)):
    """
    Prüft automatisch auf übereinstimmende OCR-Ergebnisse und erstellt Review wenn möglich

    Returns:
        Dict mit auto_reviewed (bool) und review_id (optional)
    """
    if not OCR_AVAILABLE or check_auto_review is None or suggest_best_result is None:
        return {
            "auto_reviewed": False,
            "reason": "OCR-Funktionen nicht verfügbar. Bitte Dependencies installieren.",
        }

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    # Hole alle OCRResults
    ocr_results = db.query(OCRResult).filter(OCRResult.document_id == document_id).all()

    if not ocr_results:
        return {"auto_reviewed": False, "reason": "Keine OCR-Ergebnisse gefunden"}

    # Prüfe ob automatisches Review möglich ist
    can_auto_review = check_auto_review(ocr_results)

    if not can_auto_review:
        return {
            "auto_reviewed": False,
            "reason": "Ergebnisse nicht ausreichend übereinstimmend",
        }

    # Bestimme bestes Ergebnis
    best_result_id = suggest_best_result(ocr_results)
    if not best_result_id:
        return {"auto_reviewed": False, "reason": "Kein geeignetes Ergebnis gefunden"}

    best_result = next((r for r in ocr_results if r.id == best_result_id), None)
    if not best_result:
        return {"auto_reviewed": False, "reason": "Bestes Ergebnis nicht gefunden"}

    # Prüfe ob bereits ein Review existiert
    existing_review = (
        db.query(OCRReview)
        .filter(OCRReview.document_id == document_id)
        .order_by(OCRReview.review_round.desc())
        .first()
    )

    if existing_review:
        return {
            "auto_reviewed": False,
            "reason": "Review bereits vorhanden",
            "existing_review_id": existing_review.id,
        }

    # Erstelle automatisches Review
    ocr_review = OCRReview(
        document_id=document_id,
        status=OCRReviewStatus.APPROVED,
        reviewed_ocr_result_id=best_result_id,
        final_text=best_result.text,
        reviewer_name="System (automatisch)",
        review_notes="Automatisch erstellt aufgrund übereinstimmender OCR-Ergebnisse",
        review_round=1,
    )

    db.add(ocr_review)
    db.commit()
    db.refresh(ocr_review)

    # Update Document
    document.ocr_text_final = best_result.text
    document.ocr_review_id = ocr_review.id
    document.status = DocumentStatus.REVIEWED
    db.commit()
    db.refresh(document)

    return {
        "auto_reviewed": True,
        "review_id": ocr_review.id,
        "selected_result_id": best_result_id,
        "reason": "Ergebnisse übereinstimmend",
    }


# Job-Management Endpoints
@router.post("/documents/{document_id}/jobs", response_model=OCRJobResponse)
def create_ocr_job(
    document_id: int,
    job_data: OCRJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Erstellt einen neuen OCR-Job und startet ihn im Hintergrund

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

    # Prüfe ob bereits ein aktiver Job existiert
    existing_job = (
        db.query(OCRJob)
        .filter(
            OCRJob.document_id == document_id,
            OCRJob.status.in_([OCRJobStatus.PENDING, OCRJobStatus.RUNNING]),
        )
        .first()
    )
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bereits ein aktiver Job vorhanden (ID: {existing_job.id})",
        )

    # Erstelle neuen Job
    ocr_job = OCRJob(
        document_id=document_id,
        status=OCRJobStatus.PENDING,
        language=job_data.language,
        use_correction=job_data.use_correction,
    )
    db.add(ocr_job)
    db.commit()
    db.refresh(ocr_job)

    # Starte Background-Task
    background_tasks.add_task(process_ocr_job, ocr_job.id)

    return OCRJobResponse.model_validate(ocr_job)


@router.get("/documents/{document_id}/jobs", response_model=list[OCRJobResponse])
def get_ocr_jobs(document_id: int, db: Session = Depends(get_db)):
    """
    Liste aller OCR-Jobs für ein Dokument
    """
    jobs = (
        db.query(OCRJob)
        .filter(OCRJob.document_id == document_id)
        .order_by(OCRJob.created_at.desc())
        .all()
    )
    return [OCRJobResponse.model_validate(job) for job in jobs]


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
