"""
SQLAlchemy Models für RotaryArchiv
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.rotary_archiv.core.database import Base


class DocumentStatus(str, Enum):
    """Workflow-Status für Dokumente"""
    UPLOADED = "uploaded"
    OCR_PENDING = "ocr_pending"
    OCR_DONE = "ocr_done"
    CLASSIFIED = "classified"
    ANNOTATED = "annotated"
    PUBLISHED = "published"


class EntityType(str, Enum):
    """Typen von Entitäten"""
    PERSON = "person"
    PLACE = "place"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    EVENT = "event"
    MEETING = "meeting"
    SPEAKER = "speaker"
    SPEECH_TOPIC = "speech_topic"
    CURRENT_EVENT = "current_event"
    CITY_HISTORY = "city_history"


class DocumentType(str, Enum):
    """Typen von Dokumenten"""
    MEETING_PROTOCOL = "meeting_protocol"
    INVITATION = "invitation"
    PHOTO = "photo"
    MEMBER_LIST = "member_list"
    FINANCIAL_REPORT = "financial_report"
    OTHER = "other"


class Document(Base):
    """Dokument-Model"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(512), nullable=False, unique=True)
    file_type = Column(String(50), nullable=False)  # pdf, jpg, png, etc.
    file_size = Column(Integer)  # in bytes
    
    # OCR
    ocr_text = Column(Text, nullable=True)
    ocr_text_tesseract = Column(Text, nullable=True)  # Tesseract Ergebnis
    ocr_text_ollama = Column(Text, nullable=True)    # Ollama Vision Ergebnis
    ocr_confidence = Column(String(50), nullable=True)  # JSON mit Confidence-Werten
    ocr_completed_at = Column(DateTime, nullable=True)
    
    # Metadaten
    document_type = Column(SQLEnum(DocumentType), nullable=True)
    title = Column(String(512), nullable=True)
    date = Column(DateTime, nullable=True, index=True)  # Datum des Dokuments (nicht Upload)
    
    # Workflow
    status = Column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.UPLOADED,
        nullable=False,
        index=True
    )
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    metadata_entries = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class DocumentMetadata(Base):
    """Flexible Metadaten für Dokumente"""
    __tablename__ = "document_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_json = Column(JSON, nullable=True)  # Für komplexe Werte
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="metadata_entries")
    
    def __repr__(self) -> str:
        return f"<DocumentMetadata(id={self.id}, key='{self.key}', document_id={self.document_id})>"


class Entity(Base):
    """Entitäten-Model (Personen, Orte, Organisationen, etc.)"""
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False, index=True)
    entity_type = Column(SQLEnum(EntityType), nullable=False, index=True)
    
    # Wikidata-Integration
    wikidata_id = Column(String(50), nullable=True, unique=True, index=True)  # z.B. "Q123456"
    wikidata_label = Column(String(512), nullable=True)
    wikidata_description = Column(Text, nullable=True)
    wikidata_data = Column(JSON, nullable=True)  # Zusätzliche Wikidata-Daten
    
    # Weitere Metadaten
    description = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Flexible Metadaten (metadata ist reserviert)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type}')>"


class Annotation(Base):
    """User-Annotationen für Dokumente"""
    __tablename__ = "annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Annotation-Inhalt
    text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=True)  # Start-Position im OCR-Text
    end_char = Column(Integer, nullable=True)    # End-Position im OCR-Text
    
    # User (später mit Auth)
    user_id = Column(Integer, nullable=True)  # Temporär, später ForeignKey
    user_name = Column(String(255), nullable=True)  # Temporär
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="annotations")
    
    def __repr__(self) -> str:
        return f"<Annotation(id={self.id}, document_id={self.document_id})>"
