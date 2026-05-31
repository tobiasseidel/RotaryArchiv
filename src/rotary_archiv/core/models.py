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
    erschliessungs_boxes = relationship(
        "ErschliessungsBox",
        back_populates="document_page",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DocumentPage(id={self.id}, document_id={self.document_id}, page={self.page_number})>"


class ErschliessungsBox(Base):
    """
    Erschließungs-Box auf einer Seite: verknüpft eine Stelle (bbox) mit dem
    Triple Store. Zwei Typen: entity (Person/Ort-Erwähnung) und beleg (Aussage mit Referenz).
    """

    __tablename__ = "erschliessungs_boxes"

    id = Column(Integer, primary_key=True, index=True)
    document_page_id = Column(
        Integer,
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # bbox in Normkoordinaten 0-1 oder Pixel: [x1, y1, x2, y2]
    bbox = Column(JSON, nullable=False)  # [x1, y1, x2, y2]
    box_type = Column(String(20), nullable=False, index=True)  # "entity" | "beleg"

    # Für box_type = "entity"
    entity_type = Column(String(20), nullable=True)  # "person" | "place" | ...
    entity_uri = Column(
        String(512), nullable=True
    )  # rotary:Person_<uuid> nach Zuordnung
    name = Column(String(512), nullable=True)  # eingegebener Suchbegriff

    # Für box_type = "beleg"
    subject_uri = Column(String(512), nullable=True)
    predicate_uri = Column(String(512), nullable=True)
    object_uri = Column(String(512), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document_page = relationship("DocumentPage", back_populates="erschliessungs_boxes")

    def __repr__(self) -> str:
        return f"<ErschliessungsBox(id={self.id}, page_id={self.document_page_id}, type={self.box_type})>"


class CachedImage(Base):
    """Persistierte Metadaten für lokal gecachte Bilder und Varianten."""

    __tablename__ = "cached_images"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_key = Column(String(1024), nullable=False, unique=True, index=True)
    source_url = Column(String(2048), nullable=False)
    mime_type = Column(String(120), nullable=True)
    original_path = Column(String(1024), nullable=False)
    variants_json = Column(
        JSON, nullable=False
    )  # {"64": "/media-cache/.../64.jpg", ...}
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    etag = Column(String(255), nullable=True)
    last_modified = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CachedImage(id={self.id}, source_type={self.source_type}, source_key={self.source_key})>"


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
    bboxes = relationship(
        "BBox", back_populates="ocr_result", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OCRResult(id={self.id}, source='{self.source}', document_id={self.document_id})>"


class BBox(Base):
    """Einzelne Bounding Box - normalisierte Tabelle statt JSON in bbox_data"""

    __tablename__ = "bboxes"

    id = Column(Integer, primary_key=True, index=True)
    ocr_result_id = Column(
        Integer,
        ForeignKey("ocr_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Box-Typ (ocr, manual, ignore_region, note)
    box_type = Column(String(50), nullable=False, default="ocr", index=True)

    # Geometrie
    bbox = Column(JSON, nullable=True)  # Relative Koordinaten [x1, y1, x2, y2]
    bbox_pixel = Column(JSON, nullable=True)  # Pixel-Koordinaten [x1, y1, x2, y2]
    text = Column(Text, nullable=True)  # Textinhalt der Box

    # Review-Status
    review_status = Column(
        String(50), nullable=True
    )  # pending, confirmed, rejected, ignored, ocr_done
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(255), nullable=True)

    # OCR-Ergebnisse verschiedener Engines
    ocr_results_data = Column(
        JSON, nullable=True
    )  # {"tesseract": "...", "ollama": "...", ...}
    differences = Column(
        JSON, nullable=True
    )  # Unterschiede zwischen Engine-Ergebnissen

    # Notiz-spezifische Felder
    note_author = Column(String(255), nullable=True)
    note_text = Column(Text, nullable=True)
    note_created_at = Column(String(50), nullable=True)

    # Weitere Metadaten
    deskew_angle = Column(Float, nullable=True)  # Deskew-Winkel für diese Box

    # Qualitätsmetriken (vorberechnet für SQL-Filterung)
    char_count = Column(Integer, nullable=True)  # Anzahl Zeichen im Text
    chars_per_1k_px = Column(Float, nullable=True)  # Zeichen pro 1000 Pixel
    area_px = Column(Integer, nullable=True)  # Fläche in Pixeln
    black_pixels = Column(Integer, nullable=True)  # Anzahl schwarzer Pixel
    black_pixels_per_char = Column(Float, nullable=True)  # Schwarze Pixel pro Zeichen
    left_pct = Column(Float, nullable=True)  # Linke Kante in % der Seitenbreite
    right_pct = Column(Float, nullable=True)  # Rechte Kante in % der Seitenbreite
    width_pct = Column(Float, nullable=True)  # Breite in % der Seitenbreite

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship
    ocr_result = relationship("OCRResult", back_populates="bboxes")

    def __repr__(self) -> str:
        return f"<BBox(id={self.id}, ocr_result_id={self.ocr_result_id}, box_type='{self.box_type}')>"

    def to_dict(self) -> dict:
        """Konvertiert BBox zu dict (kompatibel zu altem bbox_data Format)"""
        result = {
            "box_type": self.box_type,
            "bbox": self.bbox,
            "bbox_pixel": self.bbox_pixel,
            "text": self.text,
            "review_status": self.review_status,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "ocr_results": self.ocr_results_data,
            "differences": self.differences,
            "deskew_angle": self.deskew_angle,
        }
        if self.box_type == "note":
            result["note_author"] = self.note_author
            result["note_text"] = self.note_text
            result["note_created_at"] = self.note_created_at
        return result


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
