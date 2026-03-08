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
    PDF_NATIVE = "pdf_native"  # Text ohne OCR aus PDF extrahiert
    GPT_CORRECTED = "gpt_corrected"
    MANUAL = "manual"
    COMBINED = "combined"


class OCRJobStatus(str, Enum):
    """Status für OCR-Jobs"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    ARCHIVED = "archived"


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
    pages = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    parent_document = relationship(
        "Document", remote_side=[id], backref="child_documents"
    )
    ocr_results = relationship(
        "OCRResult", back_populates="document", cascade="all, delete-orphan"
    )
    ocr_jobs = relationship(
        "OCRJob", back_populates="document", cascade="all, delete-orphan"
    )
    document_units = relationship(
        "DocumentUnit", back_populates="document", cascade="all, delete-orphan"
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


class DocumentPage(Base):
    """Einzelne Seite eines PDF-Dokuments"""

    __tablename__ = "document_pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number = Column(Integer, nullable=False)  # Seitenzahl (1-basiert)
    file_path = Column(
        String(512), nullable=True
    )  # Pfad zur extrahierten Seite (PDF oder Bild) - optional, None für virtuelle Seiten
    file_type = Column(String(50), nullable=False)  # pdf, png, jpg
    is_extracted = Column(
        Boolean, default=False, nullable=False, server_default="0"
    )  # True wenn Seite als Datei extrahiert wurde

    # Deskew: Winkel (Grad), der beim Erzeugen von OCR/BBox angewandt wurde.
    # NULL = Rohbild (Legacy). Drehpunkt bei Transformation: obere linke Ecke (0,0).
    deskew_angle = Column(Float, nullable=True)

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

    # Bounding Boxes (für BBox OCR)
    bbox_data = Column(
        JSON, nullable=True
    )  # Liste von BBox-Objekten: [{"text": "...", "bbox": [x1,y1,x2,y2], "bbox_pixel": [...]}, ...]
    image_width = Column(
        Integer, nullable=True
    )  # Breite des verarbeiteten Bildes in Pixeln
    image_height = Column(
        Integer, nullable=True
    )  # Höhe des verarbeiteten Bildes in Pixeln

    # Qualitätsmetriken
    quality_metrics = Column(
        JSON, nullable=True
    )  # Qualitätsmetriken: {"coverage": {...}, "density": {...}}

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="ocr_results")
    document_page = relationship("DocumentPage", back_populates="ocr_results")

    def __repr__(self) -> str:
        return f"<OCRResult(id={self.id}, source='{self.source}', document_id={self.document_id})>"


class OCRJob(Base):
    """OCR-Job für asynchrone Verarbeitung"""

    __tablename__ = "ocr_jobs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    document_page_id = Column(
        Integer, ForeignKey("document_pages.id"), nullable=True, index=True
    )  # Optional: für seitenweise OCR-Jobs
    status = Column(
        SQLEnum(OCRJobStatus),
        default=OCRJobStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Job-Parameter
    job_type = Column(
        String(50), default="ocr", nullable=False, index=True
    )  # "ocr" oder "bbox_review"
    language = Column(String(50), default="deu+eng", nullable=False)
    use_correction = Column(Boolean, default=True, nullable=False)
    priority = Column(
        Integer, default=0, nullable=False, index=True
    )  # Niedrigere Zahl = höhere Priorität

    # Fortschritt und Ergebnisse
    progress = Column(Float, default=0.0, nullable=False)  # 0.0-100.0
    current_step = Column(
        String(255), nullable=True
    )  # z.B. "Tesseract OCR", "Ollama Vision", "GPT Correction"
    error_message = Column(Text, nullable=True)
    job_params = Column(
        JSON, nullable=True
    )  # z.B. {"bbox_indices": [0, 2, 5]} für llm_sight

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="ocr_jobs")
    document_page = relationship("DocumentPage", backref="ocr_jobs")

    def __repr__(self) -> str:
        return f"<OCRJob(id={self.id}, document_id={self.document_id}, document_page_id={self.document_page_id}, status={self.status})>"


class DocumentUnit(Base):
    """
    Inhaltseinheit aus einer oder mehreren zusammenhängenden Seiten (z. B. Protokoll).
    Ergebnis der Content-Analyse: Zusammenfassung, Personen, Thema, Ort/Datum,
    sowie extrahierte Floskeln und Namen für OCR-Sicht.
    """

    __tablename__ = "document_units"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    page_ids = Column(JSON, nullable=False)  # Liste von document_page.id in Reihenfolge
    belongs_with_next = Column(
        Boolean, default=False, nullable=False, server_default="0"
    )
    summary = Column(Text, nullable=True)
    persons = Column(
        JSON, nullable=True
    )  # [{"name": "...", "role": "Clubvorstand"|...}]
    topic = Column(String(512), nullable=True)
    place = Column(String(512), nullable=True)
    event_date = Column(String(100), nullable=True)  # frei formatiert oder ISO
    extracted_phrases = Column(JSON, nullable=True)  # Liste typischer Formulierungen
    extracted_names = Column(JSON, nullable=True)  # Liste erwähnter Namen

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document = relationship("Document", back_populates="document_units")

    def __repr__(self) -> str:
        return f"<DocumentUnit(id={self.id}, document_id={self.document_id}, page_ids={self.page_ids})>"


class DocumentUnitSuggestion(Base):
    """
    Vorschlag für eine Einheit (aus Grenzen-Analyse). Wird zu DocumentUnit,
    wenn der Nutzer „Übernehmen“ wählt.
    """

    __tablename__ = "document_unit_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    page_ids = Column(JSON, nullable=False)  # Liste von document_page.id
    belongs_with_next = Column(
        Boolean, default=False, nullable=False, server_default="0"
    )
    source_job_id = Column(
        Integer, ForeignKey("ocr_jobs.id"), nullable=True, index=True
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    document = relationship("Document", backref="document_unit_suggestions")
    source_job = relationship("OCRJob", backref="unit_suggestions_created")

    def __repr__(self) -> str:
        return f"<DocumentUnitSuggestion(id={self.id}, document_id={self.document_id}, page_ids={self.page_ids})>"


class AppSetting(Base):
    """Globale App-Einstellungen (Key-Value), z. B. für OCR-Sichtung."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)
    value_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AppSetting(id={self.id}, key='{self.key}')>"
