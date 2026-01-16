# Contributing zu RotaryArchiv

Vielen Dank für dein Interesse, zu RotaryArchiv beizutragen! 🎉

## Entwicklungssetup

### Voraussetzungen

- Python 3.11+
- Git
- (Optional) Make für einfachere Commands

### Installation

1. Repository klonen:
```bash
git clone <repository-url>
cd RotaryArchiv
```

2. Virtual Environment erstellen und aktivieren:
```bash
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate
```

3. Dependencies installieren:

**Windows PowerShell:**
```powershell
.\dev.ps1 install-dev
```

**Linux/Mac:**
```bash
make install-dev
```

**Oder manuell (alle Plattformen):**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Pre-commit Hooks installieren:

**Windows PowerShell:**
```powershell
.\dev.ps1 pre-commit-install
```

**Linux/Mac:**
```bash
make pre-commit-install
```

**Oder manuell:**
```bash
pre-commit install
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
make migrate

# Oder:
alembic upgrade head
```

## Code-Style

### Linting & Formatting

Wir verwenden **Ruff** für Linting und Formatting:

**Windows PowerShell:**
```powershell
.\dev.ps1 lint              # Linting
.\dev.ps1 format            # Formatting
.\dev.ps1 lint-fix          # Beides mit Auto-Fix
```

**Linux/Mac:**
```bash
make lint              # Linting
make format            # Formatting
make lint-fix          # Beides mit Auto-Fix
```

### Code-Konventionen

- **Type Hints**: Immer verwenden (Python 3.11+)
- **Docstrings**: Google-Style für Funktionen/Klassen
- **Line Length**: 100 Zeichen
- **Imports**: Sortiert mit isort (automatisch durch Ruff)
- **PEP 8**: Konformität wird durch Ruff geprüft

### Pre-commit Hooks

Pre-commit Hooks führen automatisch Checks aus:
- Ruff Linting (Python)
- Ruff Formatting (Python)
- PowerShell Syntax-Check (für `.ps1` Dateien)
- PowerShell Script Analyzer (optional, falls PSScriptAnalyzer installiert)
- Trailing Whitespace entfernen
- YAML/JSON Validierung

**PowerShell-Skripte:**
PowerShell-Skripte werden automatisch auf Syntax-Fehler geprüft. Für erweiterte Analyse kann PSScriptAnalyzer installiert werden:
```powershell
Install-Module -Name PSScriptAnalyzer -Scope CurrentUser
```

## Testing

### Tests ausführen

**Windows PowerShell:**
```powershell
.\dev.ps1 test              # Alle Tests
.\dev.ps1 test-verbose      # Mit Verbose-Output
.\dev.ps1 coverage          # Mit Coverage-Report
```

**Linux/Mac:**
```bash
make test              # Alle Tests
make test-verbose      # Mit Verbose-Output
make coverage          # Mit Coverage-Report
```

### Test-Struktur

- Tests befinden sich in `tests/`
- Test-Dateien beginnen mit `test_`
- Test-Funktionen beginnen mit `test_`
- Verwende pytest Markierungen: `@pytest.mark.slow`, `@pytest.mark.integration`, etc.

### Coverage

Wir streben eine Coverage von mindestens 50% an (aktuell), langfristig 80%+.

Coverage-Report ansehen:
```bash
make coverage
# Öffne htmlcov/index.html im Browser
```

## Git Workflow

### Commit-Messages

Verwende klare, beschreibende Commit-Messages:

```
Kurze Beschreibung (max. 50 Zeichen)

Detaillierte Beschreibung (optional):
- Was wurde geändert
- Warum wurde es geändert
- Relevante Issue-Nummern
```

Beispiele:
- `Fix: Dokumente werden nach Gruppierung nicht angezeigt`
- `Feature: Navigationsmenü mit Imports/Dokumente-Tabs`
- `Refactor: PDF-Splitter für bessere Fehlerbehandlung`

### Branches

- `main`: Stabile Version
- `develop`: Entwicklungs-Branch (optional)
- Feature-Branches: `feature/feature-name`
- Bugfix-Branches: `fix/bug-description`

### Pull Requests

1. Erstelle einen Branch von `main`
2. Mache deine Änderungen
3. Führe Tests aus: `make test`
4. Prüfe Code-Qualität: `make lint`
5. Formatiere Code: `make format`
6. Erstelle Pull Request mit klarer Beschreibung

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
├── docs/                 # Dokumentation
└── static/               # Frontend
```

## Häufige Tasks

### Server starten

**Windows PowerShell:**
```powershell
.\dev.ps1 run

# Oder:
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

**Linux/Mac:**
```bash
make run

# Oder:
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

### Datenbank-Migration erstellen

**Windows PowerShell:**
```powershell
.\dev.ps1 migrate-create "Beschreibung der Änderung"

# Oder:
alembic revision --autogenerate -m "Beschreibung"
alembic upgrade head
```

**Linux/Mac:**
```bash
make migrate-create MESSAGE="Beschreibung der Änderung"

# Oder:
alembic revision --autogenerate -m "Beschreibung"
alembic upgrade head
```

### Temporäre Dateien entfernen

**Windows PowerShell:**
```powershell
.\dev.ps1 clean
```

**Linux/Mac:**
```bash
make clean
```

## Fragen?

Bei Fragen oder Problemen:
- Erstelle ein Issue im Repository
- Kontaktiere die Maintainer

## Code of Conduct

- Sei respektvoll und konstruktiv
- Helfe anderen, wenn möglich
- Akzeptiere konstruktives Feedback

Vielen Dank für deinen Beitrag! 🙏
