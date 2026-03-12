"""
Pydantic Schemas für API Requests/Responses
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

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
        description="OCR-Ergebnisse von verschiedenen Modellen: {'ollama': {...}, 'tesseract': {...}, 'llm_sight': {...}}",
    )
    llm_sight_reviews: list[dict[str, Any]] | None = Field(
        default=None,
        description="Liste aller KI-Review-Prüfungen (jede Prüfung ein Eintrag mit at, outcome, changes_summary, ...)",
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
    persistent_multibox_region: bool | None = Field(
        default=None,
        description="True wenn diese Box eine persistente Multibox-Region (äußere +X-Box) ist",
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

    job_type: str = Field(
        default="ocr",
        description="Job-Typ: ocr, bbox_review, llm_sight, quality, content_analysis, boundary_analysis, unit_content_analysis, ...",
    )
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
        description="Aktion: 'cancel' | 'restart' | 'pause' | 'resume' | 'archive' | 'delete'"
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


class DocumentListEntry(BaseModel):
    """Minimales Schema für Dokument-Listen (z. B. Dropdown), ohne OCR-Inhalt."""

    id: int
    filename: str
    title: str | None = None
    status: DocumentStatus

    class Config:
        from_attributes = True


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


class DocumentUnitSuggestionResponse(BaseModel):
    """Schema für einen Einheiten-Vorschlag (aus Grenzen-Analyse)."""

    id: int
    document_id: int
    page_ids: list[int]
    belongs_with_next: bool
    source_job_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUnitCreate(BaseModel):
    """Body zum manuellen Anlegen einer Einheit."""

    page_ids: list[int] = Field(
        ..., min_length=1, description="Seiten-IDs in Reihenfolge"
    )
    belongs_with_next: bool = Field(
        default=False,
        description="Gehört mit nächster Seite zusammen",
    )


class DocumentUnitUpdate(BaseModel):
    """Body zum Bearbeiten einer Einheit (alle Felder optional)."""

    page_ids: list[int] | None = Field(None, min_length=1)
    belongs_with_next: bool | None = None
    summary: str | None = None
    persons: list[dict[str, Any]] | None = None
    topic: str | None = None
    place: str | None = None
    event_date: str | None = None
    extracted_phrases: list[str] | None = None
    extracted_names: list[str] | None = None


class DocumentUnitResponse(BaseModel):
    """Schema für Content-Analyse-Einheit (eine oder mehrere zusammenhängende Seiten)"""

    id: int
    document_id: int
    page_ids: list[int]
    belongs_with_next: bool
    summary: str | None
    persons: list[dict[str, Any]]  # [{"name": "...", "role": "..."}]
    topic: str | None
    place: str | None
    event_date: str | None
    extracted_phrases: list[str]
    extracted_names: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("persons", "extracted_phrases", "extracted_names", mode="before")
    @classmethod
    def default_list(cls, v: Any) -> list:
        return v if isinstance(v, list) else []

    class Config:
        from_attributes = True


class UnassignedPageItem(BaseModel):
    """Seite eines Dokuments, die noch keiner Einheit zugeordnet ist (für manuelle Grenzen)."""

    page_id: int
    page_number: int
    full_text: str = Field(description="BBox-Text der Seite in Lesereihenfolge")


class ComposedUnitOverviewItem(BaseModel):
    """Eine zusammengesetzte Einheit für die Dokumenten-Übersicht inkl. full_text."""

    id: int
    document_id: int
    page_ids: list[int]
    page_numbers: list[int] = Field(
        description="Seitenzahlen (1-basiert) aus DocumentPage"
    )
    full_text: str = Field(description="Zusammengesetzter BBox-Text in Lesereihenfolge")
    belongs_with_next: bool
    summary: str | None
    persons: list[dict[str, Any]]
    topic: str | None
    place: str | None
    event_date: str | None
    extracted_phrases: list[str]
    extracted_names: list[str]
    created_at: datetime
    updated_at: datetime

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
    deskew_angle: float | None = Field(
        None, description="Deskew-Winkel in Grad (None = nicht gemessen)"
    )
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
