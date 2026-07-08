# Start-Prompt: Phase 4 Service Layer (TDD)

Du arbeitest am **RotaryArchiv** Projekt – einem digitalen Archiv-System für Rotary Club Dokumente mit OCR-Verarbeitung.

## Deine Aufgabe

Implementiere die ersten 3 Services mit strengem TDD-Ansatz (Red → Green → Refactor) in dieser Reihenfolge:

1. **OCR-Service** – OCR-Job-Management, Pipeline-Steuerung, Queue-Status
2. **Document-Management-Service** – Upload, CRUD, Units, composed-overview
3. **Search-Service** – Volltextsuche, Personen-Aggregation, Document-Detail

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `TODO.md` | Detaillierter Plan mit allen Tests und Service-Methoden |
| `src/rotary_archiv/api/ocr.py` | Quell-Logik für OCR-Service (538 Zeilen) |
| `src/rotary_archiv/api/documents.py` | Quell-Logik für Document-Service (974 Zeilen) |
| `src/rotary_archiv/api/v1.py` | Quell-Logik für Search-Service (671 Zeilen) |
| `src/rotary_archiv/core/models.py` | Datenbank-Models (Document, OCRJob, OCRResult, DocumentUnit, etc.) |
| `src/rotary_archiv/core/database.py` | DB-Setup und `get_db()` Dependency |
| `tests/test_api/test_documents.py` | Beispiel für bestehende API-Tests |

## Vorgehen (pro Schritt)

### 1. Test-Infrastruktur aufbauen
```bash
# Neue Dateien erstellen:
tests/test_services/__init__.py
tests/test_services/conftest.py    # DB-Fixture (sqlite:///:memory:), Mock-Fixtures
```

### 2. TDD-Zyklus (pro Service)
1. **Red**: Alle Tests aus TODO.md schreiben → `pytest tests/test_services/test_X_service.py -v` → alle schlagen fehl
2. **Green**: Service implementieren → Tests werden grün
3. **Refactor**: Code refactorn, Typ-Hints, Docstrings → Tests bleiben grün

### 3. Quality Checks (nach jedem Service)
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_services/ -v
.\venv\Scripts\python.exe -m ruff check src/rotary_archiv/services/
.\venv\Scripts\python.exe -m ruff format --check src/rotary_archiv/services/
.\venv\Scripts\python.exe -m pytest tests/test_services/ --cov=src.rotary_archiv/services --cov-fail-under=80
```

## Service-Design

Jede Service-Funktion:
- Nimmt `db: Session` als ersten Parameter
- Wirft eigene Exceptions (z.B. `DocumentNotFoundError`)
- Gibt strukturierte Daten zurück (Model-Instanzen oder dicts)
- **Kein** HTTPException-Wurf – das bleibt in den API-Routen

```python
# Beispiel: OCR-Service Signatur
from sqlalchemy.orm import Session
from src.rotary_archiv.core.models import OCRJob, OCRResult

class OCRServiceError(Exception):
    """Basis-Exception für OCR-Service."""
    pass

class DocumentNotFoundError(OCRServiceError):
    def __init__(self, document_id: int):
        self.document_id = document_id
        super().__init__(f"Dokument {document_id} nicht gefunden")

def get_ocr_results(db: Session, document_id: int) -> list[OCRResult]:
    """Hole alle OCR-Ergebnisse für ein Dokument."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise DocumentNotFoundError(document_id)
    return db.query(OCRResult).filter(OCRResult.document_id == document_id).all()
```

## Exception-Hierarchie

```python
class OCRServiceError(Exception): ...
class DocumentNotFoundError(OCRServiceError): ...
class OCRResultNotFoundError(OCRServiceError): ...
class JobNotFoundError(OCRServiceError): ...
class JobConflictError(OCRServiceError): ...
class InvalidJobStateError(OCRServiceError): ...
class InvalidActionError(OCRServiceError): ...

class DocumentServiceError(Exception): ...
class DocumentNotFoundError(DocumentServiceError): ...
class InvalidPageError(DocumentServiceError): ...

class SearchServiceError(Exception): ...
class PersonNotFoundError(SearchServiceError): ...
class DocumentNotFoundError(SearchServiceError): ...
```

## DB-Fixture (conftest.py)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.rotary_archiv.core.models import Base

@pytest.fixture(scope="function")
def db_session():
    """In-Memory SQLite DB für jeden Test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

## Commits

Nach jedem abgeschlossenen Schritt (Service + Tests grün + Quality Checks bestanden):
```bash
git add -A
git commit -m "feat(services): add [ocr/document/search]_service with TDD tests"
```
