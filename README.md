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
- Docker & Docker Compose (optional, für PostgreSQL/Fuseki)
- Tesseract OCR (optional, für OCR)
- Ollama (optional, lokal installiert für OCR)
- Poppler (optional, für PDF-zu-Bild-Konvertierung)
  - Windows: Download von https://github.com/oschwartz10612/poppler-windows/releases
  - Poppler in Projekt-Verzeichnis ablegen (z.B. `./poppler/`) und in `.env` konfigurieren

### Installation

1. Repository klonen:
```bash
git clone <repository-url>
cd RotaryArchiv
```

2. Virtual Environment erstellen:
```bash
python -m venv venv
```

3. Virtual Environment aktivieren:
```bash
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

4. Dependencies installieren:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5. Environment-Variablen konfigurieren:
```bash
# Windows PowerShell:
Copy-Item .env.example .env

# Linux/Mac:
cp .env.example .env
```

Bearbeite `.env` mit eigenen Werten (optional - Standardwerte funktionieren für lokalen Test mit SQLite).

6. Datenbank-Migrationen ausführen:
```bash
alembic upgrade head
```

**Hinweis**: Standardmäßig wird SQLite verwendet (für schnellen Start). Für PostgreSQL:
- Ändere in `.env`: `POSTGRES_HOST=localhost` (statt `sqlite`)
- Installiere `psycopg2-binary`: `pip install psycopg2-binary`
- Starte Docker Services: `docker-compose up -d`

7. FastAPI Server starten:
```bash
# Aktiviere Virtual Environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Starte Server
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

**Alternative (Windows CMD):**
```bash
venv\Scripts\activate
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

**Alternative (Linux/Mac):**
```bash
source venv/bin/activate
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

Der Server läuft dann auf:
- **Frontend**: http://localhost:8000/
- **API-Dokumentation**: http://localhost:8000/docs
- **API-Endpoints**: http://localhost:8000/api/

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

### Server starten

**Schnellstart (mit aktiviertem venv):**
```bash
uvicorn src.rotary_archiv.main:app --reload
```

**Mit expliziten Parametern:**
```bash
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

**Im Hintergrund (Windows PowerShell):**
```bash
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\venv\Scripts\Activate.ps1; uvicorn src.rotary_archiv.main:app --reload"
```

### Zugriff auf die Anwendung

Nach dem Start sind verfügbar:
- **Frontend**: http://localhost:8000/ (Upload-Interface)
- **API-Dokumentation (Swagger)**: http://localhost:8000/docs
- **Alternative API-Dokumentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Tests ausführen:
```bash
pytest
```

### Datenbank-Migration erstellen:
```bash
alembic revision --autogenerate -m "Beschreibung"
alembic upgrade head
```

### Server stoppen:
Drücke `Ctrl+C` im Terminal, in dem der Server läuft.

## Lizenz

[Lizenz hier einfügen]
