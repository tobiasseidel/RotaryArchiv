# Planungs-Unterhaltung: RotaryArchiv Projekt

Datum: Initiale Projektplanung
Teilnehmer: User & AI Assistant

## Situationsbeschreibung

Der Nutzer hat eine Sammlung an Unterlagen eines Rotary Clubs:
- **Zentral**: Meeting-Protokolle
- **Zusätzlich**: Fotos, Einladungen, Mitgliederlisten, Finanzberichte
- **Status**: Dokumente sind größtenteils eingescannt, aber Inhalt ist nicht erkannt und klassifiziert
- **Ziel**: Archiv aufarbeiten, zugänglich machen, Informationen findbar machen, Basis für Geschichtsaufarbeitung

## Projektziele

### Kernfunktionen des Tools:
1. **Sortieren** - Dokumente organisieren
2. **Klassifizieren** - Dokumente kategorisieren
3. **Indexieren** - Durchsuchbar machen
4. **Recherchieren** - Informationen finden
5. **Lesen** - Dokumente anzeigen
6. **Anmerken** - Annotationen hinzufügen
7. **Verknüpfen** - Beziehungen zwischen Dokumenten/Entitäten

### Outputs:
- Statische Website
- Broschüre
- Citizen-Science Projekt (langfristige Vision)
- Podcast/ähnliche Publikation (z.B. "100 Jahre später quasi-live nacherzählt")

## Architektur-Entscheidungen

### Datenmodell: Triple-Struktur (RDF)

**Entscheidung**: Hybrid-Ansatz mit PostgreSQL + Triple Store

**Vorteile**:
- Flexibilität: Neue Relationen ohne Schema-Änderung
- Wikidata-Kompatibilität: Direkte Anbindung möglich
- Semantische Suche: Graph-basierte Abfragen
- Erweiterbarkeit: Neue Entitäten einfach hinzufügbar

**Struktur**:
- **PostgreSQL**: Dokumente, OCR-Text, Metadaten, Datei-Pfade
- **Triple Store (RDF)**: Alle Relationen als Subjekt-Prädikat-Objekt

### Technologie-Stack

**Backend**:
- Python 3.11+
- FastAPI (REST API + SPARQL Endpoint)
- PostgreSQL 15+ (Dokumente, Metadaten)
- Apache Jena/Fuseki (Docker) für Triple Store
- Alembic für Datenbank-Migrationen

**OCR-Pipeline**:
- **Parallel**: Tesseract UND Ollama Vision gleichzeitig
- **Vergleich**: Ergebnisse vergleichen/kombinieren
- **Korrektur**: Ollama GPT zur Fehlersuche
- **Annotation-Support**: Ollama GPT für Annotation-Suche

**NLP & Entity Extraction**:
- spaCy für Named Entity Recognition
- Halb-automatische Vorschläge mit Multi-Select

**Wikidata-Integration**:
- Automatische Suche bei neuen Entitäten
- Verknüpfung mit Wikidata-Objekten
- Import relevanter Informationen
- **Wichtig**: Keine automatischen Pushes ohne Bestätigung

### Entitäten-Typen

1. **Personen**
2. **Orte**
3. **Organisationen** (Rotary Clubs etc.)
4. **Themen**
5. **Treffen/Events** (Arten von Treffen)
6. **Vortragsthemen und Vortragende**
7. **Zeitgeschehen** (Informationen aus dem Tagesgeschehen)
8. **Stadtgeschichte**

### Workflow

**Status-basiert** (später evtl. fluider):
1. `uploaded` - Dokument hochgeladen
2. `ocr_pending` - OCR wartet
3. `ocr_done` - OCR abgeschlossen
4. `classified` - Klassifiziert
5. `annotated` - Annotiert
6. `published` - Veröffentlicht (später evtl. nicht klar von annotated getrennt)

**Prozess**:
- Jedes Dokument kann individuell durchlaufen
- Flexibler Workflow pro Dokument

### API-Design

**Hybrid-Ansatz**:
- **REST API** für CRUD-Operationen
- **SPARQL Endpoint** für komplexe Graph-Queries

**Endpoints**:
- `/api/documents` - Dokumente verwalten
- `/api/entities` - Entitäten verwalten
- `/api/triples` - Triples verwalten
- `/api/search` - Volltextsuche
- `/sparql` - SPARQL Queries

### Datei-Storage

- **Dateisystem**: `data/documents/` (nicht in Git)
- Metadaten in PostgreSQL
- Binärdaten bleiben im Filesystem

### Authentifizierung

- **Phase 1**: Keine Auth (User ist Hauptnutzer)
- **Später**: Einfache Auth für ausgewählte Nutzer
- **Langfristig**: Möglicherweise mehr Nutzer

### Konfiguration

- Minimal: Technische Einstellungen (Adresse, Port, Database)
- `.env` für Environment-Variablen
- `config.yaml` optional für komplexere Einstellungen

## Projekt-Struktur

```
RotaryArchiv/
├── .cursorrules              # Cursor AI Regeln
├── .env.example              # Config-Template
├── .gitignore
├── README.md                 # Projekt-Dokumentation
├── requirements.txt          # Python Dependencies
├── docker-compose.yml        # PostgreSQL + Fuseki
├── alembic.ini               # DB Migration Config
│
├── src/
│   └── rotary_archiv/
│       ├── __init__.py
│       ├── main.py           # FastAPI App
│       ├── config.py          # Configuration
│       │
│       ├── api/               # API Endpoints
│       │   ├── __init__.py
│       │   ├── documents.py
│       │   ├── entities.py
│       │   ├── triples.py
│       │   ├── search.py
│       │   └── wikidata.py
│       │
│       ├── core/              # Core Business Logic
│       │   ├── __init__.py
│       │   ├── models.py      # SQLAlchemy Models
│       │   ├── triplestore.py # Triple Store Interface
│       │   └── workflow.py    # Document Workflow
│       │
│       ├── ocr/               # OCR Pipeline
│       │   ├── __init__.py
│       │   ├── tesseract.py
│       │   ├── ollama_vision.py
│       │   ├── ollama_gpt.py
│       │   └── pipeline.py
│       │
│       ├── nlp/               # NLP & Entity Extraction
│       │   ├── __init__.py
│       │   ├── ner.py         # Named Entity Recognition
│       │   └── classification.py
│       │
│       ├── wikidata/          # Wikidata Integration
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── matcher.py
│       │
│       └── utils/
│           ├── __init__.py
│           └── file_handler.py
│
├── tests/
│   ├── __init__.py
│   ├── test_api/
│   ├── test_ocr/
│   └── test_wikidata/
│
├── alembic/                   # DB Migrations
│   └── versions/
│
├── data/                      # Dokumente (nicht in Git)
│   └── documents/
│
└── docs/                      # Dokumentation
    └── architecture.md
```

## Wichtige Entscheidungen

### Fuseki Setup
- **Entscheidung**: Docker (einfach genug)
- Alternative: RDFLib für Start, später Migration zu Fuseki

### OCR-Engines
- **Implementierung**: Mehrere OCR-Engines, am Objekt ausprobieren
- **Workflow**: Tesseract ODER Ollama Vision für ersten Schritt (parallel möglich)
- Dann: Ollama GPT zur Fehlersuche und Annotation-Support

### Wikidata-Workflow
1. Bei Identifikation von Personen/Orten/etc.: Prüfen ob internes Objekt existiert
2. Wenn nicht: Neues internes Objekt anlegen
3. Bei neuen Objekten: Wikidata-Suche
4. Wenn gefunden: Verknüpfen und relevante Informationen importieren
5. **Wichtig**: Nur Vorschläge, User muss bestätigen

### Testing & Quality
- pytest für Tests
- .cursorrules für effektiveres KI-Programmieren mit Cursor

## Nächste Schritte

1. ✅ Projekt-Struktur erstellt
2. ✅ Basis-Konfigurationsdateien erstellt
3. ⏭️ Code-Struktur implementieren
4. ⏭️ OCR-Pipeline implementieren
5. ⏭️ Triple-Store Integration
6. ⏭️ Wikidata-Integration
7. ⏭️ API-Endpoints implementieren

## Offene Fragen / Später zu klären

- Welche OCR-Engine performt am besten? (wird durch Tests geklärt)
- Wie genau soll der Export für statische Websites aussehen?
- Citizen-Science Features (langfristig)
- Podcast/Storytelling-Features (langfristig)
