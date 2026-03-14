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

**Start (empfohlen):**
- **Terminal 1:** `.\start-backend.ps1` – startet den API-Server
- **Terminal 2:** `.\start-worker.ps1` – startet den OCR-Worker

**Beenden:** In beiden Terminals mit **Ctrl+C** beenden. Optional: `.\stop-backend.ps1` und `.\stop-worker.ps1`, falls Prozesse ohne Fenster laufen oder der Port 8000 belegt bleibt.

**Manueller Start (ohne Skripte):**
```powershell
uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port 8000
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

### Optionale Dienste (Docker)

Für den lokalen Alltag reichen die PS1-Skripte und SQLite. **Docker wird aktuell nicht benötigt.**

Falls du später PostgreSQL oder den Triple Store (Fuseki) nutzen möchtest:
- `docker-compose up -d` startet Postgres und Fuseki (siehe `docker-compose.yml`).
- In `.env` dann `POSTGRES_HOST=localhost` setzen und ggf. Fuseki-URL anpassen.

## Projekt-Struktur

```
RotaryArchiv/
├── src/rotary_archiv/       # Haupt-Code
│   ├── api/                 # FastAPI Endpoints
│   │   ├── documents.py     # Dokument-Upload, CRUD, DocumentUnits
│   │   ├── ocr.py           # OCR-Job-Management
│   │   ├── pages.py         # Seiten-Extraktion
│   │   ├── review.py       # BBox-Review, OCR-Sichtung
│   │   ├── quality.py       # Qualitätsmetriken
│   │   └── settings.py     # App-Einstellungen (OCR-Sichtung, Content-Analyse)
│   ├── core/                # Business Logic, Models
│   │   ├── models.py        # Datenbank-Models
│   │   ├── database.py     # DB-Setup
│   │   └── triplestore.py   # Triple-Store (vorerst ungenutzt)
│   ├── ocr/                 # OCR Pipeline
│   │   ├── ollama_vision.py # Ollama Vision OCR
│   │   ├── tesseract_ocr.py # Tesseract OCR (optional, siehe Konfiguration)
│   │   ├── pipeline.py      # OCR-Pipeline
│   │   ├── bbox_ocr.py      # BBox-OCR (mehrere Engines)
│   │   ├── job_processor.py # Job-Verarbeitung
│   │   ├── worker.py        # Worker-Prozess
│   │   ├── content_analysis_llm.py # Content-Analyse (Einheiten, Personen, Ort)
│   │   └── llm_sight.py     # LLM-Sichtung für BBoxen
│   ├── utils/               # Utilities (PDF, Bilder, BBox, Qualität)
│   └── wikidata/            # Wikidata-Integration (vorerst ungenutzt)
├── alembic/                 # DB Migrations
├── data/                    # Dokumente (nicht in Git)
└── static/                  # Frontend
    └── index.html           # Minimales Frontend
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

### Konfiguration (optional)

- **Debug-Crops:** Ausgeschnittene BBox-Bilder werden standardmäßig nicht gespeichert. Zum Entwickeln/Debuggen in `.env` setzen: `DEBUG_SAVE_BBOX_CROPS=true`. Speicherort: `./data/debug/bbox_crops` (konfigurierbar über `DEBUG_BBOX_CROPS_PATH`).
- **Tesseract:** Tesseract OCR ist optional und standardmäßig deaktiviert. Primäre OCR-Engine ist Ollama Vision. Zum Einschalten in `.env`: `TESSERACT_ENABLED=true`. Geplant: Weitere OCR-Engines (z.B. anderes Modell) konfigurierbar.

### Vorerst nicht verwendete Module

Folgende Module sind im Code vorhanden, werden aber aktuell nicht verwendet:
- `src/rotary_archiv/wikidata/` - Wikidata-Integration
- `src/rotary_archiv/core/triplestore.py` - Triple-Store Integration
- `src/rotary_archiv/api/triples.py` - Triple-Store API
- `src/rotary_archiv/api/wikidata.py` - Wikidata API
- `src/rotary_archiv/api/sparql.py` - SPARQL Endpoint

Diese Module können später wieder aktiviert werden.

### Geplante Erweiterungen (Ausblick)

Inhaltliche Erschließung der erkannten Texte: Personen, Orte, Ereignisse katalogisieren und verknüpfen; Anbindung an Triple Store und Wikidata; optional Karten-Ansicht für historische Orte sowie Foto-Sammlung mit Anbindung an Wikimedia Commons. Diese Erweiterungen werden als eigene Schicht auf dem OCR-Kern aufgesetzt, ohne den Kern unnötig zu vergrößern.

## Lizenz

Siehe [LICENSE](LICENSE) für Details.
