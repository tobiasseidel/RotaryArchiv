"""
SQLAlchemy Models für RotaryArchiv
"""

from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.rotary_archiv.core.database import Base


class DocumentStatus(str, Enum):
    """Workflow-Status für Dokumente"""

    UPLOADED = "uploaded"
    OCR_PENDING = "ocr_pending"
    OCR_DONE = "ocr_done"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"
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


class OCRSource(str, Enum):
    """Quellen für OCR-Ergebnisse"""

    TESSERACT = "tesseract"
    OLLAMA_VISION = "ollama_vision"
    GPT_CORRECTED = "gpt_corrected"
    MANUAL = "manual"
    COMBINED = "combined"


class OCRReviewStatus(str, Enum):
    """Status für OCR-Review"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class Document(Base):
    """Dokument-Model"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(
        String(512), nullable=False, index=True
    )  # unique entfernt, da zusammengefügte Docs gleichen Pfad haben können
    file_type = Column(String(50), nullable=False)  # pdf, jpg, png, etc.
    file_size = Column(Integer)  # in bytes

    # Für zusammengefügte Dokumente
    parent_document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=True, index=True
    )
    is_composite = Column(
        Integer, default=0, server_default="0", nullable=False
    )  # 0 = Einzeldokument, 1 = Zusammengesetzt
    page_number = Column(
        Integer, nullable=True
    )  # Seitenzahl in zusammengesetztem Dokument

    # OCR - Legacy-Felder (werden später entfernt, nach Migration)
    ocr_text = Column(Text, nullable=True)  # Deprecated: Verwende ocr_text_final
    ocr_text_tesseract = Column(Text, nullable=True)  # Deprecated
    ocr_text_ollama = Column(Text, nullable=True)  # Deprecated
    ocr_confidence = Column(String(50), nullable=True)  # Deprecated
    ocr_completed_at = Column(DateTime, nullable=True)

    # OCR-Review (neu)
    ocr_text_final = Column(Text, nullable=True)  # Finales, reviewtes OCR-Ergebnis

    # Metadaten
    document_type = Column(SQLEnum(DocumentType), nullable=True)
    title = Column(String(512), nullable=True)
    date = Column(
        DateTime, nullable=True, index=True
    )  # Datum des Dokuments (nicht Upload)

    # Workflow
    status = Column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.UPLOADED,
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    metadata_entries = relationship(
        "DocumentMetadata", back_populates="document", cascade="all, delete-orphan"
    )
    annotations = relationship(
        "Annotation", back_populates="document", cascade="all, delete-orphan"
    )
    pages = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    parent_document = relationship(
        "Document", remote_side=[id], backref="child_documents"
    )
    ocr_results = relationship(
        "OCRResult", back_populates="document", cascade="all, delete-orphan"
    )
    ocr_reviews = relationship(
        "OCRReview", back_populates="document", cascade="all, delete-orphan"
    )
    entity_occurrences = relationship(
        "EntityOccurrence", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class DocumentMetadata(Base):
    """Flexible Metadaten für Dokumente"""

    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
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
    wikidata_id = Column(
        String(50), nullable=True, unique=True, index=True
    )  # z.B. "Q123456"
    wikidata_label = Column(String(512), nullable=True)
    wikidata_description = Column(Text, nullable=True)
    wikidata_data = Column(JSON, nullable=True)  # Zusätzliche Wikidata-Daten

    # Weitere Metadaten
    description = Column(Text, nullable=True)
    extra_data = Column(
        JSON, nullable=True
    )  # Flexible Metadaten (metadata ist reserviert)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    occurrences = relationship(
        "EntityOccurrence", back_populates="entity", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type}')>"


class DocumentPage(Base):
    """Einzelne Seite eines PDF-Dokuments"""

    __tablename__ = "document_pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number = Column(Integer, nullable=False)  # Seitenzahl (1-basiert)
    file_path = Column(
        String(512), nullable=False
    )  # Pfad zur extrahierten Seite (PDF oder Bild)
    file_type = Column(String(50), nullable=False)  # pdf, png, jpg

    # OCR für einzelne Seite - Legacy (deprecated)
    ocr_text = Column(Text, nullable=True)  # Deprecated: Verwende OCRResult
    ocr_confidence = Column(String(50), nullable=True)  # Deprecated

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="pages")
    ocr_results = relationship(
        "OCRResult", back_populates="document_page", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DocumentPage(id={self.id}, document_id={self.document_id}, page={self.page_number})>"


class OCRResult(Base):
    """Einzelnes OCR-Ergebnis von einer Quelle"""

    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    document_page_id = Column(
        Integer, ForeignKey("document_pages.id"), nullable=True, index=True
    )  # Optional: für Seiten-spezifische OCR

    # Quelle
    source = Column(
        SQLEnum(OCRSource), nullable=False, index=True
    )  # tesseract, ollama_vision, gpt_corrected, manual, combined
    engine_version = Column(String(50), nullable=True)  # z.B. "tesseract-5.3.0"

    # Ergebnis
    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)  # 0.0-1.0, durchschnittliche Confidence
    confidence_details = Column(
        JSON, nullable=True
    )  # Detaillierte Confidence-Werte (z.B. pro Wort)

    # Metadaten
    processing_time_ms = Column(Integer, nullable=True)  # Verarbeitungszeit in ms
    language = Column(String(50), nullable=True)  # "deu+eng"
    error_message = Column(Text, nullable=True)  # Falls Fehler aufgetreten

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="ocr_results")
    document_page = relationship("DocumentPage", back_populates="ocr_results")

    def __repr__(self) -> str:
        return f"<OCRResult(id={self.id}, source='{self.source}', document_id={self.document_id})>"


class OCRReview(Base):
    """Review eines OCR-Ergebnisses (kann mehrere Runden haben)"""

    __tablename__ = "ocr_reviews"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )

    # Review-Status
    status = Column(
        SQLEnum(OCRReviewStatus),
        default=OCRReviewStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Referenz auf OCR-Ergebnis (kann None sein bei manueller Eingabe)
    reviewed_ocr_result_id = Column(
        Integer, ForeignKey("ocr_results.id"), nullable=True, index=True
    )

    # Finales Ergebnis (nach Review)
    final_text = Column(Text, nullable=True)  # Manuell korrigierter Text

    # Reviewer
    reviewer_id = Column(Integer, nullable=True)  # Später ForeignKey zu User
    reviewer_name = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)  # Notizen zum Review

    # Versionierung (für mehrere Review-Runden)
    review_round = Column(Integer, default=1, nullable=False)  # 1, 2, 3, ...
    previous_review_id = Column(
        Integer, ForeignKey("ocr_reviews.id"), nullable=True
    )  # Verknüpfung zur vorherigen Review-Runde

    # Timestamps
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="ocr_reviews")
    reviewed_ocr_result = relationship(
        "OCRResult", foreign_keys=[reviewed_ocr_result_id]
    )
    previous_review = relationship(
        "OCRReview", remote_side=[id], foreign_keys=[previous_review_id]
    )

    def __repr__(self) -> str:
        return f"<OCRReview(id={self.id}, status='{self.status}', document_id={self.document_id}, round={self.review_round})>"


class EntityOccurrence(Base):
    """Vorkommen einer Entität im OCR-Text mit Positionen"""

    __tablename__ = "entity_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    ocr_result_id = Column(
        Integer, ForeignKey("ocr_results.id"), nullable=True, index=True
    )  # Optional: auf welchem OCR-Ergebnis basiert die Erkennung

    # Position im Text (relativ zum finalen OCR-Text)
    start_char = Column(Integer, nullable=False)  # Start-Position (0-basiert)
    end_char = Column(Integer, nullable=False)  # End-Position (exklusiv)
    text_snippet = Column(String(512), nullable=True)  # Der erkannte Text-Snippet

    # Kontext
    context_before = Column(String(255), nullable=True)  # Text vor der Entität
    context_after = Column(String(255), nullable=True)  # Text nach der Entität

    # Erkennungs-Metadaten
    detection_method = Column(
        String(50), nullable=False, index=True
    )  # "ner", "manual", "wikidata_match", "regex"
    confidence = Column(Float, nullable=True)  # 0.0-1.0

    # Review
    is_confirmed = Column(
        Boolean, default=False, nullable=False, index=True
    )  # User hat bestätigt
    is_rejected = Column(Boolean, default=False, nullable=False)  # User hat abgelehnt

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="entity_occurrences")
    entity = relationship("Entity", back_populates="occurrences")
    ocr_result = relationship("OCRResult", foreign_keys=[ocr_result_id])

    def __repr__(self) -> str:
        return f"<EntityOccurrence(id={self.id}, entity_id={self.entity_id}, document_id={self.document_id}, start={self.start_char}, end={self.end_char})>"


class Annotation(Base):
    """User-Annotationen für Dokumente"""

    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )

    # Annotation-Inhalt
    text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=True)  # Start-Position im OCR-Text
    end_char = Column(Integer, nullable=True)  # End-Position im OCR-Text

    # Optional: Verknüpfung zu EntityOccurrence
    entity_occurrence_id = Column(
        Integer, ForeignKey("entity_occurrences.id"), nullable=True, index=True
    )

    # User (später mit Auth)
    user_id = Column(Integer, nullable=True)  # Temporär, später ForeignKey
    user_name = Column(String(255), nullable=True)  # Temporär

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="annotations")
    entity_occurrence = relationship(
        "EntityOccurrence", foreign_keys=[entity_occurrence_id]
    )

    def __repr__(self) -> str:
        return f"<Annotation(id={self.id}, document_id={self.document_id})>"
