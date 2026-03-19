# Erschließungsschicht

## Zweck

Inhaltliche Erschließung der erkannten Texte: Personen, Orte, Ereignisse und Themen katalogisieren und verknüpfen. Anbindung an Triple Store, Wikidata, optional Karten-Ansicht und Foto-Sammlung (Wikimedia Commons). Die Erschließung baut auf dem OCR-Kern auf (Dokumente, Seiten, DocumentUnits, OCR-Ergebnisse) und erweitert sie um eine semantische Schicht.

## Struktur im Code

- **`src/rotary_archiv/content/`** – Paket der Erschließungsschicht (Entitäten-Typen, geplant: Entitäten-Katalog, Anbindung Triple Store).
- **`src/rotary_archiv/core/triplestore.py`** – Interface für den Triple Store (RDF/Fuseki).
- **Bestehende, vorerst nicht eingebundene API-Module:** `api/triples.py`, `api/wikidata.py`, `api/sparql.py` (können bei Bedarf in `main.py` aktiviert werden).

Die bestehenden Hilfsmethoden in `triplestore.py` (`get_document_entities`, `get_entity_documents`) folgen noch dem alten Modell (Document als Subjekt). Sie sollen auf das Referenz-Modell (Quelle als Referenz, siehe unten) umgestellt oder durch Abfragen über `belegtIn`/Mention ergänzt werden.

---

## Triple-Store-Konzept: Quelle als Referenz

**Vorgabe:** Die Quelle (Dokument, DocumentUnit) aus der relationalen Datenbank wird **nicht** als Subjekt oder Objekt der inhaltlichen Faktentriples verwendet, sondern **nur als Referenz** (Provenienz/Beleg).

- **Faktentriples** haben als Subjekt und Objekt nur **semantische** Dinge: Entitäten (Person, Ort, Ereignis, Thema) oder einen **Mention-/Assertion-Knoten**.
- Die **Quelle** (welches Dokument, welche DocumentUnit den Fakt belegt) wird über ein **eigenes Prädikat** angebunden, z. B.:
  - `rotary:belegtIn` oder `rotary:quelle` / `schema:source` mit Objekt `rotary:DocumentUnit_<id>` bzw. `rotary:Document_<id>`.
- Es wird **kein** Triple der Form `Document rotary:erwaehnt Entity` als Hauptfakt verwendet.

### Variante A – Mention als Knoten

- Triple 1: `Mention_<id> rotary:beziehtSichAuf Entity_<id>`.
- Triple 2: `Mention_<id> rotary:belegtIn DocumentUnit_<id>`.

Subjekt/Objekt der Faktentriples sind Mention und Entity; die Quelle ist nur Referenz (Objekt von `belegtIn`).

### Variante B – Aussage mit Referenz

- Triple 1: `Entity_X rotary:hatRelation Entity_Y` (Relation zwischen Entitäten).
- Triple 2: Aussage- oder Entitäts-Knoten wird mit `rotary:belegtIn DocumentUnit_<id>` verknüpft.

Auch hier: Quelle kommt nur als Referenz vor, nicht als Subjekt der Hauptrelation.

### Abfragen

SPARQL-Abfragen für „alle Belege zu Entity X“ oder „alle Entitäten zu DocumentUnit Y“ laufen über das Referenz-Prädikat, z. B. `?mention rotary:belegtIn ?documentUnit`, nicht über Document als Subjekt.

---

## Geplante Bausteine (Andeutung)

1. **Entitäten-Katalog** – Person, Place, Event, Topic mit optionaler Anbindung an Wikidata (QID, Labels, Koordinaten für Orte).
2. **Triple Store** – Relationen zwischen Entitäten/Mentions; Quelle (Dokument/Unit) nur als Referenz (Prädikat `rotary:belegtIn`). Synchronisation mit Wikidata für Abgleich und Anreicherung.
3. **Karten-Ansicht** – Historische Karten; Orte aus dem Entitäten-Katalog mit Koordinaten (aus Wikidata oder manuell) darstellen.
4. **Foto-Sammlung / Wikimedia Commons** – Anbindung an Commons; Verknüpfung zu Dokumenten und Entitäten.

Vgl. auch README, Abschnitt „Geplante Erweiterungen“.

---

## Erschließungs-Box an der Seitenstelle

Die **Stelle der Erwähnung auf der Seite** wird durch eine **Erschließungs-Box** (eigener Datentyp, Tabelle `erschliessungs_boxes`) abgebildet und mit dem Triple Store verknüpft.

### Zwei Box-Typen

1. **Entitäts-Erwähnung (Person, Ort, …)**  
   Die Box markiert eine Namens-Erwähnung. Nach dem Zeichnen der Box gibt der Nutzer den Namen ein; Vorschläge kommen zuerst aus dem **internen Triple Store**, dann aus **Wikidata**. Die gewählte Person/Entität wird ggf. mit Wikidata-ID und synchronisierten Properties (z. B. P569 Geburtsdatum) im Store angelegt; die Box wird über eine **Mention** mit der Entität verknüpft:  
   `rotary:Mention_<uuid> rotary:belegtIn rotary:ErschliessungsBox_<id>`,  
   `rotary:Mention_<uuid> rotary:beziehtSichAuf rotary:Person_<uuid>`.

2. **Beleg (Aussage mit Referenz)**  
   Die Box markiert eine Textstelle als **Beleg** für eine Aussage (z. B. „Person X wurde in Club Y aufgenommen“). Der Nutzer wählt Subjekt, Prädikat und Objekt; ein **Beleg-Knoten** verknüpft die Aussage mit der Box:  
   `rotary:Beleg_<uuid> rotary:belegtIn rotary:ErschliessungsBox_<id>`,  
   plus `rotary:aussageSubjekt`, `rotary:aussagePraedikat`, `rotary:aussageObjekt`.

### Verknüpfung zum Triple Store

- **Backend:** `api/erschliessung.py` – CRUD für Erschließungs-Boxen pro Seite; Endpoints für Vorschläge (intern, Wikidata), Zuordnung (Assign) und Beleg.
- **Triple Store:** `add_person`, `add_mention`, `add_beleg`, `search_entities`, `get_person_uri_by_name` in `core/triplestore.py`; Properties wie P569 werden über WDT-Namespace 1:1 wie bei Wikidata gespeichert (vgl. `content/wikidata_sync.py`).
- **Frontend:** Im Inspect-View (Seitenansicht) können über das „Box hinzufügen“-Dropdown die Modi **Erschließung – Person** und **Erschließung – Beleg** gewählt werden. Nach dem Zeichnen der Box öffnet sich ein Dialog zur Namenseingabe bzw. zur Auswahl Subjekt/Prädikat/Objekt. Erschließungs-Boxen werden auf der Karte farblich hervorgehoben (z. B. blau/grün) und sind klickbar.
