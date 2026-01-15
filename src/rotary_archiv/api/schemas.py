"""
Pydantic Schemas für API Requests/Responses
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.rotary_archiv.core.models import DocumentStatus, DocumentType, EntityType


# Document Schemas
class DocumentBase(BaseModel):
    """Base Schema für Dokument"""
    filename: str
    document_type: Optional[DocumentType] = None
    title: Optional[str] = None
    date: Optional[datetime] = None


class DocumentCreate(DocumentBase):
    """Schema für Dokument-Erstellung"""
    pass


class DocumentUpdate(BaseModel):
    """Schema für Dokument-Update"""
    document_type: Optional[DocumentType] = None
    title: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[DocumentStatus] = None


class DocumentResponse(DocumentBase):
    """Schema für Dokument-Response"""
    id: int
    file_path: str
    file_type: str
    file_size: Optional[int] = None
    ocr_text: Optional[str] = None
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Entity Schemas
class EntityBase(BaseModel):
    """Base Schema für Entität"""
    name: str
    entity_type: EntityType
    description: Optional[str] = None


class EntityCreate(EntityBase):
    """Schema für Entität-Erstellung"""
    wikidata_id: Optional[str] = None


class EntityUpdate(BaseModel):
    """Schema für Entität-Update"""
    name: Optional[str] = None
    description: Optional[str] = None
    wikidata_id: Optional[str] = None


class EntityResponse(EntityBase):
    """Schema für Entität-Response"""
    id: int
    wikidata_id: Optional[str] = None
    wikidata_label: Optional[str] = None
    wikidata_description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Annotation Schemas
class AnnotationBase(BaseModel):
    """Base Schema für Annotation"""
    text: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class AnnotationCreate(AnnotationBase):
    """Schema für Annotation-Erstellung"""
    document_id: int


class AnnotationResponse(AnnotationBase):
    """Schema für Annotation-Response"""
    id: int
    document_id: int
    user_name: Optional[str] = None
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


# OCR Schemas
class OCRResult(BaseModel):
    """Schema für OCR-Ergebnis"""
    text: str
    tesseract: Dict[str, Any]
    ollama_vision: Dict[str, Any]
    processed_at: str


# Search Schemas
class SearchRequest(BaseModel):
    """Schema für Suchanfrage"""
    query: str
    limit: int = Field(default=50, ge=1, le=500)


class SearchResponse(BaseModel):
    """Schema für Suchergebnis"""
    documents: List[DocumentResponse]
    entities: List[EntityResponse]
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
    context: Optional[str] = None
