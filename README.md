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

### Quick Start für Entwickler

**Windows PowerShell (empfohlen):**
```powershell
# Falls Execution Policy Fehler auftreten, führe aus:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 1. Development-Dependencies installieren
.\dev.ps1 install-dev

# 2. Pre-commit Hooks installieren
.\dev.ps1 pre-commit-install

# 3. Server starten
.\dev.ps1 run
```

**Linux/Mac (mit Make):**
```bash
# 1. Development-Dependencies installieren
make install-dev

# 2. Pre-commit Hooks installieren
make pre-commit-install

# 3. Server starten
make run
```

**Manuell (alle Plattformen):**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

### Verfügbare Commands

**Windows PowerShell:**
```powershell
.\dev.ps1 help              # Zeige alle verfügbaren Commands
.\dev.ps1 install           # Installiere Production-Dependencies
.\dev.ps1 install-dev       # Installiere Development-Dependencies
.\dev.ps1 lint              # Führe Linting aus (Ruff)
.\dev.ps1 format            # Formatiere Code (Ruff)
.\dev.ps1 lint-fix          # Linting mit Auto-Fix
.\dev.ps1 test              # Führe Tests aus
.\dev.ps1 test-verbose      # Tests mit Verbose-Output
.\dev.ps1 coverage          # Führe Tests mit Coverage-Report aus
.\dev.ps1 run               # Starte FastAPI Server
.\dev.ps1 run-prod          # Starte Server (Production-Mode)
.\dev.ps1 migrate           # Führe Datenbank-Migrationen aus
.\dev.ps1 migrate-create "Beschreibung"  # Erstelle neue Migration
.\dev.ps1 clean             # Entferne temporäre Dateien
.\dev.ps1 pre-commit-install # Installiere Pre-commit Hooks
.\dev.ps1 pre-commit-run    # Führe Pre-commit Hooks aus
```

**Linux/Mac (Make):**
```bash
make help              # Zeige alle verfügbaren Commands
make install           # Installiere Production-Dependencies
make install-dev       # Installiere Development-Dependencies
make lint              # Führe Linting aus (Ruff)
make format            # Formatiere Code (Ruff)
make test              # Führe Tests aus
make coverage          # Führe Tests mit Coverage-Report aus
make run               # Starte FastAPI Server
make migrate           # Führe Datenbank-Migrationen aus
make clean             # Entferne temporäre Dateien
make pre-commit-install # Installiere Pre-commit Hooks
```

### Code-Qualität

**Linting & Formatting:**

Windows PowerShell:
```powershell
.\dev.ps1 lint              # Code prüfen
.\dev.ps1 format            # Code formatieren
.\dev.ps1 lint-fix          # Code prüfen und automatisch fixen
```

Linux/Mac:
```bash
make lint              # Code prüfen
make format            # Code formatieren
make lint-fix          # Code prüfen und automatisch fixen
```

Wir verwenden **Ruff** für Linting und Formatting (ersetzt Flake8 + Black + isort).

**Pre-commit Hooks:**
Pre-commit Hooks führen automatisch Checks vor jedem Commit aus:
- Ruff Linting (Python)
- Ruff Formatting (Python)
- PowerShell Syntax-Check (falls `.ps1` Dateien geändert wurden)
- PowerShell Script Analyzer (optional, falls PSScriptAnalyzer installiert)
- Trailing Whitespace entfernen
- YAML/JSON Validierung

**PowerShell-Skripte prüfen:**
Falls PSScriptAnalyzer installiert ist, werden PowerShell-Skripte zusätzlich analysiert:
```powershell
# Optional: PSScriptAnalyzer installieren (für erweiterte PowerShell-Checks)
Install-Module -Name PSScriptAnalyzer -Scope CurrentUser
```

### Testing

**Tests ausführen:**

Windows PowerShell:
```powershell
.\dev.ps1 test              # Alle Tests
.\dev.ps1 test-verbose      # Mit Verbose-Output
.\dev.ps1 coverage          # Mit Coverage-Report
```

Linux/Mac:
```bash
make test              # Alle Tests
make test-verbose      # Mit Verbose-Output
make coverage          # Mit Coverage-Report
```

**Coverage-Report ansehen:**
Nach `make coverage` öffne `htmlcov/index.html` im Browser.

### Datenbank-Migrationen

**Migration erstellen:**

Windows PowerShell:
```powershell
.\dev.ps1 migrate-create "Beschreibung der Änderung"
# Oder:
alembic revision --autogenerate -m "Beschreibung"
```

Linux/Mac:
```bash
make migrate-create MESSAGE="Beschreibung der Änderung"
# Oder:
alembic revision --autogenerate -m "Beschreibung"
```

**Migration ausführen:**

Windows PowerShell:
```powershell
.\dev.ps1 migrate
# Oder:
alembic upgrade head
```

Linux/Mac:
```bash
make migrate
# Oder:
alembic upgrade head
```

### Zugriff auf die Anwendung

Nach dem Start sind verfügbar:
- **Frontend**: http://localhost:8000/ (Upload-Interface)
- **API-Dokumentation (Swagger)**: http://localhost:8000/docs
- **Alternative API-Dokumentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Weitere Informationen

- **Code-Style**: Siehe [CONTRIBUTING.md](CONTRIBUTING.md)
- **Projekt-Management**: Siehe [TODO.md](TODO.md), [BACKLOG.md](BACKLOG.md), [WORKLOG.md](WORKLOG.md)
- **Changelog**: Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

Siehe [LICENSE](LICENSE) für Details.
