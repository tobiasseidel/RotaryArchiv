# Datenmodell - Zusammenfassung

## Überblick

Das Datenmodell unterstützt jetzt einen vollständigen OCR-Workflow mit Review-Prozess und Entity-Erkennung mit Positionen.

## Workflow

```
1. Import → Document (status: UPLOADED)
   ↓
2. OCR-Verarbeitung → OCRResult (mehrere Quellen parallel)
   - Tesseract
   - Ollama Vision
   - GPT-korrigiert
   - Manuell
   Document.status → OCR_PENDING → OCR_DONE
   ↓
3. OCR-Review → OCRReview
   - User sieht alle OCR-Ergebnisse
   - User wählt bestes Ergebnis oder korrigiert manuell
   - OCRReview wird erstellt mit final_text
   - Document.ocr_text_final wird gesetzt
   - Document.status → REVIEW_PENDING → REVIEWED
   ↓
4. Entity-Erkennung → EntityOccurrence
   - NER läuft auf ocr_text_final
   - Für jede erkannte Entität wird EntityOccurrence erstellt
   - Positionen (start_char, end_char) werden gespeichert
   ↓
5. Meta-Informationen
   - Entities werden mit EntityOccurrence verknüpft
   - Annotations können auf EntityOccurrence verweisen
   - Triples können aus EntityOccurrence generiert werden
```

## Neue Tabellen

### OCRResult
- Speichert einzelne OCR-Ergebnisse von verschiedenen Quellen
- Kann auf Document- oder DocumentPage-Ebene sein
- Enthält: source, text, confidence, Metadaten

### OCRReview
- Review-Prozess für OCR-Ergebnisse
- Unterstützt mehrere Review-Runden (review_round)
- Status: pending, approved, rejected, needs_revision
- Enthält: final_text, reviewer, review_notes

### EntityOccurrence
- Vorkommen einer Entität im Text mit Positionen
- Enthält: start_char, end_char, text_snippet, context
- Review-Flags: is_confirmed, is_rejected
- Verknüpfung zu OCRResult (optional)

## Erweiterte Tabellen

### Document
- Neu: `ocr_text_final` (finales, reviewtes OCR-Ergebnis)
- Neu: Relationships zu OCRResult, OCRReview, EntityOccurrence
- Legacy: `ocr_text`, `ocr_text_tesseract`, `ocr_text_ollama` (werden später entfernt)

### DocumentPage
- Neu: Relationship zu OCRResult
- OCR-Ergebnisse können auch auf Seiten-Ebene gespeichert werden

### Annotation
- Neu: `entity_occurrence_id` (Verknüpfung zu EntityOccurrence)

### Entity
- Neu: Relationship zu EntityOccurrence

## Status-Workflow

```
UPLOADED → OCR_PENDING → OCR_DONE → REVIEW_PENDING → REVIEWED → CLASSIFIED → ANNOTATED → PUBLISHED
```

## Vorteile

1. **Flexibilität**: Neue OCR-Quellen können einfach hinzugefügt werden
2. **Nachvollziehbarkeit**: Alle OCR-Ergebnisse bleiben erhalten
3. **Review-Prozess**: Klarer Workflow für OCR-Review mit mehreren Runden
4. **Positionen**: Entities haben konkrete Positionen im Text
5. **Versionierung**: Verschiedene OCR-Versionen können verglichen werden
6. **Performance**: Nur finales OCR-Ergebnis wird für NER verwendet
7. **Seiten-Ebene**: OCR-Ergebnisse können auch auf Seiten-Ebene gespeichert werden (für PDF-Export)

## Nächste Schritte

1. API-Endpoints für OCR-Review erstellen
2. API-Endpoints für EntityOccurrence erstellen
3. OCR-Pipeline anpassen, um OCRResult zu erstellen
4. NER-Pipeline anpassen, um EntityOccurrence zu erstellen
5. Frontend für OCR-Review erstellen
6. Frontend für Entity-Review erstellen
