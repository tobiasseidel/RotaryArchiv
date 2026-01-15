# Architektur-Dokumentation

## Übersicht

RotaryArchiv verwendet eine Hybrid-Architektur mit PostgreSQL für Dokumente und einem Triple Store (RDF) für semantische Relationen.

## Komponenten

### Backend
- **FastAPI**: REST API und SPARQL Endpoint
- **PostgreSQL**: Dokumente, Metadaten, OCR-Text
- **Apache Jena/Fuseki**: Triple Store für RDF-Relationen

### OCR-Pipeline
- **Tesseract**: Lokale OCR-Engine
- **Ollama Vision**: Alternative OCR-Engine
- **Ollama GPT**: Fehlersuche und Annotation-Support

### NLP
- **spaCy**: Named Entity Recognition
- **Halb-automatische Klassifizierung**: Vorschläge mit Multi-Select

### Wikidata-Integration
- Automatische Suche bei neuen Entitäten
- Verknüpfung mit externen Wikidata-Objekten
- Import relevanter Informationen

## Datenmodell

### PostgreSQL Schema
- `documents`: Dokumente mit Metadaten
- `document_metadata`: Flexible Metadaten
- `annotations`: User-Annotationen

### Triple Store (RDF)
- Alle Relationen als Subjekt-Prädikat-Objekt
- RDF-kompatibel für Wikidata-Integration

## Workflow

1. Dokument hochladen
2. OCR (parallel: Tesseract + Ollama Vision)
3. Entity Extraction
4. User wählt Entitäten (Multi-Select)
5. Triple-Erstellung
6. Wikidata-Matching
7. Annotation
8. Export
