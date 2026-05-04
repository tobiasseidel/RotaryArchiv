# T5-wow-features.md — Signature-Features RotaryArchiv

> **Version:** 2.0 — 2026-05-03
> **Thread:** T5 Frontend/Design
> **Änderungen v2.0:** Mitgliedschafts-Features (Ideen 1–5) integriert; „Zwei Stimmen"
>   als Dokumenten-Nebeneinanderstellung (kein eigener Entitätstyp); Story als
>   kuratorischer Eingang präzisiert; Gesamtbewertung aller Features abgeschlossen.
> **Status:** Fertig — Input für T5-komponenten.md v1.2 und T6 Coding
> **Abhängigkeiten:** T5-designsystem.md, T5-komponenten.md v1.1, T3-auth-konzept.md,
>   T2-migrations-plan.md

---

## Leitprinzip

> „RotaryArchiv ist der Ort, an dem vergessene Namen wieder zu Menschen werden."

Alle Features werden daran gemessen. Zusätzlich gilt für dieses Dokument:

> Das Interface urteilt nicht. Es zeigt. Der Besucher zieht seine Schlüsse selbst.

---

## Designprinzipien für historisch sensible Darstellung

Bevor die Features beschrieben werden — diese Prinzipien sind nicht verhandelbar:

1. **Keine automatische Kategorisierung.** Das System ordnet niemanden als
   „NS-Opfer", „Mitläufer" oder „Opportunist" ein. Das tut ein menschlicher
   Redakteur — durch eine Story, einen Kontexthinweis, einen verknüpften Beleg.

2. **Muster zeigen, nicht behaupten.** Sechs Austritte mit „persönlichen Gründen"
   zwischen 1933 und 1935 sind ein Muster. Das Interface macht es sichtbar —
   ohne es zu benennen.

3. **Zwei Dokumente nebeneinander, kein Urteil dazwischen.** Ein Protokoll sagt
   eine Sache. Ein Brief sagt etwas anderes. Beide sind Dokumente. Beide werden
   gleichwertig gezeigt. Was das bedeutet, entscheidet der Besucher.

4. **Würde der Betroffenen.** Personen, die zum Austritt gedrängt wurden, bekommen
   keinen roten Warnhinweis, kein Alarm-Icon. Sondern Stille — und einen
   Kontext-Block, der erklärt, ohne zu verurteilen.

5. **Kuratorischer Eingang, dann Sog.** Stories sind redaktionelle Türen in
   historisch komplexe Themen. Durch sie betritt man das Archiv — und wird
   dann von den Primärquellen selbst weitergezogen.

---

## Feature A — „Der unleserliche Satz"
### Leerstände als Beitragseinladungen

### Kernidee

Unleserliche Textstellen in Transkriptionen werden nicht versteckt,
sondern als klickbare Einladungen dargestellt.

**Bewertung:** ✅ Kern-Feature. Geringer Aufwand, hoher emotionaler ROI.
Funktioniert für Protokolle und für alle anderen Dokumenttypen gleichermaßen.
Unverändert gegenüber v1.0.

### Zustände

| Zustand | Aussehen | CSS-Klasse |
|---|---|---|
| Offen / unleserlich | `░░░░░` grau, klickbar | `.gap-inline` |
| Panel geöffnet | Inline-Tooltip mit ContributionForm | `.gap-inline.open` |
| Beitrag eingereicht | `░░░░░` leicht grünlich | `.gap-inline.gap-submitted` |
| Admin freigegeben | Text erscheint normal, Gap verschwindet | — |

### ASCII-Layout (Panel geöffnet)

```
  ...Es fehlen ░░░░░░░░░░░░░░░░░░░░ und drei weitere...
               ┌────────────────────────────────────┐
               │ Diese Stelle ist noch unleserlich. │
               │                                    │
               │ Können Sie diesen Namen entziffern?│
               │ [Ich kenne diesen Text →]          │
               └────────────────────────────────────┘
```

### Neue API-Endpoints (Input T6)

```
GET /api/v1/documents/{id}/gaps
→ [ { bbox_id, page_number, position, gap_text_placeholder } ]

POST /api/v1/corrections
Body: { related_entity_type: "bbox", related_entity_id: {bbox_id}, body: "..." }
```

---

## Feature B — „Wer fehlte?"
### Anwesenheits-Heatmap als Geschichtsspiegel

### Kernidee

Kalender-Grid auf dem Personenprofil: jede Sitzung ein Kästchen,
ausgefüllt wenn erwähnt, leer wenn nicht. Abwesenheit wird sichtbar.

**Bewertung:** ✅ Stark — durch die Mitgliedschaftsperspektive noch stärker.
Wenn eine Person ab 1934 nicht mehr erscheint, ist das ein Muster.
Die Heatmap zeigt es ohne Kommentar. Implementierung nach T6/P2.

### ASCII-Layout

```
         Jan  Feb  Mär  Apr  Mai  Jun  ...  Dez
  1929   ████ ████ ████ ░░░░ ████ ████      ████
  1930   ████ ████ ████ ████ ████ ████      ████
  1932   ████ ████ ░░░░ ░░░░ ░░░░ ░░░░      ░░░░
  1933   ████ ████ ░░░░ ░░░░ ░░░░ ░░░░      ░░░░
  1934   ░░░░ ░░░░ ░░░░ ...

  [■ Erwähnt]  [□ Sitzung ohne Erwähnung]  [  ] Keine Sitzung
  Erste Erwähnung: 14.05.1929 · Letzte: 28.02.1933
```

- Zellenfarbe anwesend: `--color-epoch-primary`
- Zellenfarbe abwesend: `--color-border`
- Hover: Tooltip mit Datum + Snippet oder „Keine Erwähnung"
- Klick auf anwesende Zelle → direkt zum Protokoll (V04)
- Mobile: Jahres-Balken statt Monats-Grid

---

## Feature C — „Hier war ich dabei"
### Consent-gesteuerte Selbstidentifikation

### Kernidee

Eingeloggte Nutzer identifizieren sich auf einer Personenseite selbst.
Wenn alle namentlich Erwähnten eines Protokolls zugestimmt haben,
kann das Protokoll freigeschaltet werden — kollektiv, transparent.

**Bewertung:** ✅ Unverzichtbar für die 90er.
Erweiterungsidee (v2.0): Nicht nur Betroffene, auch **Nachfahren** können
einen Bezug herstellen — als Story-Beitrag, nicht als Identifikation.
[OFFEN — inhaltliche Entscheidung]

### Consent-Stufen

| Score | Effekt |
|---|---|
| ≥ 1 Person identifiziert | Personenseite: `✓ Gemeldet` |
| ≥ 50 % Consent | Dokument in V02b als „teilweise zugänglich" + CTA |
| 100 % oder Admin-Override | Vollständig öffentlich |

### Neue DB-Felder (Input T6)

```python
# Person-Modell:
self_identified_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
consent_public      = Column(Boolean, nullable=True)
consent_updated_at  = Column(DateTime, nullable=True)
identified_at       = Column(DateTime, nullable=True)
```

### Neue API-Endpoints (Input T6)

```
POST /api/v1/persons/{slug}/identify
POST /api/v1/persons/{slug}/consent   Body: { consent: true|false }
GET  /api/v1/documents/{id}/consent-status
```

---

## Feature D — „Die Stühle des Clubs"
### Amtsstrahl mit Rotations-Lesbarkeit

### Kernidee

Auf V02 (Epochen-Übersicht) ein horizontaler Zeitstrahl, der zeigt,
wer wann welches Amt innehatte — mit visuell codierter Unterscheidung
zwischen jährlich wechselnden und langfristigen Ämtern.

**Bewertung:** ✅ Wichtigstes strukturelles Feature. Neu priorisiert in v2.0.
Der Amtsstrahl macht den Unterschied zwischen „Rotary-Normalität" und
„hier ist etwas aus dem Rhythmus geraten" auf einen Blick lesbar.

### ASCII-Layout

```
Präsident     [Max M. 31/32][Ernst W. 32/33][Paul R. 33/34][░░░░ 34/35]
Sekretär      [─────────────── Karl Bauer 1929–1936 ──────────────────]
Schatzmeister [── Hans S. 1929–1932 ──][── Friedrich L. 1932–1935 ────]
Beisitzer     [Kurt F.][Paul G.][Ernst H.][Werner K.][░░░░░░][░░░░░░░░]
              1929     1930     1931     1932     1933     1934     1935
```

**Visuelle Codierung:**

| Amt-Typ | Darstellung | Bedeutung |
|---|---|---|
| Jährlich wechselnd (Präsident) | Kurze Segmente, harte Trennlinie | Das ist Rotary — das ist normal |
| Langfristig stabil | Durchgehender Balken, gedämpftere Farbe | Kontinuität, Verlässlichkeit |
| Unleserlich/unbekannt | `░░░░`-Muster, klickbar (GapInline) | Lücke — Beitragseinladung |
| Leer nach Datum | Kein Balken, nur Zeitachse | Hier hat etwas aufgehört |

**Interaktion:**
- Klick auf Balken → Personenprofil (V03)
- Hover: Tooltip mit Name, Amtszeitraum, Anzahl Sitzungen in dieser Amtszeit
- Idee 4 (Vorstandsliste nach Jahr) wird zur **ausklappbaren Detailansicht**
  unterhalb des Strahls — nicht als eigene Sektion

### Neue DB-Felder (Input T6)

```python
# Erweiterung Triplestore-Rolle oder neue Tabelle:
role_start_year  = Column(Integer, nullable=True)
role_end_year    = Column(Integer, nullable=True)
role_type        = Column(String, nullable=True)
# z.B. "annual" (jährlich) vs. "ongoing" (langfristig)
```

---

## Feature E — „Aufnahme und Abgang"
### Mitgliedschafts-Ereignis als eigener Moment

### Kernidee

Wenn ein Protokoll die Aufnahme oder den Austritt explizit nennt,
wird dieser Moment auf dem Personenprofil prominent dargestellt —
mit dem Originalzitat aus dem Protokoll und, wenn vorhanden,
einem daneben gestellten weiteren Dokument.

**Bewertung:** ✅ Unverzichtbar. In v2.0 durch „Zwei Dokumente"
(Feature F) zur stärksten einzelnen Stelle im Interface.

### ASCII-Layout — Aufnahme

```
┌── Aufnahme als Mitglied ─────────────────────────────────┐
│  15. Mai 1929                                            │
│                                                          │
│  „Herr Müller wird einstimmig als Mitglied               │
│   aufgenommen. Der Präsident begrüßt ihn herzlich."      │
│                                                          │
│  [→ Zum Protokoll vom 15.05.1929]                        │
└──────────────────────────────────────────────────────────┘
```

### ASCII-Layout — Austritt mit Kontexthinweis

```
┌── Ende der Mitgliedschaft ───────────────────────────────┐
│  9. März 1934  · „persönliche Gründe"                    │
│                  ↑ Protokollwortlaut                     │
│                                                          │
│  ┌── Historischer Kontext ──────────────────────────┐    │
│  │ Zwischen 1933 und 1935 traten mehrere Mitglieder │    │
│  │ mit dieser Formulierung aus. Historiker bewerten │    │
│  │ diese Formulierung als häufige Umschreibung für  │    │
│  │ politischen Druck in dieser Zeit.               │    │
│  │ [Mehr zum historischen Kontext →]               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  [→ Zum Protokoll]   [Ich kenne mehr dazu →]            │
└──────────────────────────────────────────────────────────┘
```

**Wichtig:** Der HistoricalContextBox-Block erscheint **nicht automatisch**.
Er wird von einem Admin/Redakteur manuell für dieses Ereignis aktiviert.
Das ist eine redaktionelle Entscheidung — keine algorithmische.

### Neue DB-Felder (Input T6)

```python
class MembershipEvent(Base):
    __tablename__ = "membership_events"
    id                    = Column(Integer, primary_key=True)
    person_id             = Column(Integer, ForeignKey("persons.id"))
    event_type            = Column(SQLEnum(MembershipEventType))
    # Enum: join / leave / role_start / role_end
    event_date            = Column(DateTime, nullable=True)
    document_id           = Column(Integer, ForeignKey("documents.id"), nullable=True)
    protocol_wording      = Column(String(500), nullable=True)
    # Originalzitat aus dem Protokoll
    historical_context    = Column(Text, nullable=True)
    # Redaktioneller Kontext-Block — wenn NULL: kein Block anzeigen
    is_public             = Column(Boolean, default=True)
```

---

## Feature F — „Zwei Dokumente"
### Nebeneinanderstellung ohne Urteil

### Kernidee

Dokumente können mit anderen Dokumenten verknüpft werden —
ohne dass das Interface diese Verknüpfung interpretiert.
Ein Brief liegt neben einem Protokoll. Beide sind Dokumente.
Was der Unterschied bedeutet, entscheidet der Besucher.

**Bewertung:** ✅ Das fehlende Herzstück (v2.0 neu).
Technisch kein neuer Entitätstyp — nur eine neue Verknüpfungstabelle
zwischen zwei bestehenden `Document`-Objekten.

### ASCII-Layout — auf V04 (Dokumentansicht)

```
┌── Dieses Protokoll sagt: ────────────────────────────────┐
│  „Herr Goldmann tritt aus persönlichen Gründen aus.      │
│   Der Präsident dankt ihm für seine Mitarbeit."          │
│  ── Sitzungsprotokoll, 9. März 1934         [→ Volltext] │
└──────────────────────────────────────────────────────────┘

┌── Ein weiteres Dokument aus dem Bestand: ───────────────┐  ← Ocker-Rand
│  „...man hat mir unmissverständlich bedeutet, dass       │
│   meine weitere Mitgliedschaft dem Club schade..."       │
│  ── Brief, undatiert, ca. 1934–1938         [→ Volltext] │
└──────────────────────────────────────────────────────────┘
```

**Visuell:**
- Beide Blöcke gleiche Breite, gleicher Aufbau — gleichwertig
- Zweiter Block: 3px Ocker-Rand links (`--color-epoch-accent`)
- Kein Werturteil, kein Label „Widerspruch", kein ⚖-Symbol im Default
- Optional: Admin kann einen kurzen redaktionellen Hinweis ergänzen
  (dann erscheint HistoricalContextBox darunter)

**Wo erscheint die Nebeneinanderstellung:**
- Auf V04 des Protokolls: verknüpfte Dokumente als eigene Sektion
- Auf V04 des Briefs: das Protokoll als verknüpftes Dokument
- Auf V03 (Personenprofil): im Mitgliedschafts-Block (Feature E)
- Auf V08 (Story): in der Primärquellen-Sektion

### Neue DB-Felder (Input T6)

```python
class DocumentLink(Base):
    __tablename__ = "document_links"
    id              = Column(Integer, primary_key=True)
    document_a_id   = Column(Integer, ForeignKey("documents.id"))
    document_b_id   = Column(Integer, ForeignKey("documents.id"))
    link_note       = Column(Text, nullable=True)
    # Optionaler redaktioneller Hinweis — wenn NULL: nur Dokumente zeigen
    created_by      = Column(Integer, ForeignKey("users.id"))
    is_public       = Column(Boolean, default=True)
```

---

## Feature G — Story als kuratorischer Eingang
### Redaktionelle Tür zu Primärquellen

### Kernidee

Stories sind nicht nur Community-Beiträge — sie sind **redaktionelle Einstiege**
in historisch komplexe Themen. Eine Story über die Austritte 1933–1935 ist
der Artikel, der dem Besucher Kontext gibt — und ihn dann in die Primärquellen
zieht, wo er selbst weitergräbt.

**Bewertung:** ✅ Architekturentscheidung, nicht Feature.
Ändert V08 (Story-Detail) strukturell: weniger „Beitrag lesen",
mehr „Tür zu Primärquellen öffnen".

### Neues Element auf V08 — Primärquellen-Sektion

```
┌── Primärquellen zu dieser Story ────────────────────────┐
│  Dokumente, auf die sich dieser Beitrag stützt:         │
│                                                         │
│  ● [Protokoll]  Sitzung vom 09.03.1934    [→ Öffnen]   │
│  ● [Dokument]   Brief E. Goldmann         [→ Öffnen]   │
│  ● [Protokoll]  Sitzung vom 15.04.1934    [→ Öffnen]   │
│                                                         │
│  [Alle 7 verknüpften Dokumente anzeigen]               │
└──────────────────────────────────────────────────────────┘
```

**Neues Story-Feld:**

```python
# Erweiterung Story-Modell:
story_type = Column(SQLEnum(StoryType), default=StoryType.COMMUNITY)
# Enum: community (Standard) / editorial (von Admin/Redakteur)
# editorial → wird auf V01 und V02 prominenter platziert
```

**Neues API-Feld:**

```python
# Story-Dokument-Verknüpfung:
class StoryDocumentLink(Base):
    __tablename__ = "story_document_links"
    story_id     = Column(Integer, ForeignKey("stories.id"))
    document_id  = Column(Integer, ForeignKey("documents.id"))
    sort_order   = Column(Integer, default=0)
```

---

## Feature H — „Die stille Welle"
### Austritte als sichtbares Muster

### Kernidee

Auf V02a (Die 30er) gibt es im Amtsstrahl (Feature D) eine zusätzliche
Zeile: Austritte pro Jahr als Balken-Dichte. Kein Label, keine Farbe
außer dem neutralen Epochenton. Die Verdichtung 1933–1935 ist sofort sichtbar.

**Bewertung:** ✅ Ergänzung zu Feature D, kein eigenständiges Feature.
Wird als Teil des Amtsstrahls implementiert, nicht als eigene Komponente.

### ASCII-Layout

```
Austritte  · · ·  ·  ██████████████████████  · · ·
                      1933–1935
```

Darunter ausklappbar:

```
[▼ 14 Austritte in diesem Zeitraum — Details anzeigen]
→ Liste: Datum · Name (wenn öffentlich) · Protokollwortlaut · verknüpfte Dokumente
```

---

## Feature I — Suchfilter Mitgliedschaftsgeschichte
### Gezielte Recherche für Dr. Miriam

### Kernidee

Erweiterung von V05 mit einem Filter für Mitgliedschaftsereignisse —
inkl. Unterfilter für Einträge mit verknüpften Dokumenten.

**Bewertung:** ✅ Notwendig für Dr. Miriam, dezent für alle anderen.
Der Unterfilter „mit verknüpftem Dokument" erscheint nur, wenn solche
Verknüpfungen vorhanden sind — entsteht aus den Daten, nicht aus dem Design.

### Filterstruktur

```
Typ: [Mitgliedschaft ▾]
  ├── Aufnahme
  ├── Austritt
  ├── Amtswechsel
  └── Mit verknüpftem Dokument  ← nur wenn vorhanden
```

---

## Gesamtbewertung & Phasierung

| Feature | Typ | Aufwand | Phase |
|---|---|---|---|
| A — GapInline | Kern-Feature | Gering | MVP |
| B — AttendanceHeatmap | Strukturell | Mittel | Nach T6/P1 |
| C — Consent/Selbstidentifikation | Community | Hoch | Nach T6/P3+Auth |
| D — Amtsstrahl | Strukturell | Mittel | Nach T6/P2 |
| E — Aufnahme/Abgang | Inhaltlich | Mittel | Nach T6/P2 |
| F — Zwei Dokumente | Inhaltlich | Gering-Mittel | Nach T6/P1 |
| G — Story als Eingang | Architektur | Gering | MVP (Frontend-only) |
| H — Stille Welle | Teil von D | — | Mit Feature D |
| I — Suchfilter Mitgliedschaft | Erweiterung | Gering | Nach T6/P2 |

### MVP-Empfehlung (sofort umsetzbar)

1. **Feature A** (GapInline) — nutzt BBox-Daten, die bereits vorhanden sind
2. **Feature G** (Story als Eingang) — nur Frontend, kein neues Datenmodell,
   ein neues Story-Feld (`story_type`) und eine Verknüpfungstabelle
3. **Feature F** (Zwei Dokumente) — eine neue Verknüpfungstabelle,
   kein neuer Entitätstyp, sofort visuell wirkungsvoll

---

*Nächste Aktualisierung: T5-komponenten.md v1.2 mit den neuen Komponenten
MembershipBlock (K04-Erweiterung), DocumentLinkPanel (K05-Erweiterung),
AmtsStrahl (K06-Erweiterung), ConsentProgress (K13), StorySourcePanel (K11-Erweiterung).*
