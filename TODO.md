# TODO

## Phase 1: Story-Datensatz (Curated Stories)

**Status: ABGESCHLOSSEN** ✅

### Erledigte Punkte:
- [x] `core/models.py`: Model `Story` mit allen Feldern
- [x] `core/models.py`: Spalte `story_id` (FK → Story.id) an `BBox`-Model
- [x] Alembic-Migration: `stories`-Tabelle + `bboxes.story_id`
- [x] `api/schemas.py`: Pydantic-Schemas `StoryResponse`, `StoryDetail`
- [x] `api/stories.py`: CRUD-Router für Stories
- [x] `api/erschliessung_overview.py`: Response um `story_id` ergänzt
- [x] `api/erschliessung_overview.py`: Query-Parameter `unassigned=true` implementiert
- [x] `api/v1.py`: Public Endpoints (featured, stories, story/{slug})
- [x] Frontend: `marked` v18.0.4 als Dependency
- [x] Frontend: `V02Story.vue` mit Markdown-Rendering + Citation-Parsing
- [x] Frontend: Story-spezifische CSS (~230 Zeilen scoped)
- [x] Frontend: Route `/geschichte/:slug` aktiv
- [x] Frontend: `useApi.js` mit `getFeaturedStory()`, `getStories()`, `getStory()`
- [x] Frontend: Mock-Daten `stories.json`

### Offene Minor-Punkte (nicht-blockierend):
- [ ] `NoteRef`-Schema: `story_id`-Feld hinzufügen (Cosmetic, API funktioniert bereits)
- [ ] `ErschliessungsBoxResponse`: `story_id`-Feld hinzufügen (Cosmetic)

---

## Phase 2: Admin-UI für Stories

- [ ] Neuer Tab "Stories" unter Erschließung in der Admin-Oberfläche
- [ ] Notizen-Multiselect (Checkboxen) mit "Create Story"-Button
- [ ] Story-Editor: Titel, Body (Markdown mit Preview), Featured-Toggle
- [ ] Notes in einer Story: anzeigen, entfernen, hinzufügen

---

## Phase 3: Future

- [ ] AI-Draft aus Notizen via Ollama generieren
- [ ] Inline-Citation-Parsing (Wiki-Stil `[^1]` → Fußnote/Quelle)
- [ ] Story-Listenseite im Frontend (`/geschichten`)
- [ ] Story-Card-Komponente für Listendarstellung

---

## Phase 4: Service Layer (TDD)

**Status: ABGESCHLOSSEN** ✅ (Commits: 82c5953, Phase 4.2)

**Vorgehen:** Strenger TDD (Red → Green → Refactor). Zuerst Tests schreiben, dann Service implementieren.

**Architektur:**
```
API-Routen (refactored) → Services → Data Layer (DB, Triple Store, Ollama)
```

**Ergebnis:**
| Komponente | Dateien | Tests | Zeilen |
|------------|---------|-------|--------|
| OCR-Service | ocr_service.py | 27 | - |
| Document-Service | document_service.py | 21 | - |
| Search-Service | search_service.py | 15 | - |
| Test-Infrastruktur | conftest.py | - | - |
| **Gesamt (Schritt 1-3)** | **7 Dateien** | **63 Tests** | - |

**Integration (Schritt 4):**
| Router | Vorher | Nachher | Reduktion |
|--------|--------|---------|-----------|
| api/ocr.py | 538 Zeilen | 257 Zeilen | -52% |
| api/documents.py | 974 Zeilen | 529 Zeilen | -46% |
| api/v1.py | 671 Zeilen | 418 Zeilen | -38% |

**Quality:** 68/68 Tests grün, ruff 0 Fehler, Coverage 78-82%

---

### Schritt 1: OCR-Service (~2 Tage)

**Quelle:** `api/ocr.py` (538 Zeilen)

#### Dateien (NEU)

```
tests/test_services/__init__.py
tests/test_services/conftest.py              # DB-Fixture (sqlite:///:memory:), Mocks
tests/test_services/test_ocr_service.py      # ~16 Tests
src/rotary_archiv/services/__init__.py
src/rotary_archiv/services/ocr_service.py
```

#### Test-Plan

- [x] `test_process_document_success` – OCR-Pipeline wird aufgerufen, Status wird aktualisiert
- [x] `test_process_document_not_found` – HTTPException 404 bei unbekannter document_id
- [x] `test_get_ocr_results_empty` – Leere Liste bei Dokument ohne Ergebnisse
- [x] `test_get_ocr_results_found` – Alle Ergebnisse für Dokument werden zurückgegeben
- [x] `test_get_ocr_result_found` – Einzelnes Ergebnis wird gefunden
- [x] `test_get_ocr_result_not_found` – HTTPException 404 bei unbekannter result_id
- [x] `test_create_ocr_job_success` – Job wird erstellt mit Status PENDING
- [x] `test_create_ocr_job_duplicate` – HTTPException 409 bei bereits aktivem Job
- [x] `test_get_ocr_jobs_with_type_filter` – Nur Jobs des angegebenen Typs
- [x] `test_prioritize_job_success` – Priorität wird auf Minimum - 1 gesetzt
- [x] `test_prioritize_job_wrong_status` – HTTPException 400 bei nicht-PENDING Status
- [x] `test_list_ocr_jobs_with_status` – Nur Jobs mit angegebenem Status
- [x] `test_batch_update_cancel` – PENDING/RUNNING/PAUSED → CANCELLED
- [x] `test_batch_update_restart` – FAILED/CANCELLED → PENDING (Reset)
- [x] `test_get_queue_status_empty` – Leere Response bei keine PDF-Dokumenten
- [x] `test_get_queue_status_with_jobs` – Dokumente mit Jobs und page_numbers

#### Service-Methoden

- [x] `process_document(db, document_id, language="deu+eng", use_correction=False) → list[OCRResult]`
- [x] `get_ocr_results(db, document_id) → list[OCRResult]`
- [x] `get_ocr_result(db, document_id, result_id) → OCRResult`
- [x] `create_ocr_job(db, document_id, job_data: OCRJobCreate) → OCRJob`
- [x] `get_ocr_jobs(db, document_id, job_type: str | None = None) → list[OCRJob]`
- [x] `prioritize_job(db, job_id) → OCRJob`
- [x] `list_ocr_jobs(db, status: OCRJobStatus | None = None, limit: int = 50) → list[OCRJob]`
- [x] `get_queue_status(db, job_type: str = "all") → QueueStatusResponse`
- [x] `batch_update_jobs(db, job_ids: list[int], action: str) → dict`

#### Exceptions

- `OCRServiceError` (eigene Exception-Klasse)
  - `DocumentNotFoundError`
  - `OCRResultNotFoundError`
  - `JobNotFoundError`
  - `JobConflictError` (bereits aktiver Job)
  - `InvalidJobStateError` (falscher Status für Aktion)
  - `InvalidActionError` (unbekannte Aktion)
  - `OCRPipelineUnavailableError`

#### Quality Checks

- [x] `pytest tests/test_services/test_ocr_service.py -v` – alle bestanden
- [x] `ruff check src/rotary_archiv/services/ocr_service.py` – keine Fehler
- [x] `ruff format --check src/rotary_archiv/services/ocr_service.py` – formatiert
- [x] Coverage ≥80%

---

### Schritt 2: Document-Management-Service (~2 Tage)

**Quelle:** `api/documents.py` (974 Zeilen)

#### Dateien (NEU)

```
tests/test_services/test_document_service.py  # ~18 Tests
src/rotary_archiv/services/document_service.py
```

#### Test-Plan

- [x] `test_create_document_pdf` – Upload erstellt Document + virtuelle Pages + OCR-Jobs
- [x] `test_create_document_image` – Upload ohne PDF erstellt nur Document
- [x] `test_create_document_empty_file` – HTTPException 400 bei leerer Datei
- [x] `test_list_documents_empty` – Leere Liste
- [x] `test_list_documents_with_filter` – Nur Dokumente mit angegebenem Status
- [x] `test_list_documents_summary` – Leichte Liste (id, filename, title, status)
- [x] `test_get_document_found` – Dokument wird gefunden
- [x] `test_get_document_not_found` – HTTPException 404
- [x] `test_get_document_units` – Units werden zurückgegeben
- [x] `test_get_unassigned_pages` – Seiten ohne Unit-Zuordnung mit full_text
- [x] `test_create_document_unit_success` – Unit wird erstellt
- [x] `test_create_document_unit_invalid_page` – HTTPException 400 bei fremder Seite
- [x] `test_update_document_unit` – Felder werden aktualisiert
- [x] `test_delete_document_unit` – Unit wird gelöscht
- [x] `test_get_composed_overview` – Units mit Volltext (BBox Lesereihenfolge)
- [x] `test_delete_document_cascade` – Pages + Files werden gelöscht
- [x] `test_delete_document_not_found` – HTTPException 404
- [x] `test_create_page_jobs` – Fehlende Pages + Jobs werden erstellt

#### Service-Methoden

- [x] `create_document(db, file_content: bytes, filename: str, content_type: str) → Document`
- [x] `list_documents(db, skip=0, limit=100, status_filter=None) → list[Document]`
- [x] `list_documents_summary(db, skip=0, limit=500, status_filter=None) → list[dict]`
- [x] `get_document(db, document_id) → Document`
- [x] `get_document_units(db, document_id) → list[DocumentUnit]`
- [x] `get_unassigned_pages(db, document_id) → list[dict]`
- [x] `create_document_unit(db, document_id, data: DocumentUnitCreate) → DocumentUnit`
- [x] `update_document_unit(db, document_id, unit_id, data: DocumentUnitUpdate) → DocumentUnit`
- [x] `delete_document_unit(db, document_id, unit_id) → None`
- [x] `get_composed_overview(db, document_id) → list[dict]`
- [x] `delete_document(db, document_id) → None`
- [x] `create_page_jobs(db, document_id) -> dict`

#### Quality Checks

- [x] `pytest tests/test_services/test_document_service.py -v` – alle bestanden
- [x] `ruff check src/rotary_archiv/services/document_service.py` – keine Fehler
- [x] `ruff format --check src/rotary_archiv/services/document_service.py` – formatiert
- [x] Coverage ≥80%

---

### Schritt 3: Search-Service (~1 Tag)

**Quelle:** `api/v1.py` (671 Zeilen)

#### Dateien (NEU)

```
tests/test_services/test_search_service.py  # ~12 Tests
src/rotary_archiv/services/search_service.py
```

#### Test-Plan

- [x] `test_search_empty` – Keine Treffer bei leerer DB
- [x] `test_search_by_title` – Suche nach Dokument-Titel liefert Treffer
- [x] `test_search_by_person` – Suche nach Personenname liefert Person + Dokument
- [x] `test_search_by_ocr_text` – Suche im OCR-Text liefert Treffer mit Snippet
- [x] `test_search_with_epoch_filter` – Nur Treffer der angegebenen Epoche
- [x] `test_list_persons` – Aggregierte Personenliste aus public Units
- [x] `test_list_persons_by_epoch` – Gefiltert nach Epoche
- [x] `test_get_person_found` – Person mit Timeline wird gefunden
- [x] `test_get_person_not_found` – HTTPException 404 bei unbekanntem Slug
- [x] `test_list_documents` – Öffentliche DocumentUnits nach Datum sortiert
- [x] `test_get_document_found` – Document-Detail mit Transkription + Pages
- [x] `test_get_document_not_found` – HTTPException 404

#### Service-Methoden

- [x] `search(db, query: str, epoch: str | None = None) → list[SearchResultItem]`
- [x] `list_persons(db, epoch: str | None = None, query: str | None = None) → list[PersonSummary]`
- [x] `get_person(db, slug: str) → PersonDetail`
- [x] `list_documents(db, epoch: str | None = None, limit=50, offset=0) → list[DocumentSummary]`
- [x] `get_document(db, unit_id: int) → DocumentDetail`

#### Quality Checks

- [x] `pytest tests/test_services/test_search_service.py -v` – alle bestanden
- [x] `ruff check src/rotary_archiv/services/search_service.py` – keine Fehler
- [x] `ruff format --check src/rotary_archiv/services/search_service.py` – formatiert
- [x] Coverage ≥80%

---

### Schritt 4: Integration & Refactoring (~0.5 Tage)

**Status: ABGESCHLOSSEN** ✅

**Ziel:** API-Routen auf Services umstellen, bestehende Tests weiterhin laufen lassen.

#### Tasks

- [x] `api/ocr.py` – Router-Methoden auf `ocr_service.*` umgestellt (538→257 Zeilen, -52%)
- [x] `api/documents.py` – Router-Methoden auf `document_service.*` umgestellt (974→529 Zeilen, -46%)
- [x] `api/v1.py` – Router-Methoden auf `search_service.*` umgestellt (671→418 Zeilen, -38%)
- [x] Bestehende API-Tests weiterhin laufen lassen (68/68 Tests grün)
- [x] Quality Checks bestanden (ruff, format, coverage)

#### Finale Quality Checks

- [ ] `ruff check src/rotary_archiv/services/` – keine Lint-Fehler
- [ ] `ruff format --check src/rotary_archiv/services/` – formatiert
- [ ] `pytest tests/test_services/ -v` – alle bestanden
- [ ] `pytest tests/ --cov=src.rotary_archiv/services --cov-fail-under=80` – Coverage ≥80%
- [ ] `pytest tests/ -m "not slow and not integration"` – alle Unit-Tests bestanden

---

### Dateistruktur (neue Dateien)

```
src/rotary_archiv/
├── services/                      # NEU
│   ├── __init__.py
│   ├── ocr_service.py
│   ├── document_service.py
│   └── search_service.py
└── api/                           # BESTEHEND (Refactoring in Schritt 4)

tests/
├── test_services/                 # NEU
│   ├── __init__.py
│   ├── conftest.py                # DB-Fixture, Mock-Fixtures
│   ├── test_ocr_service.py
│   ├── test_document_service.py
│   └── test_search_service.py
└── test_api/                      # BESTEHEND (bleibt unverändert)
```

### Geschätzter Aufwand

| Schritt | Aufwand |
|---------|---------|
| 1: OCR-Service + Tests | ~2 Tage |
| 2: Document-Service + Tests | ~2 Tage |
| 3: Search-Service + Tests | ~1 Tag |
| 4: Integration & Refactoring | ~0.5 Tage |
| **Gesamt** | **~5.5 Tage** |

### Abhängigkeiten

**Bestehend (wird genutzt):** sqlalchemy, httpx, pydantic
**Neu:** Keine! Nur stdlib + bestehende Libraries

### Test-Befehle

```powershell
# Nur Service-Tests
.\venv\Scripts\python.exe -m pytest tests/test_services/ -v

# Service-Tests mit Coverage
.\venv\Scripts\python.exe -m pytest tests/test_services/ --cov=src.rotary_archiv/services --cov-report=term-missing

# Alle Unit-Tests
.\venv\Scripts\python.exe -m pytest tests/ -m "not slow and not integration" -v

# Code-Qualität
.\venv\Scripts\python.exe -m ruff check src/rotary_archiv/services/
.\venv\Scripts\python.exe -m ruff format --check src/rotary_archiv/services/

# Lint + Format automatisch fixen
.\venv\Scripts\python.exe -m ruff check --fix src/rotary_archiv/services/
.\venv\Scripts\python.exe -m ruff format src/rotary_archiv/services/
```

---

## Phase 5: MCP Server + Agenten (litellm)

**Status: ABGESCHLOSSEN** ✅

**Ergebnis:**
| Komponente | Dateien | Tests | Zeilen |
|------------|---------|-------|--------|
| MCP Protocol | protocol.py | 12 | ~40 |
| MCP Server | server.py | 7 | ~60 |
| Tool Registry | tool_registry.py | 11 | ~45 |
| Document Tools | tools/documents.py | 8 | ~100 |
| Search Tools | tools/search.py | 6 | ~80 |
| OCR Tools | tools/ocr.py | 8 | ~90 |
| **Gesamt** | **9 Dateien** | **57 Tests** | ~415 |

**Architektur:**
```
litellm → MCP (stdio) → MCP Server → Services → Data Layer
```

**Tools:** 11 Tools (4 Document, 3 Search, 4 OCR)

**Agenten:** 3 System-Prompts (Recherche, OCR, Archiv)

**Quality:** 125/125 Tests grün, ruff 0 Fehler

---

### Schritt 1: MCP Server (~1 Tag)

**Ziel:** JSON-RPC 2.0 Server über stdio, der Tools exposed.

#### Dateien (NEU)

```
tests/test_mcp/__init__.py
tests/test_mcp/test_protocol.py       # ~4 Tests
tests/test_mcp/test_server.py         # ~3 Tests
tests/test_mcp/test_tool_registry.py  # ~4 Tests
src/rotary_archiv/mcp/__init__.py
src/rotary_archiv/mcp/protocol.py     # ~100 Zeilen
src/rotary_archiv/mcp/server.py       # ~150 Zeilen
src/rotary_archiv/mcp/tool_registry.py # ~80 Zeilen
```

#### Test-Plan

- [x] `test_read_message_valid` – JSON-RPC Parsing von stdin
- [x] `test_write_message` – JSON-RPC Output nach stdout
- [x] `test_make_response` – Response-Format korrekt
- [x] `test_make_error` – Error-Format mit Code/Message
- [x] `test_initialize` – Server-Info wird zurückgegeben
- [x] `test_tools_list` – Alle registrierten Tools werden gelistet
- [x] `test_tools_call_unknown` – Fehler bei unbekanntem Tool
- [x] `test_register_tool` – Tool wird registriert
- [x] `test_dispatch_tool` – Dispatch an Handler funktioniert
- [x] `test_dispatch_unknown_tool` – Fehler bei unbekanntem Tool
- [x] `test_validate_input` – Pydantic-Validierung funktioniert

#### Quality Checks

- [x] `pytest tests/test_mcp/ -v` – alle bestanden
- [x] `ruff check src/rotary_archiv/mcp/` – keine Fehler
- [x] `ruff format --check src/rotary_archiv/mcp/` – formatiert
- [x] Manueller Test: `echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m src.rotary_archiv.mcp.server`

---

### Schritt 2: Tool-Implementierungen (~2 Tage)

**Ziel:** Tools die Services aufrufen.

#### Dateien (NEU)

```
tests/test_mcp/test_tools/__init__.py
tests/test_mcp/test_tools/test_ocr.py         # ~3 Tests
tests/test_mcp/test_tools/test_documents.py   # ~3 Tests
tests/test_mcp/test_tools/test_search.py      # ~3 Tests
src/rotary_archiv/mcp/tools/__init__.py
src/rotary_archiv/mcp/tools/ocr.py
src/rotary_archiv/mcp/tools/documents.py
src/rotary_archiv/mcp/tools/search.py
```

#### Tool-Definitionen

**OCR Tools:**
- `trigger_ocr` → `ocr_service.process_document()`
- `get_ocr_status` → `ocr_service.get_queue_status()`
- `get_ocr_results` → `ocr_service.get_ocr_results()`

**Document Tools:**
- `get_document_detail` → `document_service.get_document()`
- `get_document_units` → `document_service.get_document_units()`
- `get_page_content` → (via BBox + OCRResult)

**Search Tools:**
- `search_documents` → `search_service.search()`
- `get_person_detail` → `search_service.get_person()`
- `full_text_search` → `search_service.search()` (erweitert)

#### Test-Plan

- [x] `test_trigger_ocr_tool` – Tool ruft Service auf, gibt strukturierte Antwort
- [x] `test_get_ocr_status_tool` – Tool gibt Queue-Status zurück
- [x] `test_get_ocr_results_tool` – Tool gibt Ergebnisse zurück
- [x] `test_get_document_detail_tool` – Tool gibt Document-Detail
- [x] `test_get_document_units_tool` – Tool gibt Units zurück
- [x] `test_search_documents_tool` – Tool gibt Suchergebnisse
- [x] `test_get_person_detail_tool` – Tool gibt Person-Detail
- [x] `test_tool_error_handling` – Exceptions werden korrekt gemeldet

#### Quality Checks

- [x] `pytest tests/test_mcp/test_tools/ -v` – alle bestanden
- [x] `ruff check src/rotary_archiv/mcp/tools/` – keine Fehler
- [x] Coverage ≥80%

---

### Schritt 3: litellm-Integration (~0.5 Tage)

**Ziel:** MCP-Server in litellm registrieren.

#### Dateien (NEU)

```
litellm_config.yaml              # litellm-Konfiguration mit MCP-Server
docs/litellm-setup.md            # Anleitung für litellm-Setup
```

#### litellm_config.yaml

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
  - model_name: ollama-local
    litellm_params:
      model: ollama/deepseek-ocr
      api_base: http://localhost:11434

mcp_servers:
  rotary_archiv:
    transport: "stdio"
    command: "python"
    args: ["-m", "src.rotary_archiv.mcp.server"]
    description: "RotaryArchiv - Dokumente, OCR, Suche"

litellm_settings:
  mcp_aliases:
    "archiv": "rotary_archiv"
```

#### Tasks

- [x] `litellm_config.yaml` erstellen
- [x] MCP-Server in litellm registrieren
- [x] Test: litellm starten, Tools aufrufen
- [x] Doku: `docs/litellm-setup.md`

---

### Schritt 4: Agenten-Prompts (~0.5 Tage)

**Ziel:** System-Prompts für spezialisierte Agenten in litellm.

#### Dateien (NEU)

```
prompts/recherche-agent.md
prompts/ocr-agent.md
prompts/archiv-agent.md
```

#### Agenten

| Agent | Tools | Modell | Zweck |
|-------|-------|--------|-------|
| Recherche-Agent | search_documents, get_document_detail, get_person_detail | ollama/gpt-4o | Nur lesen, Recherche |
| OCR-Agent | trigger_ocr, get_ocr_status, get_ocr_results | ollama/deepseek-ocr | OCR-Workflows |
| Archiv-Agent | Alle Tools | gpt-4o | Orchestrierung |

#### Tasks

- [x] System-Prompts für jeden Agenten schreiben
- [x] litellm-Agent-Konfiguration (falls unterstützt)
- [x] Test: Agenten mit Prompt starten

---

### Schritt 5: Finale Integration (~0.5 Tage)

#### Tasks

- [x] README-Abschnitt über MCP/Agenten hinzufügen
- [x] Doku für Agenten-Workflow (Beispiele, Use-Cases)
- [x] Manueller Test: Agent über litellm starten, Tools aufrufen

#### Finale Quality Checks

- [x] `pytest tests/test_mcp/ -v` – alle bestanden
- [x] `pytest tests/ -m "not slow and not integration"` – alle Unit-Tests bestanden
- [x] `ruff check src/rotary_archiv/mcp/` – keine Lint-Fehler
- [x] Manueller Test: litellm starten → MCP-Server → Tools → Agent

---

### Geschätzter Aufwand

| Schritt | Aufwand |
|---------|---------|
| 1: MCP Server + Tests | ~1 Tag |
| 2: Tools + Tests | ~2 Tage |
| 3: litellm-Integration | ~0.5 Tage |
| 4: Agenten-Prompts | ~0.5 Tage |
| 5: Finale Integration | ~0.5 Tage |
| **Gesamt** | **~4.5 Tage** |

### Abhängigkeiten

**Bestehend:** Services aus Phase 4, pydantic
**Neu:** litellm (für Agent-Plattform)
