# Datenmodell: OCR-Erkennungen und Review-Prozess

## Aktuelle Situation

**Was wir haben:**
- `Document`: Basis-Dokument mit `ocr_text`, `ocr_text_tesseract`, `ocr_text_ollama`
- `DocumentPage`: Einzelne Seiten mit OCR
- `Annotation`: User-Annotationen mit `start_char`, `end_char`
- `Entity`: Entitäten ohne direkte Verknüpfung zu OCR-Positionen

**Probleme:**
1. OCR-Ergebnisse sind direkt im Document gespeichert (nicht flexibel)
2. Kein Review-Prozess für OCR-Ergebnisse
3. Keine Positionen für OCR-Erkennungen
4. Keine Verknüpfung zwischen OCR-Quellen und finalem Text
5. Entities haben keine Positionen im Text

## Vorgeschlagenes Datenmodell

### 1. OCRResult (Neue Tabelle)
Speichert einzelne OCR-Ergebnisse von verschiedenen Quellen:

```python
class OCRResult(Base):
    """Einzelnes OCR-Ergebnis von einer Quelle"""

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    document_page_id = Column(Integer, ForeignKey("document_pages.id"), nullable=True)

    # Quelle
    source = Column(String(50))  # "tesseract", "ollama_vision", "manual", "gpt_corrected"
    engine_version = Column(String(50), nullable=True)  # z.B. "tesseract-5.3.0"

    # Ergebnis
    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)  # 0.0-1.0
    confidence_details = Column(JSON, nullable=True)  # Detaillierte Confidence-Werte

    # Metadaten
    processing_time_ms = Column(Integer, nullable=True)
    language = Column(String(50), nullable=True)  # "deu+eng"
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
```

### 2. OCRReview (Neue Tabelle)
Review-Prozess für OCR-Ergebnisse:

```python
class OCRReview(Base):
    """Review eines OCR-Ergebnisses"""

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))

    # Review-Status
    status = Column(String(50))  # "pending", "approved", "rejected", "needs_revision"
    reviewed_ocr_result_id = Column(Integer, ForeignKey("ocr_results.id"), nullable=True)

    # Finales Ergebnis (nach Review)
    final_text = Column(Text, nullable=True)  # Manuell korrigierter Text

    # Reviewer
    reviewer_id = Column(Integer, nullable=True)  # Später ForeignKey zu User
    reviewer_name = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Timestamps
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

### 3. EntityOccurrence (Neue Tabelle)
Vorkommen von Entitäten im Text mit Positionen:

```python
class EntityOccurrence(Base):
    """Vorkommen einer Entität im OCR-Text"""

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"))
    ocr_result_id = Column(Integer, ForeignKey("ocr_results.id"), nullable=True)

    # Position im Text
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    text_snippet = Column(String(512), nullable=True)  # Der erkannte Text

    # Kontext
    context_before = Column(String(255), nullable=True)  # Text vor der Entität
    context_after = Column(String(255), nullable=True)   # Text nach der Entität

    # Erkennungs-Metadaten
    detection_method = Column(String(50))  # "ner", "manual", "wikidata_match"
    confidence = Column(Float, nullable=True)

    # Review
    is_confirmed = Column(Boolean, default=False)  # User hat bestätigt
    is_rejected = Column(Boolean, default=False)  # User hat abgelehnt

    created_at = Column(DateTime, server_default=func.now())
```

### 4. Erweiterte Document-Tabelle
```python
class Document(Base):
    # ... bestehende Felder ...

    # OCR-Review
    ocr_review_id = Column(Integer, ForeignKey("ocr_reviews.id"), nullable=True)
    ocr_text_final = Column(Text, nullable=True)  # Finales, reviewtes OCR-Ergebnis

    # Relationships
    ocr_results = relationship("OCRResult", back_populates="document", cascade="all, delete-orphan")
    ocr_review = relationship("OCRReview", back_populates="document", uselist=False)
    entity_occurrences = relationship("EntityOccurrence", back_populates="document", cascade="all, delete-orphan")
```

### 5. Erweiterte Entity-Tabelle
```python
class Entity(Base):
    # ... bestehende Felder ...

    # Relationships
    occurrences = relationship("EntityOccurrence", back_populates="entity", cascade="all, delete-orphan")
```

## Workflow

### 1. Import → Document
- Dokument wird hochgeladen
- `Document` wird erstellt mit `status=UPLOADED`

### 2. OCR-Verarbeitung
- Mehrere OCR-Quellen laufen parallel
- Für jede Quelle wird ein `OCRResult` erstellt
- `Document.status` → `OCR_PENDING` → `OCR_DONE`

### 3. OCR-Review
- User sieht alle OCR-Ergebnisse
- User wählt bestes Ergebnis oder korrigiert manuell
- `OCRReview` wird erstellt mit `final_text`
- `Document.ocr_text_final` wird gesetzt

### 4. Entity-Erkennung
- NER läuft auf `ocr_text_final`
- Für jede erkannte Entität wird `EntityOccurrence` erstellt
- Positionen (`start_char`, `end_char`) werden gespeichert

### 5. Meta-Informationen
- Entities werden mit `EntityOccurrence` verknüpft
- Annotations können auf `EntityOccurrence` verweisen
- Triples können aus `EntityOccurrence` generiert werden

## Vorteile

1. **Flexibilität**: Neue OCR-Quellen können einfach hinzugefügt werden
2. **Nachvollziehbarkeit**: Alle OCR-Ergebnisse bleiben erhalten
3. **Review-Prozess**: Klarer Workflow für OCR-Review
4. **Positionen**: Entities haben konkrete Positionen im Text
5. **Versionierung**: Verschiedene OCR-Versionen können verglichen werden
6. **Performance**: Nur finales OCR-Ergebnis wird für NER verwendet

## Offene Fragen

1. Sollen OCR-Ergebnisse auch auf Seiten-Ebene gespeichert werden? (Ja, für große Dokumente)
2. Wie viele OCR-Quellen sollen unterstützt werden? (Aktuell: Tesseract, Ollama Vision, GPT-Korrektur)
3. Soll es eine automatische Auswahl des besten OCR-Ergebnisses geben? (Ja, als Vorschlag)
4. Wie sollen Positionen bei Text-Korrekturen gehandhabt werden? (Neu-Erkennung nach Korrektur)
