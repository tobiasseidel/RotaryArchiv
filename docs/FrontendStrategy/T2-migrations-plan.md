# T2-migrations-plan.md
> **Version:** 1.1 — 2026-05-02
> **Thread:** T2 Datenmodell-Audit
> **Input für:** T6 Coding (OpenCode), T3 Auth & Deployment
> **Abhängigkeiten:** T2-datenmodell-audit.md, T3 (für E-Mail-Verschlüsselung)
> **Änderungen v1.1:** P0 (Shared Package `rotary_core`) ergänzt; Architekturentscheidung
> Zwei-Backend-Option dokumentiert; Triplestore-Status als aktiv bestätigt.

---

## Architekturentscheidung (gefallen in T2)

**Schicht A und Schicht B erhalten getrennte FastAPI-Backends.**
Sie teilen sich dieselbe PostgreSQL-Datenbank und denselben Apache Fuseki-Triplestore,
aber **keinen Code-Prozess**.

Die gemeinsamen Datenmodell-Dateien (`models.py`, `triplestore.py`, `database.py`,
`config.py`) werden als **lokales Shared Package `rotary_core`** extrahiert.
Beide Backends importieren daraus. Schema-Hoheit (Alembic-Migrationen) liegt
ausschließlich bei Backend A.

```
rotary-archiv/
├── packages/
│   └── rotary_core/          ← eine einzige Quelle für Modelle + Triplestore
│       ├── models.py
│       ├── triplestore.py
│       ├── database.py
│       └── config.py
├── backend_a/                ← bestehend (Schicht A: OCR, Admin, Erschließung)
│   ├── pyproject.toml        ←  rotary_core @ ../../packages/rotary_core
│   └── src/rotary_archiv/
└── backend_b/                ← neu (Schicht B: Public Frontend API)
    ├── pyproject.toml        ←  rotary_core @ ../../packages/rotary_core
    └── src/rotary_public/
        └── api/
```

**Konsequenz für Drift-Risiko:** Null. Eine Modell-Änderung in `rotary_core/models.py`
wirkt sofort in beiden Backends. Alembic läuft nur in Backend A.

---

## Priorisierung: 5 Migrations-Phasen

| Phase | Inhalt | Wartet auf | Benötigt für |
|---|---|---|---|
| **P0 — Shared Package** | `rotary_core` extrahieren, Backend A umstellen | Nichts | Alles weitere |
| **P1 — Fundament** | Person-Tabelle + `is_public` auf Document + Index | P0 | V03, V04 |
| **P2 — Sichtbarkeit** | Place/Event-Tabellen + context_snippet + Triplestore-Datum | P1 | V02, V06, V07 |
| **P3 — Community** | Story + Correction-Tabellen | P0 + T3 (E-Mail-Verschlüsselung) | V08, V09, V10, V11 |
| **P4 — API Schicht B** | Alle neuen Endpoints in Backend B | P1, P2, P3 | Alle Views |

---

## Phase P0 — Shared Package (Priorität: KRITISCH, zuerst)

**Aufwand:** ~0,5 Tage. Kein Breaking Change für Schicht A.

### P0.1 — Verzeichnisstruktur anlegen

```bash
mkdir -p packages/rotary_core
touch packages/rotary_core/__init__.py
```

### P0.2 — Dateien verschieben (nicht kopieren)

```bash
# Aus src/rotary_archiv/core/ verschieben:
mv src/rotary_archiv/core/models.py       packages/rotary_core/models.py
mv src/rotary_archiv/core/database.py     packages/rotary_core/database.py
mv src/rotary_archiv/triplestore.py       packages/rotary_core/triplestore.py
# config.py: nur den datenmodell-relevanten Teil extrahieren
# (OCR-spezifische Settings bleiben in backend_a)
```

### P0.3 — `pyproject.toml` für rotary_core

```toml
[project]
name = "rotary-core"
version = "0.1.0"
dependencies = [
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "rdflib>=7.0",
    "httpx>=0.27",
]
```

### P0.4 — Backend A auf Import umstellen

```python
# Vorher: from src.rotary_archiv.core.models import Document
# Nachher:
from rotary_core.models import Document
from rotary_core.triplestore import get_triplestore
from rotary_core.database import Base, get_db
```

In `backend_a/pyproject.toml`:
```toml
dependencies = [
    "rotary-core @ file:../../packages/rotary_core",
    ...  # alle bisherigen deps
]
```

### P0.5 — Alembic bleibt in Backend A

`alembic/env.py` importiert `Base` weiterhin — jetzt aus `rotary_core.models`.
Backend B führt **keine** Migrationen durch. Es liest nur.

### P0.6 — Triplestore: Fuseki als Pflicht-Voraussetzung dokumentieren

Da Backend B und Backend A gleichzeitig auf den Triplestore zugreifen,
**muss Fuseki als gemeinsamer SPARQL-Endpunkt aktiv sein** — der Turtle-File-Singleton
funktioniert nur mit einem einzigen Prozess sicher. Wenn Fuseki noch nicht produktiv
ist, muss das vor P4 erledigt sein (→ T3 Deployment).

---

## Phase P1 — Fundament (Priorität: KRITISCH)

### P1.1 — Neue Tabelle `persons` in `rotary_core/models.py`

**Alembic-Migration (in Backend A):** `alembic revision --autogenerate -m "add_persons_table"`

```python
class PersonEpoch(str, Enum):
    THIRTIES = "30er"
    NINETIES = "90er"
    UNKNOWN  = "unknown"

class Person(Base):
    __tablename__ = "persons"

    id            = Column(Integer, primary_key=True, index=True)
    slug          = Column(String(255), nullable=False, unique=True, index=True)
    display_name  = Column(String(512), nullable=False)
    born_year     = Column(Integer, nullable=True)
    died_year     = Column(Integer, nullable=True)
    epoch         = Column(SQLEnum(PersonEpoch), nullable=False, default=PersonEpoch.UNKNOWN)
    wikidata_id   = Column(String(100), nullable=True, index=True)
    canonical_uri = Column(String(512), nullable=True, unique=True, index=True)
    # ^ migriert aus ErschliessungsBox.entity_uri (z.B. "rotary:Person_42")
    is_public     = Column(Boolean, nullable=False, default=False,
                           server_default="0", index=True)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime, server_default=func.now(),
                           onupdate=func.now(), nullable=False)
```

**Neue optionale Relationship auf ErschliessungsBox** (kein Breaking Change):
```python
person_id = Column(Integer, ForeignKey("persons.id"), nullable=True, index=True)
person    = relationship("Person", backref="mentions")
```

**Einmal-Datenmigrations-Skript:**
```python
# Alle eindeutigen entity_uri mit entity_type='person' aus ErschliessungsBox
# → in persons-Tabelle überführen (canonical_uri = entity_uri).
# Slug: python-slugify({display_name}-{born_year}), Kollision → Suffix -2, -3.
# Epoch: aus Document.date des ältesten verknüpften Dokuments ableiten.
```

**Slug-Stabilitätsregel:** Slug ist nach Erzeugung unveränderlich.
Namenskorrekturen gehen in `display_name`, niemals in `slug`.

---

### P1.2 — `is_public` auf `documents`

**Alembic-Migration:** `alembic revision -m "add_is_public_to_documents"`

```python
op.add_column("documents", sa.Column(
    "is_public", sa.Boolean(), nullable=False, server_default="0"
))
op.create_index("ix_documents_is_public", "documents", ["is_public"])
```

**Datenmigration:** `Document` mit `status = PUBLISHED` → `is_public = True`.
Alle Dokumente mit `date < 1940-01-01` → `is_public = True` als Batch-Default
(manuell bestätigbar durch Admin).

**Hinweis:** `DocumentStatus.PUBLISHED` und `is_public` koexistieren —
`PUBLISHED` beschreibt den OCR-Workflow, `is_public` die Frontend-Sichtbarkeit.

---

### P1.3 — Index auf `ErschliessungsBox.entity_uri`

**Alembic-Migration:** `alembic revision -m "add_index_erschliessungsbox_entity_uri"`

```python
op.create_index("ix_erschliessungsbox_entity_uri",
                "erschliessungs_boxes", ["entity_uri"])
op.create_index("ix_erschliessungsbox_entity_type_uri",
                "erschliessungs_boxes", ["entity_type", "entity_uri"])
```

Ohne diesen Index sind alle Zeitstrahl- und Netzwerk-Abfragen Full Table Scans.
Aufwand: 15 Minuten, null Risiko — **sollte sofort gemacht werden**.

---

## Phase P2 — Sichtbarkeit (Priorität: HOCH)

### P2.1 — Neue Tabelle `places`

```python
class Place(Base):
    __tablename__ = "places"
    id            = Column(Integer, primary_key=True, index=True)
    display_name  = Column(String(512), nullable=False)
    canonical_uri = Column(String(512), nullable=True, unique=True, index=True)
    wikidata_id   = Column(String(100), nullable=True)
    latitude      = Column(Float, nullable=True)
    longitude     = Column(Float, nullable=True)
    is_public     = Column(Boolean, nullable=False, default=True,
                           server_default="1", index=True)
    # Orte: standardmäßig öffentlich (per T1-Entscheidung)
    created_at    = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime, server_default=func.now(),
                           onupdate=func.now(), nullable=False)
```

Datenmigration: aus `ErschliessungsBox` (entity_type='place') + Triplestore
(`rotary:lat`, `rotary:lon` via `get_place_details()`) befüllen.

### P2.2 — Neue Tabelle `historical_events`

```python
class HistoricalEvent(Base):
    __tablename__ = "historical_events"
    id            = Column(Integer, primary_key=True, index=True)
    display_name  = Column(String(512), nullable=False)
    event_date    = Column(DateTime, nullable=True, index=True)
    epoch         = Column(SQLEnum(PersonEpoch), nullable=True)
    description   = Column(Text, nullable=True)
    is_public     = Column(Boolean, nullable=False, default=True,
                           server_default="1", index=True)
    created_at    = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime, server_default=func.now(),
                           onupdate=func.now(), nullable=False)
```

### P2.3 — `context_snippet` auf `ErschliessungsBox`

```python
context_snippet = Column(String(500), nullable=True)
# Befüllen: 200 Zeichen links + rechts der BBox aus ocr_text_final beim Erschließen.
# Ermöglicht Zeitstrahl-Snippets in V03 ohne weitere OCR-Lookups.
```

### P2.4 — Datum auf Triplestore-Mentions schreiben

In `rotary_core/triplestore.py`, Methode `add_mention()` erweitern:

```python
def add_mention(
    self,
    mention_uri: str,
    person_uri: str,
    belegt_in_uri: str,
    *,
    role: str | None = None,
    document_date: str | None = None,   # NEU: ISO-Datum des Quelldokuments
) -> None:
    self.add_triple(mention_uri, str(ROTARY["beziehtSichAuf"]), person_uri, "uri")
    self.add_triple(mention_uri, str(ROTARY["belegtIn"]), belegt_in_uri, "uri")
    if role:
        self.add_triple(mention_uri, str(ROTARY["rolle"]), role, "literal")
    if document_date:                   # NEU
        self.add_triple(mention_uri, str(ROTARY["date"]), document_date, "literal")
```

Dadurch wird die Zeitstrahl-Abfrage (V03) zu einem reinen SPARQL-Query
ohne SQL-Hybrid-Lookup.

**Bestehende Mentions ohne Datum:** Einmal-Nachlauf-Skript, das alle
`rotary:Mention_*`-Knoten im Graph durchläuft, die noch kein `rotary:date`-Triple
haben, und das Datum über `ErschliessungsBox → DocumentPage → Document.date` nachträgt.

---

## Phase P3 — Community (Priorität: HOCH, nach T3)

**Wartet auf:** T3 (Auth-Mechanismus + E-Mail-Verschlüsselungsverfahren)

### P3.1 — Neue Tabelle `stories`

```python
class ContributionStatus(str, Enum):
    DRAFT     = "draft"       # Entwurf (nur eingeloggte Nutzer)
    SUBMITTED = "submitted"   # In Moderationswarteschlange
    APPROVED  = "approved"    # Freigegeben — öffentlich sichtbar
    REJECTED  = "rejected"    # Abgelehnt

class Story(Base):
    __tablename__ = "stories"
    id                  = Column(Integer, primary_key=True, index=True)
    slug                = Column(String(255), nullable=False, unique=True, index=True)
    title               = Column(String(512), nullable=False)
    body                = Column(Text, nullable=False)
    author_name         = Column(String(255), nullable=True)   # NULL = "Anonym"
    author_email_enc    = Column(Text, nullable=True)          # Verfahren: T3
    status              = Column(SQLEnum(ContributionStatus), nullable=False,
                                 default=ContributionStatus.SUBMITTED, index=True)
    is_public           = Column(Boolean, nullable=False, default=False,
                                 server_default="0", index=True)
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id   = Column(Integer, nullable=True, index=True)
    submitted_by_user   = Column(Integer, nullable=True)       # FK → User (T3)
    reviewed_by_user    = Column(Integer, nullable=True)
    reviewed_at         = Column(DateTime, nullable=True)
    rejection_note      = Column(Text, nullable=True)
    created_at          = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime, server_default=func.now(),
                                 onupdate=func.now(), nullable=False)
```

### P3.2 — Neue Tabelle `corrections`

```python
class Correction(Base):
    __tablename__ = "corrections"
    id                  = Column(Integer, primary_key=True, index=True)
    related_entity_type = Column(String(50), nullable=False)
    related_entity_id   = Column(Integer, nullable=False, index=True)
    body                = Column(Text, nullable=False)
    author_name         = Column(String(255), nullable=True)
    author_email_enc    = Column(Text, nullable=True)          # Verfahren: T3
    status              = Column(SQLEnum(ContributionStatus), nullable=False,
                                 default=ContributionStatus.SUBMITTED, index=True)
    submitted_by_user   = Column(Integer, nullable=True)
    reviewed_by_user    = Column(Integer, nullable=True)
    reviewed_at         = Column(DateTime, nullable=True)
    rejection_note      = Column(Text, nullable=True)
    created_at          = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime, server_default=func.now(),
                                 onupdate=func.now(), nullable=False)
```

---

## Phase P4 — API Schicht B / Backend B (Priorität: HOCH, nach P1+P2)

Alle Endpoints entstehen in **`backend_b/src/rotary_public/api/`** —
vollständig getrennt von Backend A. Kein Refactoring der bestehenden `api/`-Dateien.

### API-Konventionen (Backend B)

1. **Auth-Header:** `Authorization: Bearer <token>` optional. Fehlt → anonymer Request.
2. **is_public-Filter:** Anonym → nur `is_public = True`. Mit Token → alle erlaubten Objekte.
3. **Stub-Response:** `is_public = False` + anonym → HTTP 200 mit `{"stub": true, ...}`,
   kein 403/404.
4. **Versionierung:** Prefix `/api/v1/` für alle Endpoints.
5. **Triplestore-Zugriff:** Ausschließlich via Fuseki (kein Turtle-File-Singleton).

### Endpoint-Liste

```
# Personen
GET  /api/v1/persons                        ?epoch=30er|90er&q=...
GET  /api/v1/persons/{slug}                 Profil + Stub-Fallback
GET  /api/v1/persons/{slug}/timeline        Zeitstrahl via SPARQL (rotary:date auf Mentions)
GET  /api/v1/persons/{slug}/network         Kookkurrenz via SPARQL

# Dokumente
GET  /api/v1/documents                      ?epoch=...&date_from=...&date_to=...&q=...
GET  /api/v1/documents/{id}                 Detail + Stub-Fallback
GET  /api/v1/documents/{id}/export/bibtex   BibTeX-String
GET  /api/v1/documents/{id}/export/citation Zitattext (Deutsch, APA-ähnlich)

# Suche
GET  /api/v1/search                         ?q=...&type=person|document|place|event&epoch=...

# Orte & Ereignisse
GET  /api/v1/places                         ?epoch=...  (mit lat/lon für Leaflet)
GET  /api/v1/events                         ?epoch=...&date_from=...&date_to=...

# Netzwerk-Graph
GET  /api/v1/network/graph                  ?epoch=...&min_connections=2
                                            → {nodes: [...], edges: [...]}

# Stories & Korrekturen
GET  /api/v1/stories                        ?status=approved&related_entity_type=...
GET  /api/v1/stories/{slug}
POST /api/v1/stories                        Anonym oder eingeloggt
POST /api/v1/corrections                    Anonym oder eingeloggt

# Startseite & Statistik
GET  /api/v1/stats                          {persons_public, documents_public, stories_approved}
GET  /api/v1/featured                       Hero-Block des Tages

# Admin-Moderation (nur authentifiziert — T3)
GET  /api/v1/admin/moderation-queue
POST /api/v1/admin/stories/{id}/approve
POST /api/v1/admin/stories/{id}/reject
POST /api/v1/admin/corrections/{id}/approve
POST /api/v1/admin/corrections/{id}/reject
```

### BibTeX-Export — Format

```bibtex
@misc{rotaryarchiv_{id},
  title   = {{{title}}},
  author  = {{Rotary Club Dresden}},
  year    = {{{year}}},
  note    = {{Sitzungsprotokoll vom {date}, erschlossen im RotaryArchiv}},
  url     = {{https://{domain}/dokument/{id}}},
  urldate = {{{today}}}
}
```

---

## Gesamtreihenfolge für T6 Coding

```
P0    rotary_core extrahieren          ~0,5 Tage   kein Breaking Change
P1.3  Index entity_uri                 15 Min       sofort, null Risiko
P1.2  is_public auf documents          30 Min       sofort, kein Breaking Change
P1.1  Person-Tabelle + Datenmigration  1–2 Tage
P2.1  Place-Tabelle                    0,5 Tage
P2.2  Event-Tabelle                    0,5 Tage
P2.3  context_snippet                  0,5 Tage
P2.4  Datum auf Triplestore-Mentions   1 Tag (inkl. Nachlauf-Skript)
P4    Backend B + alle Endpoints       3–5 Tage    nach P1 abgeschlossen
P3    Story/Correction-Tabellen        1–2 Tage    nach T3-Freigabe
```

**Für T5 Frontend/Design:** Die API-Response-Strukturen aus P4 sind ab P1
stabil beschrieben. T5 kann parallel mit Mock-Responses gegen das
obige API-Schema designen.

---

## Offene Entscheidungen (weiterleiten)

| Frage | Zuständig |
|---|---|
| Verschlüsselungsverfahren für `author_email_enc` (Fernet? asymmetrisch?) | T3 |
| Auth-Mechanismus — JWT, Session, API-Key? | T3 |
| Fuseki bereits produktiv aktiv oder noch zu konfigurieren? | T3 / T6 |
| `DocumentStatus.PUBLISHED` weiterführen oder durch `is_public` ablösen? | T6 |
| Kookkurrenz-Tabelle als Denormalisierung oder Live-SPARQL? (erst bei Performance-Bedarf) | T6 |
