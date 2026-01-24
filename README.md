# RotaryArchiv

Ein digitales Archiv-System für Rotary Club Dokumente mit OCR-Verarbeitung.

## Features

- **PDF Upload**: Einfaches Hochladen von PDF-Dokumenten
- **OCR-Verarbeitung**: Automatische Texterkennung mit Ollama Vision
- **Job-Queue**: Seitenweise Verarbeitung in einer Queue
- **Klare Referenzen**: OCR-Ergebnisse mit Dokument-, Seiten- und Positionsreferenzen (BBox)

## Architektur

```
┌─────────────────────────────────────────┐
│  FastAPI API-Server                    │
│  - REST API                             │
│  - Erstellt OCR-Jobs (PENDING)          │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼──────────┐
│Datenbank (SQLite/PostgreSQL)           │
│                        │
│- Dokumente             │
│- Seiten                │
│- OCR-Jobs (Queue)      │
│- OCR-Ergebnisse        │
└─────────────┬──────────┘
              │
┌─────────────▼──────────┐
│  OCR-Worker (separater Prozess)        │
│  - Verarbeitet PENDING-Jobs            │
│  - Aktualisiert Job-Status             │
└─────────────────────────┘
```

**Wichtig**: Die Anwendung besteht aus **zwei Prozessen**:
- **API-Server**: Verarbeitet HTTP-Requests
- **Worker**: Verarbeitet OCR-Jobs im Hintergrund

Siehe [Worker-Architektur](docs/worker-architektur.md) für Details.

## Setup

### Voraussetzungen

- Python 3.11+
- PostgreSQL (oder SQLite für Entwicklung)
- Ollama (lokal installiert für OCR)
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
- Starte Docker Services: `docker-compose up -d` (falls vorhanden)

7. **Beide Prozesse starten** (API-Server + Worker):

**Terminal 1 - API-Server:**
```powershell
# Windows PowerShell:
.\start-backend.ps1

# Oder manuell:
uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Worker:**
```powershell
# Windows PowerShell:
.\start-worker.ps1

# Oder manuell:
python -m src.rotary_archiv.ocr.worker
```

**Wichtig**: Beide Prozesse müssen laufen:
- **API-Server**: Verarbeitet HTTP-Requests und erstellt OCR-Jobs
- **Worker**: Verarbeitet OCR-Jobs aus der Datenbank

Der Server läuft dann auf:
- **Frontend**: http://localhost:8000/
- **API-Dokumentation**: http://localhost:8000/docs
- **API-Endpoints**: http://localhost:8000/api/

Siehe [Worker-Architektur](docs/worker-architektur.md) für Details zur getrennten Architektur.

## Projekt-Struktur

```
RotaryArchiv/
├── src/rotary_archiv/    # Haupt-Code
│   ├── api/              # FastAPI Endpoints
│   │   ├── documents.py # Dokument-Upload & CRUD
│   │   ├── ocr.py       # OCR-Job-Management
│   │   └── pages.py     # Seiten-Extraktion
│   ├── core/             # Business Logic, Models
│   │   ├── models.py    # Datenbank-Models
│   │   └── database.py  # DB-Setup
│   ├── ocr/              # OCR Pipeline
│   │   ├── ollama_vision.py  # Ollama Vision OCR
│   │   ├── pipeline.py       # OCR-Pipeline
│   │   └── job_processor.py  # Job-Verarbeitung
│   └── utils/            # Utilities
├── alembic/              # DB Migrations
├── data/                 # Dokumente (nicht in Git)
└── static/               # Frontend
    └── index.html        # Minimales Frontend
```

## Workflow

1. **PDF hochladen** → Dokument wird erstellt, Status: `uploaded`
2. **OCR-Jobs erstellen** → Für jede Seite wird ein OCR-Job erstellt
3. **Job-Verarbeitung** → Jobs werden seitenweise abgearbeitet
4. **OCR-Ergebnisse** → Ergebnisse werden mit Referenzen (Dokument, Seite, Position/BBox) gespeichert

## API-Endpoints

- `GET /api/documents` - Liste aller Dokumente
- `POST /api/documents` - Neues Dokument hochladen
- `GET /api/documents/{id}` - Einzelnes Dokument
- `POST /api/documents/{id}/create-page-jobs` - Erstelle OCR-Jobs für Dokument
- `GET /api/ocr/documents/{id}/jobs` - Liste aller OCR-Jobs für ein Dokument
- `GET /api/ocr/jobs/{id}` - Einzelner OCR-Job
- `GET /api/pages/document/{id}` - Alle Seiten eines Dokuments

## Entwicklung

### Code-Qualität

Wir verwenden **Ruff** für Linting und Formatting.

**Windows PowerShell:**
```powershell
.\dev.ps1 lint              # Code prüfen
.\dev.ps1 format            # Code formatieren
.\dev.ps1 lint-fix          # Code prüfen und automatisch fixen
```

**Linux/Mac:**
```bash
make lint              # Code prüfen
make format            # Code formatieren
make lint-fix          # Code prüfen und automatisch fixen
```

### Datenbank-Migrationen

**Migration erstellen:**
```bash
alembic revision --autogenerate -m "Beschreibung"
```

**Migration ausführen:**
```bash
alembic upgrade head
```

## Hinweise

### Vorerst nicht verwendete Module

Folgende Module sind im Code vorhanden, werden aber aktuell nicht verwendet:
- `src/rotary_archiv/wikidata/` - Wikidata-Integration
- `src/rotary_archiv/core/triplestore.py` - Triple-Store Integration
- `src/rotary_archiv/api/triples.py` - Triple-Store API
- `src/rotary_archiv/api/wikidata.py` - Wikidata API
- `src/rotary_archiv/api/sparql.py` - SPARQL Endpoint

Diese Module können später wieder aktiviert werden.

## Lizenz

Siehe [LICENSE](LICENSE) für Details.
