# Start-Prompt: Phase 4 Schritt 4 - Integration & Refactoring

Du arbeitest am **RotaryArchiv** Projekt. Phase 4 Schritt 1-3 sind abgeschlossen:

- ✅ OCR-Service (`services/ocr_service.py`) mit 27 Tests
- ✅ Document-Service (`services/document_service.py`) mit 21 Tests
- ✅ Search-Service (`services/search_service.py`) mit 15 Tests

## Deine Aufgabe

Stelle die API-Routen auf die neuen Services um. Die API-Routen enthalten aktuell noch die eigene Logik und sollen nur noch die Services aufrufen.

## Wichtige Dateien

| Datei | Aktueller Stand | Ziel |
|-------|-----------------|------|
| `src/rotary_archiv/api/ocr.py` | Eigene Logik (538 Zeilen) | Nutzt `ocr_service.*` |
| `src/rotary_archiv/api/documents.py` | Eigene Logik (974 Zeilen) | Nutzt `document_service.*` |
| `src/rotary_archiv/api/v1.py` | Eigene Logik (671 Zeilen) | Nutzt `search_service.*` |
| `src/rotary_archiv/services/ocr_service.py` | Fertig | Wird aufgerufen |
| `src/rotary_archiv/services/document_service.py` | Fertig | Wird aufgerufen |
| `src/rotary_archiv/services/search_service.py` | Fertig | Wird aufgerufen |

## Vorgehen

### 1. OCR-Router umstellen (`api/ocr.py`)

**Vorher:**
```python
@router.get("/documents/{document_id}/results", response_model=list[OCRResultResponse])
def get_ocr_results(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    ocr_results = db.query(OCRResult).filter(OCRResult.document_id == document_id).all()
    return [OCRResultResponse.model_validate(r) for r in ocr_results]
```

**Nachher:**
```python
from src.rotary_archiv.services import ocr_service
from src.rotary_archiv.services.ocr_service import DocumentNotFoundError

@router.get("/documents/{document_id}/results", response_model=list[OCRResultResponse])
def get_ocr_results(document_id: int, db: Session = Depends(get_db)):
    try:
        results = ocr_service.get_ocr_results(db, document_id)
        return [OCRResultResponse.model_validate(r) for r in results]
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
```

### 2. Exception-Mapping

Die Services werfen eigene Exceptions. Diese müssen in HTTPExceptions umgewandelt werden:

```python
from src.rotary_archiv.services.ocr_service import (
    DocumentNotFoundError,
    OCRResultNotFoundError,
    JobNotFoundError,
    JobConflictError,
    InvalidJobStateError,
    InvalidActionError,
)

# In jedem Endpoint:
try:
    result = ocr_service.some_method(db, ...)
    return ...
except DocumentNotFoundError:
    raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
except JobNotFoundError:
    raise HTTPException(status_code=404, detail="Job nicht gefunden")
except JobConflictError as e:
    raise HTTPException(status_code=409, detail=str(e))
except InvalidJobStateError as e:
    raise HTTPException(status_code=400, detail=str(e))
except InvalidActionError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### 3. Bestehende Tests prüfen

Nach jedem Router-Refactoring:
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_api/ -v
.\venv\Scripts\python.exe -m pytest tests/test_services/ -v
```

## Exception-Hierarchie (zur Erinnerung)

```python
# ocr_service.py
class OCRServiceError(Exception): ...
class DocumentNotFoundError(OCRServiceError): ...
class OCRResultNotFoundError(OCRServiceError): ...
class JobNotFoundError(OCRServiceError): ...
class JobConflictError(OCRServiceError): ...
class InvalidJobStateError(OCRServiceError): ...
class InvalidActionError(OCRServiceError): ...

# document_service.py
class DocumentServiceError(Exception): ...
class DocumentNotFoundError(DocumentServiceError): ...
class InvalidPageError(DocumentServiceError): ...

# search_service.py
class SearchServiceError(Exception): ...
class PersonNotFoundError(SearchServiceError): ...
class DocumentNotFoundError(SearchServiceError): ...
```

## Quality Checks (nach jedem Router)

```powershell
# API-Tests
.\venv\Scripts\python.exe -m pytest tests/test_api/ -v

# Service-Tests (dürften nicht kaputt gehen)
.\venv\Scripts\python.exe -m pytest tests/test_services/ -v

# Lint
.\venv\Scripts\python.exe -m ruff check src/rotary_archiv/api/
.\venv\Scripts\python.exe -m ruff format --check src/rotary_archiv/api/
```

## Finale Quality Checks

```powershell
# Alle Tests
.\venv\Scripts\python.exe -m pytest tests/ -m "not slow and not integration" -v

# Coverage
.\venv\Scripts\python.exe -m pytest tests/ --cov=src.rotary_archiv --cov-report=term-missing

# Lint + Format
.\venv\Scripts\python.exe -m ruff check src/rotary_archiv/
.\venv\Scripts\python.exe -m ruff format --check src/rotary_archiv/
```

## Commit

Nach Abschluss:
```bash
git add -A
git commit -m "refactor(api): use services in ocr/documents/v1 routers"
```
