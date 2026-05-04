# T2-datenmodell-audit.md
> **Version:** 1.0 — 2026-05-02  |  **Thread:** T2 Datenmodell-Audit
> **Input für:** T5 Frontend/Design, T6 Coding, T3 Auth & Deployment
> **Basis:** models.py, triplestore.py, project-brief.md v0.2, T1-informationsarchitektur.md v1.1

---

## Vorbemerkung: Was das Modell heute ist

Das bestehende System besteht aus 10 SQLAlchemy-Klassen, die ausschließlich
Schicht A (OCR-Erschließung, Admin) bedienen:

| Modell | Zweck |
|---|---|
| `Document` | Hauptdokument, OCR-Workflow-Status |
| `DocumentPage` | Einzelseiten |
| `ErschliessungsBox` | Triplestore-Brücke: entity-Boxen + beleg-Boxen (S/P/O) |
| `OCRResult` | OCR-Ergebnisse pro Quelle |
| `BBox` | Bounding Boxes mit Review-Status |
| `OCRJob` | Asynchrone Job-Queue |
| `DocumentUnit` | Inhaltliche Einheit mit persons/place als JSON |
| `DocumentUnitSuggestion` | KI-Vorschlag für Unit-Grenzen |
| `CachedImage` | Bild-Cache-Metadaten |
| `AppSetting` | Globale Key-Value-Einstellungen |

Der Triplestore (`triplestore.py`) ist ein vollwertiges RDF-System
(rdflib + optionaler Apache Fuseki) mit echtem SPARQL-Interface.
Er ist aktiv in Verwendung (NOTE-Kommentar in Zeile 4 ist veraltet).
Personen, Orte und Ereignisse leben als URI-Ressourcen im RDF-Graph.

---

## Prüfpunkt 1 — is_public-Flag

| Entität | Eigene Tabelle? | is_public vorhanden? | Bewertung |
|---|---|---|---|
| Document | ✅ | ❌ | ⚠️ ADD COLUMN möglich |
| Person | ❌ nur URI-String | ❌ | ❌ Neu bauen |
| Story | ❌ nicht existent | ❌ | ❌ Neu bauen |
| Ort | ❌ nur URI-String | ❌ | ❌ Neu bauen |
| Ereignis | ❌ nur String in DocumentUnit | ❌ | ❌ Neu bauen |

Sonderfall: `DocumentStatus.PUBLISHED` ersetzt is_public nicht —
es beschreibt den OCR-Workflow, nicht die Frontend-Sichtbarkeit.
Beide müssen koexistieren.

---

## Prüfpunkt 2 — Slugs für Personen

❌ Kein Person-Modell, kein Slug-Feld.

Personen existieren nur als:
- `ErschliessungsBox.entity_uri` — URI-String (z.B. `rotary:Person_42`)
- `ErschliessungsBox.name` — nicht normierter Suchbegriff
- `DocumentUnit.persons` — JSON-Array `[{"name": "...", "role": "..."}]`

Strategie: Neue Tabelle `persons` mit `slug VARCHAR(255) UNIQUE`,
generiert als `{vorname}-{nachname}-{geburtsjahr}` via python-slugify.
Slug ist nach Erzeugung unveränderlich. Korrekturen gehen in `display_name`.

---

## Prüfpunkt 3 — Beitragsstatus-Enum

❌ Weder Story- noch Correction-Modell vorhanden.

`api/review.py` betrifft BBox-OCR-Review (intern), nicht Community-Beiträge.
`BBox.review_status` ist ein OCR-Workflow-Feld — nicht wiederverwendbar.

Erforderlich: zwei neue Tabellen `stories` und `corrections` mit Enum
`ContributionStatus: draft | submitted | approved | rejected`.

---

## Prüfpunkt 4 — Triplestore-Abfragen

### Datenstruktur (aktiv in Verwendung)

| Prädikat | Bedeutung |
|---|---|
| `rotary:name` | Anzeigename der Entität |
| `rotary:sameAs` | Wikidata-URI |
| `wdt:P569` etc. | Wikidata-Claims (Geburtsdatum, Ämter …) |
| `rotary:lat` / `rotary:lon` | Koordinaten für Orte |
| `rotary:beziehtSichAuf` | Mention → Entität |
| `rotary:belegtIn` | Mention → Quelle (ErschliessungsBox) |
| `rotary:rolle` | Rolle in einer Erwähnung |
| `rotary:statementSubject/Predicate/Object` | Reifizierte Aussagen |
| `rotary:erwaehnt` | Altes Modell — deprecated, koexistiert noch |

### (a) Netzwerk-Abfrage ⚠️

```sparql
SELECT DISTINCT ?coPersonUri ?coName WHERE {
  ?mention1 rotary:beziehtSichAuf <PERSON_URI> .
  ?mention1 rotary:belegtIn ?box .
  ?mention2 rotary:belegtIn ?box .
  ?mention2 rotary:beziehtSichAuf ?coPersonUri .
  ?coPersonUri rotary:name ?coName .
  FILTER (?coPersonUri != <PERSON_URI>)
}
```

Möglich, aber belegtIn zeigt auf ErschliessungsBox (Seiten-Ebene),
nicht auf Dokument-Ebene. Zwei Personen auf verschiedenen Seiten
desselben Dokuments werden nicht verbunden. Lösung: `rotary:document`
als zusätzliches Triple auf Mention-Knoten, oder Hybrid SQL+SPARQL.

### (b) Zeitstrahl-Abfrage ⚠️

Datum fehlt auf Mention-Knoten. Es muss über
`ErschliessungsBox → DocumentPage → Document.date` per SQL nachgeladen
werden (Hybrid-Ansatz). Lösung: `rotary:date` beim Anlegen einer Mention
als Literal mitspeichern + Einmal-Nachlauf für bestehende Mentions.

### Fehlende Indizes (kritisch)

- `ErschliessungsBox.entity_uri` — kein Index → Full Table Scan
- Compound Index `(entity_type, entity_uri)` fehlt

---

## Prüfpunkt 5 — API-Endpoints

Alle 7 bestehenden Module sind Schicht-A-intern (Admin/OCR).
Null Endpoints für Schicht B vorhanden.

### Fehlende Endpoints (Auswahl)

| Endpoint | View | Bewertung |
|---|---|---|
| `GET /api/v1/persons/{slug}` | V03 | ❌ Neu |
| `GET /api/v1/persons/{slug}/timeline` | V03 | ❌ Neu |
| `GET /api/v1/persons/{slug}/network` | V07 | ❌ Neu |
| `GET /api/v1/documents/{id}/export/bibtex` | V04 | ❌ Neu |
| `GET /api/v1/search` | V05 | ❌ Neu |
| `GET /api/v1/network/graph` | V07 | ❌ Neu |
| `POST /api/v1/stories` | V09 | ❌ Neu |
| `POST /api/v1/corrections` | V10 | ❌ Neu |

Gesamt: 17+ neue Endpoints erforderlich.

Stub-Response-Konvention für alle Schicht-B-Endpoints:
nicht-öffentliche Objekte → HTTP 200 `{"stub": true, ...}`, kein 403/404.

---

## Gesamtbewertung

| Prüfpunkt | Bewertung | Aufwand |
|---|---|---|
| is_public-Flag | ❌/⚠️ | Hoch (neue Tabellen) |
| Slugs für Personen | ❌ | Mittel |
| Beitragsstatus-Enum | ❌ | Mittel |
| Triplestore-Abfragen | ⚠️ | Mittel (Erweiterungen) |
| API Schicht B | ❌ | Hoch (komplett neu) |

Kernbefund: Das Modell ist ein exzellentes OCR-Werkzeug, aber kein
Wissensgraph-Backend. Für Schicht B fehlt die gesamte Entitätsschicht
sowie alle öffentlichen API-Endpoints. Die Migration ist umfangreich,
aber ohne Breaking Changes für Schicht A durchführbar.
