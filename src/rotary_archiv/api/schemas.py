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
    EntityType,
    OCRJobStatus,
    OCRReviewStatus,
    OCRSource,
)


# OCR Schemas (müssen vor DocumentResponse definiert werden)
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

    class Config:
        from_attributes = True


class OCRReviewCreate(BaseModel):
    """Schema für OCR-Review-Erstellung"""

    reviewed_ocr_result_id: int | None = Field(
        None, description="ID des zu reviewenden OCRResult (optional)"
    )
    final_text: str | None = Field(
        None, description="Manuell korrigierter Text (optional)"
    )
    review_notes: str | None = Field(None, description="Notizen zum Review (optional)")
    reviewer_name: str | None = Field(None, description="Name des Reviewers (optional)")


class OCRReviewResponse(BaseModel):
    """Schema für OCRReview-Response"""

    id: int
    document_id: int
    status: OCRReviewStatus
    reviewed_ocr_result_id: int | None = None
    final_text: str | None = None
    reviewer_id: int | None = None
    reviewer_name: str | None = None
    review_notes: str | None = None
    review_round: int
    previous_review_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OCRComparisonResponse(BaseModel):
    """Schema für OCR-Vergleichs-Response"""

    results: list[dict[str, Any]] = Field(
        ..., description="Liste der verglichenen Ergebnisse"
    )
    metrics: dict[str, Any] = Field(..., description="Gesamt-Metriken")
    suggested_best: int | None = Field(
        None, description="ID des vorgeschlagenen besten Ergebnisses"
    )


class OCRJobResponse(BaseModel):
    """Schema für OCRJob-Response"""

    id: int
    document_id: int
    document_page_id: int | None = None
    status: OCRJobStatus
    language: str
    use_correction: bool
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

    language: str = Field(default="deu+eng", description="Sprache für Tesseract")
    use_correction: bool = Field(default=True, description="GPT-Korrektur verwenden")


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
    ocr_text_final: str | None = None  # Finales, reviewtes OCR-Ergebnis
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    # Relationships werden optional hinzugefügt wenn benötigt
    ocr_results: list[OCRResultResponse] | None = None
    ocr_review: OCRReviewResponse | None = None

    class Config:
        from_attributes = True


# Entity Schemas
class EntityBase(BaseModel):
    """Base Schema für Entität"""

    name: str
    entity_type: EntityType
    description: str | None = None


class EntityCreate(EntityBase):
    """Schema für Entität-Erstellung"""

    wikidata_id: str | None = None


class EntityUpdate(BaseModel):
    """Schema für Entität-Update"""

    name: str | None = None
    description: str | None = None
    wikidata_id: str | None = None


class EntityResponse(EntityBase):
    """Schema für Entität-Response"""

    id: int
    wikidata_id: str | None = None
    wikidata_label: str | None = None
    wikidata_description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Annotation Schemas
class AnnotationBase(BaseModel):
    """Base Schema für Annotation"""

    text: str
    start_char: int | None = None
    end_char: int | None = None


class AnnotationCreate(AnnotationBase):
    """Schema für Annotation-Erstellung"""

    document_id: int


class AnnotationResponse(AnnotationBase):
    """Schema für Annotation-Response"""

    id: int
    document_id: int
    user_name: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Triple Schemas
class TripleCreate(BaseModel):
    """Schema für Triple-Erstellung"""

    subject: str
    predicate: str
    object_value: str
    object_type: str = "uri"  # "uri" oder "literal"


class TripleResponse(BaseModel):
    """Schema für Triple-Response"""

    subject: str
    predicate: str
    object_value: str
    object_type: str


# OCR Legacy Schema
class OCRResultLegacy(BaseModel):
    """Schema für OCR-Ergebnis (Legacy, für Rückwärtskompatibilität)"""

    text: str
    tesseract: dict[str, Any]
    ollama_vision: dict[str, Any]
    processed_at: str


# Search Schemas
class SearchRequest(BaseModel):
    """Schema für Suchanfrage"""

    query: str
    limit: int = Field(default=50, ge=1, le=500)


class SearchResponse(BaseModel):
    """Schema für Suchergebnis"""

    documents: list[DocumentResponse]
    entities: list[EntityResponse]
    total: int


# Wikidata Schemas
class WikidataSearchRequest(BaseModel):
    """Schema für Wikidata-Suche"""

    query: str
    limit: int = Field(default=10, ge=1, le=50)


class WikidataMatchRequest(BaseModel):
    """Schema für Wikidata-Match"""

    name: str
    entity_type: EntityType
    context: str | None = None
