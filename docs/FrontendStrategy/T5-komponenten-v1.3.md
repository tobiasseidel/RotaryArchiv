# T5-komponenten.md — UI-Komponentenliste RotaryArchiv

> **Version:** 1.3 — 2026-05-02
> **Thread:** T5 Frontend/Design
> **Phase:** 3 — Komponentenliste
> **Änderungen v1.1:** K04 + K05 um Wow-Feature-Erweiterungen ergänzt (AttendanceHeatmap,
>   GapInline); neue Komponente K13 ConsentProgress; Komponentenmatrix aktualisiert.
> **Input aus:** T1-informationsarchitektur.md, T2-migrations-plan.md,
>   T5-designsystem.md, T5-wow-features.md, T5-wow-features-v2.md
> **Status:** Fertig

---

## Komponentenarchitektur-Prinzip

Alle 12 Views sind aus denselben 13 Komponenten zusammengesetzt.
Keine View-spezifischen Sonder-Komponenten. Varianten statt Duplikate.
Jede Komponente hält genau einen Verantwortungsbereich.

---

## K01 — AppShell

**Zweck:** Persistente Hülle um jede View. Enthält Navigation, Footer, globalen Auth-State.

**Views:** Alle 12

**Benötigte Daten:**
- `GET /api/v1/stats` → Statistiken für Footer-Widget
- Auth-State aus localStorage (JWT Access Token, wenn vorhanden)

**Varianten:**
- `anonym` — Navigation ohne Nutzerprofil-Link
- `eingeloggt` — Navigation mit Profillink + Logout

**ASCII-Layout:**
```
┌─────────────────────────────────────────────────┐
│  RotaryArchiv          [Suche 🔍]    [Login]    │  ← Nav (Inter, 15px)
│  Entdecken ▾  Stöbern ▾  Stories  Über uns      │
├─────────────────────────────────────────────────┤
│                                                 │
│              [PAGE CONTENT]                     │
│                                                 │
├─────────────────────────────────────────────────┤
│  RotaryArchiv · Rotary Club Dresden · 100 Jahre │  ← Footer
│  Datenschutz · Impressum · Mitmachen            │
└─────────────────────────────────────────────────┘
```

**Hinweis:** „RotaryArchiv" ist kein Grafik-Logo — es ist der Text in Lora Bold
+ aktueller Epochenfarbe (wenn eine Epochen-Seite aktiv ist).

---

## K02 — HeroBlock

**Zweck:** Emotionaler Einstieg auf V01. Kuratoriertes Protokollzitat, täglich wechselnd.

**Views:** V01 (Startseite)

**Benötigte Daten:**
- `GET /api/v1/featured` → `{ date, quote_text, quote_source, person_slug?, document_id? }`

**Varianten:** keine — HeroBlock ist immer gleich aufgebaut

**ASCII-Layout:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   14. März 1933                           [Epoche-Tag] │
│                                                         │
│   „Der Vorsitzende eröffnet die Sitzung.               │
│    Es fehlen sieben Mitglieder."                        │
│                                                         │
│   ── Sitzungsprotokoll Nr. 47             [→ Zum Dok.] │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

- Hintergrund: `--color-bg`, kein Bild, kein Gradient
- Zitat: Lora Kursiv, 2rem, `--color-text-primary`
- Datum: Inter Semibold, 0.875rem, `--color-text-secondary`
- Quelle: Inter Regular, 0.875rem + Link in Epochenfarbe

**Warum kein Hintergrundbild?**
Ein Bild hinter dem Zitat würde um Aufmerksamkeit konkurrieren. Das Zitat selbst
ist das Bild. Typografie als einziges Gestaltungsmittel — das stärkste Statement
für ein Archiv, das Sprache zur Hauptmaterie erklärt.

---

## K03 — EntityCard

**Zweck:** Kompakte Darstellung einer Entität (Person, Dokument, Ort, Ereignis)
in Listen, Suche, Querverweisen, Kacheln.

**Views:** V01, V02, V05 (Suchergebnisse), V03 (verwandte Personen), V06, V07, V08

**Benötigte Daten:**

| Variante | API-Felder |
|---|---|
| Person | `slug, display_name, born_year, died_year, epoch, is_public` + optional: Portrait-URL |
| Dokument | `id, title, date, epoch, is_public, context_snippet` |
| Ort | `id, display_name, latitude, longitude, is_public` |
| Ereignis | `id, display_name, event_date, epoch, description, is_public` |

**Varianten:**
- `EntityCard–Person`
- `EntityCard–Dokument`
- `EntityCard–Ort`
- `EntityCard–Ereignis`
- `EntityCard–Stub` (für alle Typen, wenn `is_public = false`)

**ASCII-Layout — EntityCard–Person:**
```
┌──────────────────────────────────┐
│ [Portrait 3:4]  Max Müller       │  ← Lora Bold, 1.125rem
│   ~60x80px      1887 – 1951      │  ← Inter, 0.875rem, Sekundär
│                 Die 30er [Badge] │
│                 ──────────────── │
│                 Vorsitzender     │  ← Inter, 0.875rem
└──────────────────────────────────┘
  ↑ linker Rand: 3px Epochenfarbe beim Hover
```

**ASCII-Layout — EntityCard–Stub:**
```
┌──────────────────────────────────┐
│ [  MM  ]        Max M.           │  ← Initialen-Placeholder
│  (Creme)        90er Jahre       │
│                 ──────────────── │
│                 Zugangsbeschränkt│  ← Stub-Farbe
│                 → Einloggen      │  ← Epochenfarbe-Link
└──────────────────────────────────┘
```

**Regelung Bildrechte:**
- Gemeinfreies Portrait oder explizit freigegebenes Bild → anzeigen (desaturiert -25%)
- Kein Bild oder ungeklärte Rechte → Initialen-Placeholder in Epochen-Badge-Farbe

---

## K04 — PersonProfile

**Zweck:** Vollständiges Personenprofil auf V03. Rabbit-Hole-Zentrum.

**Views:** V03

**Benötigte Daten:**
- `GET /api/v1/persons/{slug}` →
  `{ display_name, born_year, died_year, epoch, wikidata_id, notes, is_public,
     self_identified: bool, consent_public: bool|null }`
- `GET /api/v1/persons/{slug}/timeline` → `[ { date, document_id, snippet, role } ]`
- `GET /api/v1/persons/{slug}/network` → `{ nodes, edges }`

**Varianten:**
- `PersonProfile–Öffentlich` — vollständiges Profil
- `PersonProfile–Stub` — Platzhalter (`{ stub: true, display_name, epoch }`)

**ASCII-Layout (öffentlich):**
```
┌──────────────────────────────────────────────────────────┐
│  [Portrait]  Max Müller                   ✓ Gemeldet     │  ← nur wenn self_identified
│  ~120x160px  1887 – 1951 · Vorsitzender 1931–1933        │
│              Die 30er                        [Wikidata ↗]│
├──────────────────────────────────────────────────────────┤
│  ANWESENHEIT                          [→ AttendanceHeatmap]│
│  ████████████░░░░░░░░░░░░░░  1927–1934 · 47 von 61 Sitzungen│
├──────────────────────────────────────────────────────────┤
│  ZEITSTRAHL DER ERWÄHNUNGEN                              │
│  ● 14.03.1933  „...eröffnet die Sitzung..."  [→ Protokoll]│
│  ● 28.02.1933  „...begrüßt Herrn Müller..."  [→ Protokoll]│
├──────────────────────────────────────────────────────────┤
│  NETZWERK  [NetworkGraph–Mini, ~300px hoch]              │
├──────────────────────────────────────────────────────────┤
│  COMMUNITY-BEITRÄGE                                      │
│  [StoryTeaser]  [StoryTeaser]                            │
│  [„Ich kenne mehr über diese Person"]                    │
│  [„Stimmt etwas nicht?"]   [„Das bin ich →"] (eingeloggt)│
└──────────────────────────────────────────────────────────┘
```

## K04-Erweiterung: MembershipBlock *(Features E + F)*

**Zweck:** Zeigt Aufnahme und Austritt als eigene Blöcke auf dem Personenprofil —
mit Originalzitat, optionalem HistoricalContextBox und verknüpften Dokumenten.

**Einbettung:** In K04 PersonProfile, nach Portrait/Metadaten, vor AttendanceHeatmap.

**Benötigte Daten:**
```
GET /api/v1/persons/{slug}/membership
→ [
    {
      event_type: "join" | "leave" | "role_start" | "role_end",
      event_date,
      document_id,
      protocol_wording,       ← Originalzitat, nullable
      historical_context,     ← Redaktioneller Text, nullable
      linked_documents: [{ id, title, date, snippet }]
    }
  ]
```

**Variante Aufnahme:**
```
┌── Aufnahme als Mitglied ─────────────────────────────────┐
│  15. Mai 1929                                            │
│                                                          │
│  „Herr Müller wird einstimmig als Mitglied               │
│   aufgenommen. Der Präsident begrüßt ihn herzlich."      │
│  [→ Zum Protokoll]                                       │
└──────────────────────────────────────────────────────────┘
```

**Variante Austritt ohne Kontext:**
```
┌── Ende der Mitgliedschaft ───────────────────────────────┐
│  9. März 1934  · „persönliche Gründe"                    │
│  [→ Zum Protokoll]   [Ich kenne mehr dazu →]            │
└──────────────────────────────────────────────────────────┘
```

**Variante Austritt mit historical_context (Admin aktiviert):**
```
┌── Ende der Mitgliedschaft ───────────────────────────────┐
│  9. März 1934  · „persönliche Gründe"                    │
│                                                          │
│  ▌ [HistoricalContextBox K10]                            │
│    Historiker bewerten diese Formulierung...             │
│                                                          │
│  [→ Zum Protokoll]   [Ich kenne mehr dazu →]            │
└──────────────────────────────────────────────────────────┘
```

**Variante Austritt mit verknüpftem Dokument (DocumentLinkPanel):**
Siehe K05-Erweiterung DocumentLinkPanel unten — wird inline eingebettet.

---

## K05-Erweiterung: DocumentLinkPanel *(Feature F)*

**Zweck:** Zeigt ein oder mehrere mit dem aktuellen Dokument verknüpfte
Dokumente nebeneinander — ohne Wertung, ohne Label „Widerspruch".

**Einbettung:** In K05 DocumentDualView, als eigene Sektion unterhalb des
Transkripts. Auch einbettbar in K04 MembershipBlock (kompakte Variante).

**Benötigte Daten:**
```
GET /api/v1/documents/{id}/linked
→ [
    {
      id, title, date, snippet,
      link_note   ← optionaler redaktioneller Hinweis, nullable
    }
  ]
```

**ASCII-Layout auf V04 (volle Variante):**
```
┌── Dieses Protokoll: ─────────────────────────────────────┐
│  „...tritt aus persönlichen Gründen aus..."              │
│  Sitzungsprotokoll, 9. März 1934          [→ Volltext]   │
└──────────────────────────────────────────────────────────┘

┌── Ein weiteres Dokument aus dem Bestand: ───────────────┐  ← 3px Ocker-Rand
│  „...man hat mir unmissverständlich bedeutet..."         │
│  Brief, undatiert, ca. 1934–1938          [→ Volltext]   │
└──────────────────────────────────────────────────────────┘
```

**ASCII-Layout kompakt (in MembershipBlock):**
```
  Weiteres Dokument: Brief, ca. 1934  [→ Öffnen]           ← Ocker-Rand links
```

**Regeln:**
- Beide Blöcke gleiche Breite, gleicher Aufbau — kein Block ist prominenter
- Zweiter Block: 3px `--color-epoch-accent` links, kein weiteres Signal
- `link_note` von Admin: erscheint als HistoricalContextBox (K10) darunter —
  wenn `link_note = null`: nur die beiden Blöcke, kein Kommentar
- Kein Label „Widerspruch", „Kontrast" oder ähnliches — nie

**Neue API-Endpoints (Input T6):**
```
GET  /api/v1/documents/{id}/linked
POST /api/v1/document-links
     Body: { document_a_id, document_b_id, link_note? }
     Auth: Admin required
```

**Neue DB-Tabelle (Input T6):**
```python
class DocumentLink(Base):
    __tablename__ = "document_links"
    id            = Column(Integer, primary_key=True)
    document_a_id = Column(Integer, ForeignKey("documents.id"))
    document_b_id = Column(Integer, ForeignKey("documents.id"))
    link_note     = Column(Text, nullable=True)
    created_by    = Column(Integer, ForeignKey("users.id"))
    is_public     = Column(Boolean, default=True)
```

---

## K06-Erweiterung: AmtsStrahl *(Features D + H)*

**Zweck:** Horizontaler Zeitstrahl der Amtsinhaber auf V02.
Zeigt jährlich wechselnde und langfristige Ämter visuell unterschiedlich.
Enthält als unterste Zeile die Austritts-Dichte (Feature H „Stille Welle").

**Einbettung:** Eigene Sektion auf V02 (Epochen-Übersicht), oberhalb TimelineView.

**Benötigte Daten:**
```
GET /api/v1/roles?epoch=30er
→ [
    {
      role_name, role_type: "annual"|"ongoing",
      holders: [{ person_slug, display_name, start_year, end_year, is_public }]
    }
  ]

GET /api/v1/membership-events?epoch=30er&event_type=leave&group_by=year
→ [ { year, count } ]   ← für Stille-Welle-Zeile
```

**ASCII-Layout:**
```
Präsident     [Max M. 31/32][Ernst W. 32/33][░░░░ 33/34][░░░░ 34/35]
Sekretär      [──────────────── Karl Bauer 1929–1936 ────────────────]
Schatzmeister [── Hans S. 1929–32 ──][── Friedrich L. 1932–35 ───────]

──────────────────────────────────────────────────────────────────────
Austritte     · · ·  ·  ████████████████████  ·  ·
              1929   1930   1931   1932   1933   1934   1935
```

**Visuelle Codierung:**

| Typ | Darstellung |
|---|---|
| Jährlich (annual) | Kurze Segmente, harte Trennlinie, volle Epochenfarbe |
| Langfristig (ongoing) | Durchgehender Balken, 70% Epochenfarbe |
| Unleserlich | `.gap-inline`-Muster, klickbar (→ GapInline K05) |
| Leer nach Datum | Nur Zeitachse, kein Balken |

**Interaktion:**
- Klick auf Balken → Personenprofil V03
- Hover: Tooltip mit Name, Amtszeitraum, Sitzungsanzahl
- Austritts-Zeile ausklappbar:
  `[▼ 14 Austritte 1933–1935 — Details anzeigen]`
  → Liste mit Datum, Name (wenn öffentlich), Protokollwortlaut,
    Icon wenn verknüpfte Dokumente vorhanden


---

## K07 — NetworkGraph

**Zweck:** Interaktiver Beziehungsgraph für V07 (Vollansicht) und V03 (Mini-Variante).

**Views:** V07, V03

**Benötigte Daten:**
- `GET /api/v1/network/graph?epoch=...&min_connections=2`
  → `{ nodes: [{id, label, epoch, is_public, slug}], edges: [{source, target, weight}] }`
- Für Mini-Variante: `GET /api/v1/persons/{slug}/network`

**Varianten:**
- `NetworkGraph–Full` — V07, volle Höhe, Filter-Panel, klickbare Knoten
- `NetworkGraph–Mini` — V03, eingebettet, ~300px, nur direkte Verbindungen

**Bibliothek:** [OFFEN] — Empfehlung: **vis-network** oder **D3.js force simulation**

**ASCII-Layout (Full):**
```
┌─[Filter]──────────────────────────────────────────────┐
│ Epoche: [30er] [90er] [Beide]  Min. Verbindungen: [2] │
├───────────────────────────────────────────────────────┤
│       ●Max M.──────────●Karl B.                       │
│       │        ╲       │                              │
│       ●Ernst W.  ●Hans K.                             │
│               [○ anon.] ← nicht-öffentliche Person   │
│  Klick auf Knoten → PersonProfile (V03)               │
└───────────────────────────────────────────────────────┘
```

- Nicht-öffentliche Knoten: leerer Kreis (○), kein Name, kein Link
- Knoten-Größe: proportional zur Anzahl Verbindungen
- Edge-Dicke: proportional zu `weight` (gemeinsame Dokumente)

---

## K08 — SearchBar & SearchResults

**Zweck:** Globale Suche (in AppShell) + Ergebnisliste auf V05.

**Views:** Alle (SearchBar), V05 (SearchResults)

**Benötigte Daten:**
- `GET /api/v1/search?q=...&type=...&epoch=...`
  → `{ results: [{ type, id/slug, display_name, epoch, context_snippet, is_public }] }`

**Varianten:**
- `SearchBar–Global` — kompakt, in AppShell-Navigation
- `SearchBar–Expanded` — auf V05, mit Filterleiste
- `SearchResults–Liste` — Ergebnisliste mit Snippets
- `SearchResults–Leer` — Leerzustand als Einladung

**ASCII-Layout — SearchResults–Leer:**
```
┌───────────────────────────────────────────────────┐
│  Für „Friedrich Hartmann" gibt es noch            │
│  keine Einträge im Archiv.                        │
│                                                   │
│  Wissen Sie etwas über diese Person?              │
│  [Story einreichen →]                             │
└───────────────────────────────────────────────────┘
```

## K08a-Erweiterung: Mitgliedschafts-Suchfilter *(Feature I)*

**Zweck:** Zusätzlicher Filter in SearchResults für Mitgliedschaftsereignisse.

**Neue Filterstruktur:**
```
Typ: [Mitgliedschaft ▾]
  ├── Aufnahme
  ├── Austritt
  ├── Amtswechsel
  └── Mit verknüpftem Dokument  ← nur wenn DocumentLinks vorhanden
```

**Neuer API-Parameter:**
```
GET /api/v1/search?type=membership_event&has_linked_document=true
```

---

## K09 — ContributionForm

**Zweck:** Niedrigschwelliges Einreichungsformular für Stories (V09),
Korrekturen (V10) und Gap-Inline-Beiträge (K05-Erweiterung).

**Views:** V09, V10, inline in K05

**Benötigte Daten (POST):**
- `POST /api/v1/stories` → `{ title, body, author_name?, author_email_enc?,
  related_entity_type?, related_entity_id? }`
- `POST /api/v1/corrections` → `{ body, author_name?, author_email_enc?,
  related_entity_type, related_entity_id }`

**Varianten:**
- `ContributionForm–Story`
- `ContributionForm–Korrektur`
- `ContributionForm–Gap` (inline, vorausgefüllt mit `bbox_id`, nur Freitext-Feld)

**Nach Einreichung — Bestätigung (Formular verschwindet):**
```
┌──────────────────────────────────────────────────────┐
│  Danke.                                              │
│                                                      │
│  Ihr Beitrag wird von einem Admin geprüft und danach │
│  hier sichtbar sein.                                 │
│                                                      │
│  [Zurück zur Person]  [Weitere Story einreichen]     │
└──────────────────────────────────────────────────────┘
```

---

## K10 — HistoricalContextBox

**Zweck:** Eingebetteter Erklärungsblock für historisch sensible Inhalte,
epochenspezifische Hinweise und Nicht-öffentlich-Erklärungen.

**Views:** V02, V03, V04, V12

**Varianten:**
- `HistoricalContextBox–Sensibel` — für 1933–1937
- `HistoricalContextBox–Zugangsbeschränkung` — für nicht-öffentliche Inhalte
- `HistoricalContextBox–Erschließungshinweis` — für teilweise erschlossene Dokumente

**ASCII-Layout:**
```
│▌ Dieser Abschnitt des Protokolls ist unleserlich.    │
│  43 % dieser Seite sind bisher entziffert —          │
│  die Arbeit läuft weiter.                            │
```

- Linker Rand: 3px `--color-epoch-accent`
- Schrift: Lora Kursiv, `--color-text-secondary`

---


## K11-Erweiterung: StorySourcePanel *(Feature G)*

**Zweck:** Zeigt auf V08 (Story-Detail) die verknüpften Primärquellen —
macht Stories zur Tür ins Archiv.

**Einbettung:** Sektion am Ende von StoryDetail–Seite, vor Community-CTA.

**Benötigte Daten:**
```
GET /api/v1/stories/{slug}/documents
→ [ { id, title, date, type, snippet } ]
```

**ASCII-Layout:**
```
┌── Primärquellen zu dieser Story ────────────────────────┐
│                                                         │
│  ● [Protokoll]  Sitzung 09.03.1934        [→ Öffnen]   │
│  ● [Dokument]   Brief Ernst Goldmann      [→ Öffnen]   │
│  ● [Protokoll]  Sitzung 15.04.1934        [→ Öffnen]   │
│                                                         │
│  [Alle 7 verknüpften Dokumente anzeigen]               │
└──────────────────────────────────────────────────────────┘
```

**Neues Story-Feld (Input T6):**
```python
story_type = Column(SQLEnum(StoryType), default=StoryType.COMMUNITY)
# COMMUNITY: normaler Beitrag
# EDITORIAL: von Admin, prominenter auf V01/V02 platziert
```

**Neue DB-Tabelle (Input T6):**
```python
class StoryDocumentLink(Base):
    __tablename__ = "story_document_links"
    story_id    = Column(Integer, ForeignKey("stories.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    sort_order  = Column(Integer, default=0)
```

---

## K12 — MapView

**Zweck:** Leaflet-Kartenkomponente für V06.

**Views:** V06

**Benötigte Daten:**
- `GET /api/v1/places?epoch=...` →
  `[{ id, display_name, latitude, longitude, is_public, mention_count }]`

**ASCII-Layout:**
```
┌─[Toggle: 30er | 90er | Beide]──────────────────────┐
│  ┌──────── Karte (Leaflet, CartoDB Voyager) ──────┐ │
│  │         ●  ← Marker in Epochenfarbe            │ │
│  │     ●       ●              ●                   │ │
│  └─────────────────────────────────────────────── ┘ │
│  [Detail-Panel: Ort · N Erwähnungen · Personen...] │
└─────────────────────────────────────────────────────┘
```

---

## K13 — ConsentProgress *(Feature C — neu)*

**Zweck:** Zeigt den kollektiven Freischaltungsfortschritt eines 90er-Protokolls.
Macht den Consent-Prozess transparent und sozial ansteckend.

**Views:** V02b (Epochen-Übersicht 90er), V04 (Dokumentansicht, Stub-Variante)

**Benötigte Daten:**
- `GET /api/v1/documents/{id}/consent-status` →
  `{ total_persons, identified, consented, score: float, ready_for_release: bool }`
- `POST /api/v1/persons/{slug}/identify` (Auth required)
- `POST /api/v1/persons/{slug}/consent` (Auth required, must be self_identified)

**Varianten:**
- `ConsentProgress–DokumentStub` — auf V04, wenn Dokument gesperrt + hat Fortschritt
- `ConsentProgress–EpochenListe` — kompakte Version in V02b-Übersicht

**ASCII-Layout — ConsentProgress–DokumentStub:**
```
┌──────────────────────────────────────────────────────────┐
│  Protokoll vom 15. März 1998                             │
│                                                          │
│  Dieses Protokoll kann öffentlich werden,                │
│  wenn alle Beteiligten zustimmen.                        │
│                                                          │
│  ████████████░░░░░░░░  5 von 8 Personen haben zugestimmt│
│                                                          │
│  Kennen Sie jemanden, der dabei war?                     │
│  [Weitersagen →]                                         │
└──────────────────────────────────────────────────────────┘
```

**ASCII-Layout — Selbstidentifikation (eingeloggt, auf PersonProfile):**
```
┌──────────────────────────────────────────────────────────┐
│  Sind Sie W. Hartmann, geb. ca. 1952?                    │
│                                                          │
│  Wenn Sie sich identifizieren, werden Sie gefragt, ob    │
│  Sie der Veröffentlichung der Sie betreffenden           │
│  Protokolleinträge zustimmen.                            │
│                                                          │
│  [Ja, das bin ich]        [Abbrechen]                   │
└──────────────────────────────────────────────────────────┘
```

**Consent-Stufen (konfigurierbar durch Admin):**

| Score | Effekt im Frontend |
|---|---|
| ≥ 1 Person identifiziert | Personenseite zeigt `✓ Gemeldet` |
| ≥ 50 % Consent | Dokument in V02b als „teilweise zugänglich" + CTA |
| 100 % oder Admin-Override | Dokument wird vollständig öffentlich |

**Datenschutz-Prinzip:**
- Wer sich identifiziert hat, ist öffentlich **nicht** einsehbar
- Öffentlich sichtbar: nur Anzahl + Signal `✓ Gemeldet`
- Admin sieht: `self_identified_by (user_id)`, `consent_public`, `consent_updated_at`

**Neue DB-Felder (Input für T6 / rotary_core/models.py):**
```python
# Erweiterung Person-Modell:
self_identified_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
consent_public      = Column(Boolean, nullable=True)
  # None = noch nicht entschieden
  # True = Consent gegeben
  # False = abgelehnt
consent_updated_at  = Column(DateTime, nullable=True)
identified_at       = Column(DateTime, nullable=True)
```

**Neue Endpoints (Input für T6 / Backend B):**
```
POST /api/v1/persons/{slug}/identify
     Auth: required
     → self_identified_by = current_user.id, identified_at = now()

POST /api/v1/persons/{slug}/consent
     Auth: required, must be self_identified
     Body: { consent: true | false }
     → consent_public = body.consent, consent_updated_at = now()
     → Trigger: Neuberechnung consent_score für verknüpfte Dokumente

GET  /api/v1/documents/{id}/consent-status
     → { total_persons, identified, consented, score, ready_for_release }
```

## Hintergrund: Warum V12 zwei Zielgruppen braucht

V12 „Über das Projekt" hat bisher eine primäre Zielgruppe: den neugierigen
Außenstehenden, der verstehen will, worum es geht.

Es gibt eine zweite, strukturell wichtige Zielgruppe, die bisher nicht adressiert
wurde: **der Vorstand des Rotary Club Dresden** — oder allgemeiner: ein Mitglied
oder Gremium, das institutionelle Verantwortung trägt und deshalb skeptisch ist.

Diese Person fragt nicht: „Was ist das für ein Projekt?"
Sie fragt: **„Was kann hier über unseren Club veröffentlicht werden, ohne dass
wir gefragt werden? Und wer entscheidet das?"**

Diese Frage ist berechtigt. Sie verdient eine direkte, ehrliche Antwort —
visuell gleichwertig zur kuratorischen Aussage, inhaltlich an die Institution
gerichtet.

---

## Ergänzung: V12 — Über das Projekt

### Aktualisierte Zielgruppenübersicht

| Archetyp | Haltung beim Eintreffen | Was sie suchen |
|---|---|---|
| Neugieriger Außenstehender | Offen, orientierungslos | Mission, Tonalität, Vertrauensaufbau |
| **Vorstand / Institutionsvertreter** | **Skeptisch, prüfend** | **Kontrolle, Grenzen, Ansprechpartner** |

Beide Zielgruppen landen auf derselben Seite. Das Layout trennt nicht —
es adressiert beide innerhalb einer kohärenten Struktur.

### Seitenstruktur V12 (aktualisiert)

```
┌─────────────────────────────────────────────────────────┐
│  [T5-IT-03a] Kuratorisches Statement                    │
│  Wer steckt dahinter? Was ist die Absicht?              │
│  → Adressiert: Außenstehende, Familienforscher,         │
│    interessierte Öffentlichkeit                         │
├─────────────────────────────────────────────────────────┤
│  [T5-IT-03b] Was der Club kontrolliert  ← NEU           │
│  Welche Entscheidungen liegen beim Club?                │
│  → Adressiert: Vorstand, Mitglieder, Institutionsvertr. │
├─────────────────────────────────────────────────────────┤
│  [Bestehend] Team, Methodik, Kontakt                    │
└─────────────────────────────────────────────────────────┘
```

**Visuelle Gleichwertigkeit:**
Beide Sektionen (T5-IT-03a und T5-IT-03b) haben identisches Styling:
gleiche Schriftgröße, gleicher Weißraum, gleicher visueller Gewicht.
Keine Sektion wirkt wie ein Anhang oder eine Fußnote der anderen.

---

## T5-IT-03b: Untersektion „Was der Club kontrolliert"

### Inhaltliche Anforderungen

Diese Sektion beantwortet vier Fragen, die ein skeptischer Vorstand stellen würde:

1. **Wer entscheidet, was veröffentlicht wird?**
2. **Können Inhalte zurückgezogen werden?**
3. **Wie werden lebende Personen geschützt?**
4. **An wen wende ich mich mit Einwänden?**

Die Antworten sind kurz, direkt und ohne defensiven Ton.
Kein Marketingsprech. Kein Kleingedrucktes.

### ASCII-Layout

```
┌── Was der Club kontrolliert ────────────────────────────┐
│                                                         │
│  Dieses Archiv entsteht in enger Abstimmung mit dem     │
│  Rotary Club Dresden.                                   │
│                                                         │
│  ┌── Was der Club entscheidet: ──────────────────────┐  │
│  │  ✓  Welche Dokumente erschlossen werden           │  │
│  │  ✓  Ob Inhalte zurückgezogen oder gesperrt werden │  │
│  │  ✓  Wer administrativen Zugang erhält             │  │
│  │  ✓  Alle Inhalte zu lebenden Personen             │  │
│  │     (→ Einwilligung erforderlich, jederzeit       │  │
│  │        widerrufbar)                               │  │
│  └────────────────────────────────────────────────── ┘  │
│                                                         │
│  Einwände, Korrekturen oder Sperrwünsche:               │
│  [→ Direkt an das Projektteam schreiben]                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Typografie:**
- Abschnittstitel „Was der Club kontrolliert": Lora Bold, H2 (1.5rem)
  — identisch mit T5-IT-03a-Titel
- Fließtext: Lora Regular, 1rem
- Checkliste: Inter Regular, 0.9375rem, mit `✓` in `--color-epoch-primary`
- Kontakt-Link: Epochenfarbe, unterstrichen

**Kein HistoricalContextBox hier.** Diese Sektion ist kein Hinweis —
sie ist eine direkte Aussage. K10 ist für Erklärungen, nicht für Versprechen.

### Warum keine Defensive

Der Ton ist aktiv, nicht apologetisch:
- NICHT: „Wir versuchen sicherzustellen, dass..."
- SONDERN: „Der Club entscheidet. Punkt."

Das ist stärker als jede Beruhigungsstrategie — weil es wahr ist
und weil es die Kontrollfrage direkt beantwortet.

---

## Neue K10-Variante: `HistoricalContextBox–Kontrollhinweis`

**Nicht für V12 selbst** — aber als wiederverwendbare Komponente für Stellen
im Archiv, wo ein institutioneller Hinweis nötig ist
(z.B. auf V04 bei einem gesperrten Dokument mit Club-Entscheidung):

```
│▌ Dieses Dokument wurde auf Wunsch des Rotary Club Dresden  │
│  gesperrt. Für Rückfragen: [→ Kontakt]                     │
```

- Stilisierung: identisch mit anderen K10-Varianten
  (3px `--color-epoch-accent` links, Lora Kursiv, `--color-text-secondary`)
- Kein Alarm-Ton, keine Begründungspflicht im Interface
- Unterschied zu `K10–Zugangsbeschränkung`: dort geht es um Persönlichkeitsrechte,
  hier um eine institutionelle Entscheidung

**Neue Variante in K10:**
```
K10-Varianten (aktualisiert):
- HistoricalContextBox–Sensibel
- HistoricalContextBox–Zugangsbeschränkung
- HistoricalContextBox–Erschließungshinweis
- HistoricalContextBox–Kontrollhinweis  ← NEU
```

---

## Aktualisierte Komponentenmatrix (nur geänderte Zeile)

| Komponente  | V12 | Änderung |
|---|---|---|
| K10 ContextBox | ✓ | Neue Variante `–Kontrollhinweis` hinzugefügt |

*V12 erscheint bereits in der bestehenden Matrix — keine Strukturänderung nötig.*


---

## Komponentenmatrix: Welche Komponente in welchem View?

| Komponente            | V01 | V02 | V03 | V04 | V05 | V06 | V07 | V08 | V09 | V10 | V11 | V12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| K01 AppShell          |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |
| K02 HeroBlock         |  ✓  |     |     |     |     |     |     |     |     |     |     |     |
| K03 EntityCard        |  ✓  |  ✓  |  ✓  |     |  ✓  |     |     |  ✓  |     |     |     |     |
| K04 PersonProfile           |     |     |  ✓  |     |     |     |     |     |     |     |     |     |
| ↳ AttendanceHeatmap         |     |     |  ✓  |     |     |     |     |     |     |     |     |     |
| ↳ **MembershipBlock**       |     |     |  ✓  |     |     |     |     |     |     |     |     |     |
| K05 DualView                |     |     |     |  ✓  |     |     |     |     |     |     |     |     |
| ↳ GapInline                 |     |     |     |  ✓  |     |     |     |     |     |     |     |     |
| ↳ **DocumentLinkPanel**     |     |     |  ✓  |  ✓  |     |     |     |     |     |     |     |     |
| K06 TimelineView            |     |  ✓  |  ✓  |     |     |     |     |     |     |     |     |     |
| ↳ **AmtsStrahl**            |     |  ✓  |     |     |     |     |     |     |     |     |     |     |
| K07 NetworkGraph      |     |     |  ✓  |     |     |     |  ✓  |     |     |     |     |     |
| K08 Search                  |  ✓  |     |     |     |  ✓  |     |     |     |     |     |     |     |
| ↳ **Mitgliedschaftsfilter** |     |     |     |     |  ✓  |     |     |     |     |     |     |     |
| K09 ContribForm       |     |     |     |  ✓  |     |     |     |     |  ✓  |  ✓  |     |     |
| K10 ContextBox        |     |  ✓  |  ✓  |  ✓  |     |     |     |  ✓  |     |     |     |  ✓  |
| K11 StoryTeaser             |  ✓  |     |  ✓  |     |     |     |     |  ✓  |     |     |  ✓  |     |
| ↳ **StorySourcePanel**      |     |     |     |     |     |     |     |  ✓  |     |     |     |     |
| K12 MapView           |     |     |     |     |     |  ✓  |     |     |     |     |     |     |
| K13 ConsentProgress         |     |  ✓  |     |  ✓  |     |     |     |     |     |     |     |     |

---


## Neue DB-Tabellen Gesamtübersicht (Input T6)

| Tabelle | Feature | Phase |
|---|---|---|
| `membership_events` | E (Aufnahme/Abgang) | T6/P2 |
| `document_links` | F (Zwei Dokumente) | T6/P1 |
| `story_document_links` | G (Story als Eingang) | T6/P1 |
| Felder auf `Person` | C (Consent) | T6/P3 |
| Felder auf `Role`/Triplestore | D (Amtsstrahl) | T6/P2 |
| Feld `story_type` auf `Story` | G (Editorial) | T6/P1 |


## Offene Entscheidungen

| Entscheidung | Empfehlung | Status |
|---|---|---|
| Netzwerk-Graph-Bibliothek | vis-network oder D3.js | [OFFEN] |
| Hover-Tooltip in Transkriptionstext | Popper.js oder CSS-only | [OFFEN] |
| Portrait-Bildpfad | `/static/portraits/{slug}.jpg` via Nginx | Empfehlung, T6 bestätigen |
| GapInline-Schwellwert für ocr_confidence | < 0.6 als „unleserlich"? | [OFFEN — T6/T7] |

---

*Letzte Änderung: v1.2 — patch aus wow-v2  eingearbeitet.*
*Phase 4 (T5-framework-entscheidung.md) auf Abruf bereit.*
