# RotaryArchiv

Ein digitales Archiv-System für Rotary Club Dokumente mit OCR, semantischer Suche, Wikidata-Integration und Export-Funktionen.

## Features

- **OCR-Pipeline**: Parallel Tesseract + Ollama Vision, Vergleich und GPT-basierte Korrektur
- **Hybrid-Datenbank**: PostgreSQL für Dokumente, Triple Store (RDF) für Relationen
- **Wikidata-Integration**: Automatische Verknüpfung mit externen Entitäten
- **Semantische Suche**: Volltextsuche + Graph-basierte Abfragen (SPARQL)
- **Workflow-Management**: Status-basierte Dokumentenverarbeitung
- **Export**: Statische Websites, Broschüren, Podcast-Scripts

## Architektur

```
┌─────────────────────────────────────────┐
│  FastAPI (Python 3.11+)                 │
│  - REST API + SPARQL Endpoint           │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼──────┐    ┌───────▼────────┐
│PostgreSQL│    │  Apache Jena   │
│          │    │  (Fuseki)      │
│Dokumente │    │                │
│OCR-Text  │    │Triples (RDF)   │
│Metadaten │    │Relationen      │
└──────────┘    └────────────────┘
```

## Setup

### Voraussetzungen

- Python 3.11+
- Docker & Docker Compose
- Tesseract OCR
- Ollama (lokal installiert)

### Installation

1. Repository klonen:
```bash
git clone <repository-url>
cd RotaryArchiv
```

2. Virtual Environment erstellen:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Dependencies installieren:
```bash
pip install -r requirements.txt
```

4. Environment-Variablen konfigurieren:
```bash
cp .env.example .env
# .env bearbeiten mit eigenen Werten
```

5. Docker Services starten (PostgreSQL + Fuseki):
```bash
docker-compose up -d
```

6. Datenbank-Migrationen ausführen:
```bash
alembic upgrade head
```

7. FastAPI Server starten:
```bash
uvicorn src.rotary_archiv.main:app --reload
```

## Projekt-Struktur

```
RotaryArchiv/
├── src/rotary_archiv/    # Haupt-Code
│   ├── api/              # FastAPI Endpoints
│   ├── core/             # Business Logic, Models
│   ├── ocr/              # OCR Pipeline
│   ├── nlp/              # NLP & Entity Extraction
│   ├── wikidata/         # Wikidata Integration
│   └── utils/            # Utilities
├── tests/                # Tests
├── alembic/              # DB Migrations
├── data/                 # Dokumente (nicht in Git)
└── docs/                 # Dokumentation
```

## Workflow

1. **Dokument hochladen** → Status: `uploaded`
2. **OCR durchführen** (Tesseract + Ollama Vision parallel) → Status: `ocr_done`
3. **Entity Extraction** → Vorschläge für Personen/Orte/Organisationen
4. **User wählt aus** (Multi-Select) → Triples werden erstellt
5. **Wikidata-Matching** → Vorschläge für externe Verknüpfungen
6. **Annotation** → User kann Notizen hinzufügen
7. **Export** → Statische Website, Broschüre, etc.

## API-Endpoints

- `GET /api/documents` - Liste aller Dokumente
- `POST /api/documents` - Neues Dokument hochladen
- `GET /api/documents/{id}` - Einzelnes Dokument
- `GET /api/entities` - Alle Entitäten
- `POST /api/triples` - Neues Triple erstellen
- `GET /api/search?q=...` - Volltextsuche
- `POST /sparql` - SPARQL Query

## Entwicklung

### Tests ausführen:
```bash
pytest
```

### Datenbank-Migration erstellen:
```bash
alembic revision --autogenerate -m "Beschreibung"
alembic upgrade head
```

## Lizenz

[Lizenz hier einfügen]
