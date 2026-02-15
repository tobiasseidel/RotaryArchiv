"""
Pydantic Schemas für API Requests/Responses
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.rotary_archiv.core.models import (
    DocumentStatus,
    DocumentType,
    OCRJobStatus,
    OCRSource,
)


# OCR Schemas
class BBoxItem(BaseModel):
    """Einzelne Bounding Box"""

    text: str
    bbox: list[float] = Field(
        description="Relative Koordinaten [x_min, y_min, x_max, y_max] (0.0-1.0)"
    )
    bbox_pixel: list[int] = Field(description="Pixel-Koordinaten [x1, y1, x2, y2]")
    # Review-Felder (optional)
    review_status: str | None = Field(
        default="pending",
        description="Review-Status: pending, auto_confirmed, confirmed, rejected, ignored, ocr_done",
    )
    reviewed_at: datetime | None = Field(
        default=None, description="Zeitpunkt der Review"
    )
    reviewed_by: str | None = Field(default=None, description="User-ID des Reviewers")
    ocr_results: dict[str, Any] | None = Field(
        default=None,
        description="OCR-Ergebnisse von verschiedenen Modellen: {'ollama': {...}, 'tesseract': {...}}",
    )
    differences: list[dict[str, Any]] | None = Field(
        default=None, description="Liste von Unterschieden zwischen OCR-Ergebnissen"
    )
    # Box-Typ und Notiz (optional)
    box_type: str | None = Field(
        default=None,
        description="Typ: ocr, ignore_region, note",
    )
    note_author: str | None = Field(default=None, description="Autor der Notiz")
    note_text: str | None = Field(default=None, description="Text der Notiz")
    note_created_at: str | None = Field(
        default=None, description="Erstellungszeitpunkt der Notiz (ISO)"
    )


class OCRResultResponse(BaseModel):
    """Schema für OCRResult-Response"""

    id: int
    document_id: int
    document_page_id: int | None = None
    source: OCRSource
    engine_version: str | None = None
    text: str
    confidence: float | None = None
    confidence_details: dict[str, Any] | None = None
    processing_time_ms: int | None = None
    language: str | None = None
    error_message: str | None = None
    created_at: datetime
    # BBox-Felder
    bbox_data: list[BBoxItem] | None = None
    image_width: int | None = None
    image_height: int | None = None

    class Config:
        from_attributes = True


class OCRJobResponse(BaseModel):
    """Schema für OCRJob-Response"""

    id: int
    document_id: int
    document_page_id: int | None = None
    job_type: str = Field(
        default="ocr", description="Job-Typ: 'ocr' oder 'bbox_review'"
    )
    status: OCRJobStatus
    language: str
    use_correction: bool
    priority: int = Field(
        default=0, description="Priorität (niedrigere Zahl = höhere Priorität)"
    )
    progress: float
    current_step: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class OCRJobCreate(BaseModel):
    """Schema für OCRJob-Erstellung"""

    language: str = Field(
        default="deu+eng",
        description="Sprache (wird ignoriert, Ollama erkennt automatisch)",
    )
    use_correction: bool = Field(
        default=False, description="Wird ignoriert (keine Korrektur mehr)"
    )


# Queue-Status: gemeinsames Statuspaket für Job-Queue (ein Request statt vieler)
class QueueStatusJobItem(BaseModel):
    """Job-Eintrag im Queue-Status mit page_number."""

    id: int
    document_id: int
    document_page_id: int | None = None
    page_number: int | None = Field(
        default=None, description="Seitenzahl aus DocumentPage"
    )
    job_type: str = Field(default="ocr", description="'ocr' oder 'bbox_review'")
    status: OCRJobStatus
    language: str
    use_correction: bool
    priority: int = 0
    progress: float
    current_step: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class QueueStatusDocumentItem(BaseModel):
    """Dokument mit Jobs für Queue-Status."""

    id: int
    filename: str
    title: str | None = None
    status: DocumentStatus
    file_type: str
    jobs: list[QueueStatusJobItem] = Field(default_factory=list)


class QueueStatusResponse(BaseModel):
    """Gemeinsames Statuspaket: Dokumente inkl. Jobs mit page_number."""

    documents: list[QueueStatusDocumentItem] = Field(default_factory=list)


# Batch-Job-Management Schemas
class JobBatchRequest(BaseModel):
    """Request für Batch-Job-Aktionen"""

    job_ids: list[int] = Field(description="Liste von Job-IDs")
    action: str = Field(
        description="Aktion: 'cancel' | 'restart' | 'pause' | 'resume' | 'archive'"
    )


class JobBatchError(BaseModel):
    """Fehler für einen einzelnen Job in Batch-Operation"""

    job_id: int
    reason: str


class JobBatchResponse(BaseModel):
    """Response für Batch-Job-Aktionen"""

    updated: int = Field(description="Anzahl erfolgreich aktualisierter Jobs")
    errors: list[JobBatchError] = Field(
        default_factory=list, description="Liste von Fehlern pro Job"
    )


# Document Schemas
class DocumentBase(BaseModel):
    """Base Schema für Dokument"""

    filename: str
    document_type: DocumentType | None = None
    title: str | None = None
    date: datetime | None = None


class DocumentCreate(DocumentBase):
    """Schema für Dokument-Erstellung"""

    pass


class DocumentUpdate(BaseModel):
    """Schema für Dokument-Update"""

    document_type: DocumentType | None = None
    title: str | None = None
    date: datetime | None = None
    status: DocumentStatus | None = None


class DocumentResponse(DocumentBase):
    """Schema für Dokument-Response"""

    id: int
    file_path: str
    file_type: str
    file_size: int | None = None
    parent_document_id: int | None = None
    is_composite: int | None = None
    page_number: int | None = None
    ocr_text: str | None = None  # Legacy, deprecated
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    # Relationships werden optional hinzugefügt wenn benötigt
    ocr_results: list[OCRResultResponse] | None = None

    class Config:
        from_attributes = True


# Page Inspect Schema
class PageInspectResponse(BaseModel):
    """Schema für Page Inspect View mit Bounding Boxes"""

    page_id: int
    document_id: int
    page_number: int
    image_url: str = Field(description="URL zum Seitenbild")
    image_width: int = Field(description="Bildbreite in Pixeln")
    image_height: int = Field(description="Bildhöhe in Pixeln")
    ocr_results: list[OCRResultResponse] = Field(
        description="OCR-Ergebnisse mit Bounding Boxes"
    )

    class Config:
        from_attributes = True


# NOTE: Folgende Schemas sind vorerst nicht verwendet (für später):
# - Entity Schemas (Entity, EntityCreate, EntityResponse, etc.)
# - Annotation Schemas (Annotation, AnnotationCreate, AnnotationResponse, etc.)
# - Triple Schemas (TripleCreate, TripleResponse)
# - Search Schemas (SearchRequest, SearchResponse)
# - Wikidata Schemas (WikidataSearchRequest, WikidataMatchRequest)
# - OCRReview Schemas (OCRReviewCreate, OCRReviewResponse)
