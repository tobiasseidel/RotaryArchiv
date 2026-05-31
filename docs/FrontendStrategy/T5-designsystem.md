# T5-designsystem.md — Visuelles Fundament RotaryArchiv

> **Version:** 1.0 — 2026-05-02
> **Thread:** T5 Frontend/Design
> **Phase:** 2 — Designsystem
> **Input aus:** T1-emotionaler-kern.md, T1-ux-archetypen.md, project-brief_v04.md
> **Status:** Fertig

---

## Leitprinzip für alle Entscheidungen

> „RotaryArchiv ist der Ort, an dem vergessene Namen wieder zu Menschen werden."

Jede Entscheidung in diesem Dokument wird daran gemessen.
Nicht: „Sieht professionell aus."
Sondern: „Hilft das dabei, dass ein Name im Interface zu einer Person wird?"

---

## 1. Typografie

### Entscheidung

**Zwei-Schrift-System:**

| Rolle | Familie | Quelle | Begründung |
|---|---|---|---|
| **Primär — Lesetext, Zitate, Protokolle** | **Lora** | Google Fonts (OFL) | Humanistische Serifenschrift, entwickelt für Bildschirmlesen. Warm, buchförmig, mit archivarischem Charakter — ohne historisierende Karikatur. |
| **Sekundär — Navigation, Labels, UI** | **Inter** | Google Fonts (OFL) | Neutrale, hoch optimierte Interface-Schrift. Klare Hierarchie, ausgezeichnete Lesbarkeit bei kleinen Größen. Ergänzt Lora, konkurriert nicht. |

**Warum Lora, nicht Playfair Display?**
Playfair Display ist schön, aber theatralisch — es betont historisches Flair als Ästhetik,
nicht als Inhalt. Lora ist zurückhaltender: sie transportiert Würde, ohne die Vergangenheit
zu verniedlichen. Sie ist das typografische Äquivalent zu gut gealtertem Papier, nicht
zu einem Theaterplakat.

**Warum Inter, nicht Source Sans oder Nunito?**
Inter ist auf pixel-genaue Bildschirmausgabe optimiert und hat exzellente Zeichensätze
für Deutsch (ß, Umlaute). Nunito wäre zu rund und freundlich — das Interface soll
ehrlich sein, nicht niedlich.

### Typografische Skala

```
Lora, font-size scale (rem, base 16px):

Display     — 2.5rem / 40px   — V01 Hero-Zitat, Epochen-Titel
H1          — 2.0rem / 32px   — Personenname, Dokumenttitel
H2          — 1.5rem / 24px   — Abschnittstitel
H3          — 1.25rem / 20px  — Kartenüberschriften, Zeitstrahl-Marker
Body        — 1.0rem / 16px   — Fließtext, Transkriptionen
Caption     — 0.875rem / 14px — Metadaten, Quellenangaben

Inter, font-size scale:

Nav         — 0.9375rem / 15px — Navigationslabels
Label       — 0.875rem / 14px  — Formularfelder, Filter, Tags
Micro       — 0.75rem / 12px   — Zeitstempel, Badges
```

### Lesbarkeitsregeln (nicht verhandelbar)

- **Zeilenlänge Protokolltexte:** 60–70 Zeichen. Danach Zeilenumbruch. Kein Vollbreite-Text.
- **Zeilenabstand Fließtext:** `line-height: 1.75` für Protokollinhalte, `1.5` für UI-Text.
- **Mindestkontrast:** WCAG AA für alle Texte auf Hintergründen — kein Kompromiss.
- **Kerning:** `font-kerning: normal` — Lora profitiert von natürlichem Kern.
- **Protokolltext:** Immer Lora, immer 16px+, Kursiv nur für Zitate und historische
  Hervorhebungen — nicht für UI-Text.

---

## 2. Farbpalette

### Designprinzip

Die Farben sollen archivarische Wärme transportieren, ohne in Sepia-Klischee zu verfallen.
Das Fundament ist ein **gebrochenes Creme** — das Äquivalent zu gut erhaltenem,
aber nicht neuem Papier. Keine grellen Primärfarben, kein Tech-Blau.

### Basispalette (epochenübergreifend)

```
Hintergrund   —  #F5F0E8   „Altes Papier"      — warmes Off-White, nie reinweiß
Surface       —  #FDFAF5   „Frisches Papier"   — für Cards, Overlays, Modal-Hintergründe
Text Primär   —  #1C1917   „Tinte"             — fast Schwarz, warmer Ton (kein Kaltgrau)
Text Sekundär —  #57534E   „Verblasste Tinte"  — Metadaten, Labels, Captions
Trennlinie    —  #D6CFC4   „Falzlinie"         — dezente Trenner, Rahmen
```

### Epochenfarbe: Die 30er (1927–1937)

```
Primärfarbe   —  #2C4A3E   „Archivgrün"        — tiefes, gediegenes Dunkelgrün.
                                                  Farbe alter Archivmappen, Schreibtisch-
                                                  unterlagen der Weimarer Republik.
                                                  Ernst, nicht kalt.
Akzent        —  #8B7355   „Briefpapier-Ocker" — warmes Braun-Ocker für Hervorhebungen,
                                                  Hover-States, aktive Zeitstrahlelemente.
Tag/Badge     —  #E8E0D4   „Archivgrau"        — für Epochen-Badges in dieser Sektion
```

**Warum Dunkelgrün für die 30er?**
Weil es die Farbe von Aktendeckeln, Schreibtischunterlagen und Bibliotheksregalen der
Zwischenkriegszeit ist — nicht der NS-Ästhetik. Es ist gediegenes bürgerliches Grün:
der Rotary Club der 30er war eine Bürgerorganisation in der Weimarer Republik.
Die Farbe kommuniziert historisches Gewicht ohne Dramatisierung.

### Epochenfarbe: Die 90er (1990–2008)

```
Primärfarbe   —  #1A3A5C   „Mauerfall-Blau"   — dunkles Mitternachtsblau.
                                                 Näher, persönlicher, moderner.
                                                 Bürotinte der 90er, blaue Ordner.
Akzent        —  #7A6E8A   „Wendegrau-Lila"   — gedämpftes Blauviolett für Hervorhebungen.
                                                 Zeitlos für die 90er, ohne Pop-Klischee.
Tag/Badge     —  #E0E4EC   „Aktenheftgrau"    — für Epochen-Badges in dieser Sektion
```

**Warum Mitternachtsblau für die 90er?**
Die 90er in Dresden sind eine persönlichere, lebhaftere Epoche — aber noch keine Gegenwart.
Blau kommuniziert Nähe und Zugänglichkeit gegenüber dem Dunkelgrün der 30er, ohne dass
es wie ein modernes Tech-Portal aussieht. Wolfgang (der Insider der 90er) soll sich
sofort orientieren können: das ist seine Zeit.

### Wie unterscheiden sich die Epochen visuell ohne zwei komplett verschiedene Designs?

Das Basisdesign bleibt identisch. Die Epochenfarbe tritt auf drei definierten Ebenen auf:

1. **Akzentlinie:** Ein 3px-Streifen am linken Rand von Epochen-Cards und im Page-Header
2. **Hover-State:** Aktive Links und Hover-Zustände erhalten die Epochenfarbe
3. **Badge-Farbe:** Epochen-Tags haben den jeweiligen Hintergrundton

Alles andere — Hintergrund, Typografie, Spacing, Komponenten-Shapes — bleibt unverändert.

### Funktionale Farben

```
Erfolg        —  #3B6E4A   — grünlich, harmoniert mit Archivgrün
Warnung       —  #92640A   — warmes Ocker, kein grelles Gelb
Fehler        —  #8B2E2E   — gedämpftes Rot. Nie grell.
Stub/Gesperrt —  #A09890   — mittleres Neutralgrau. Platzhalter sind NICHT rot.
                             Sie sind ruhig, würdevoll, erklärend.
```

### Was niemals passiert

- Kein `#0000FF`-Blau für Links — alle Links erhalten die epochenspezifische Akzentfarbe
- Kein weißer (`#FFFFFF`) Hintergrund — immer warmes Creme (`#F5F0E8`)
- Keine Fehlerfarbe bei nicht-öffentlichen Inhalten — `Stub/Gesperrt` ist neutral
- Kein Schwarz bei Borders — immer `Trennlinie #D6CFC4`

---

## 3. Bildsprache

### Grundregel: Authentizität vor Ästhetik

Das Material ist echt. Scanartefakte, leicht vergilbtes Papier, ungleichmäßige
Druckdichte — das ist kein Problem, das korrigiert werden muss. Es ist der Beweis
der Echtheit. Kein künstlicher Sepia-Filter. Keine Vignettierung. Keine Vintage-Effekte.

### Portraits

```
Behandlung:
- Leicht desaturiert (Sättigung -20 bis -30%), nicht vollständig schwarzweiß.
  Begründung: Erhält die menschliche Wärme (Hauttöne bleiben spürbar),
  reduziert aber Fremdartigkeit bei Farbfotos neben historischen Dokumenten.
- Kein Filter, keine Körnung, keine künstliche Alterung.
- Aspect ratio: immer 3:4 (Hochformat), nie quadratisch.
  Portraits von Menschen verdienen Würde — quadratische Thumbnails degradieren
  Gesichter zu Icons.
- Bei fehlendem Bild: KEIN Silhouetten-Icon. Stattdessen: initialen-basierter
  Placeholder mit dem Epochen-Hintergrundton.
```

**Gemeinfreie Bilder / Bilder mit Einwilligung:**
Werden im Original angezeigt (mit leichter Desaturierung wenn Farbfoto).

**Bilder mit ungeklärten Rechten:**
Werden NICHT angezeigt. Stattdessen: Initialen-Placeholder + kurzer Hinweis
„Bildrechte ungeklärt — bisher kein Bild verfügbar."

### Scan-Dokumente

```
Behandlung:
- Originalfarbigkeit beibehalten (meist gelbliches Papier + schwarze Tinte).
- Kein Weißabgleich. Der Scan soll wie ein Scan aussehen.
- Einbettung in einem leichten CSS-Rahmen:
  box-shadow: 0 4px 24px rgba(28, 25, 23, 0.12);
  — simuliert das Aufliegen eines Dokuments, nicht einen Screenshot.
- Bei Dual-View (Scan + Transkription): Scan auf Surface-Hintergrund (#FDFAF5),
  damit er sich als physisches Objekt liest.
```

### Karten / Leaflet-Kartenansicht

```
- Kartenstil: CartoDB Voyager (kostenlos, hell, zurückhaltend) —
  harmoniert mit der Farbpalette.
- Marker: Epoch-spezifische Farbe (#2C4A3E / #1A3A5C), Kreis mit weißem Rand.
- Kein buntes Standard-Leaflet-Blau.
```

---

## 4. Spacing & Grid

### Grid-System

```
Desktop (≥1024px):
- 12-Spalten-Grid, max-width: 1200px, margin: auto
- Gutter: 24px
- Hauptspalte Lesecontent: 8 von 12 Spalten (66%), rechte Sidebar: 4 von 12
- Bei reiner Vollseite (Karte, Netzwerk): 12/12

Tablet (768–1023px):
- 8-Spalten-Grid
- Hauptspalte: 6/8, Sidebar darunter stapeln

Mobile (< 768px):
- 4-Spalten-Grid (single-column-first)
- Sidebar wird zu eigenem Abschnitt unterhalb des Hauptinhalts
- Dual-View (Scan + Transkription): Tabs statt nebeneinander
- Netzwerk-Graph: vereinfachte Version oder explizite „Besser auf Desktop"-Meldung
```

**Warum 1200px max-width?**
Breite Viewports mit Vollbreite-Text erzeugen unleserliche Zeilenlängen.
1200px ist das Maximum, das bei Protokolltexten noch kontrollierte Zeilenlängen
(60–70 Zeichen) in einer 8-Spalten-Hauptspalte erlaubt.

### Spacing-Skala (8px-Basis)

```
4px   — Micro  (Icon-Abstände, Badge-Padding)
8px   — XS     (Inline-Abstände, Inputfeld-Padding)
16px  — S      (Komponenteninterne Abstände)
24px  — M      (Card-Padding, Section-Innenabstände)
40px  — L      (Zwischen Hauptsektionen)
64px  — XL     (Seiten-Hero-Bereiche, große Zwischenräume)
96px  — XXL    (Epochenübergänge auf der Startseite)
```

**Warum viel Weißraum?**
Weil Würde Luft braucht. Protokolltext ist keine Produktbeschreibung.
Wer einen Namen aus den 30ern liest, braucht Atemraum, um ihn zu einem Menschen
werden zu lassen. Enge Abstände würden das sabotieren.

---

## 5. Nicht-öffentliche Inhalte — Platzhalter-Konzept

Dies ist eine der wichtigsten Designentscheidungen des gesamten Projekts.

### Grundregel

> Nicht-öffentliche Inhalte sind **niemals ein Fehlerzustand**.
> Sie sind eine **würdevolle Erklärung mit einer Einladung**.

### Visuelles Konzept

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ░░░  [INITIALEN]  ░░░░░░░░░░░░░░░░░░░             │
│                                                     │
│   Diese Person aus den 90er Jahren ist im           │
│   Archiv erfasst, aber noch nicht öffentlich        │
│   zugänglich.                                       │
│                                                     │
│   Viele der Beteiligten leben noch. Wir             │
│   respektieren ihre Persönlichkeitsrechte.          │
│                                                     │
│   → Einloggen, um mehr zu sehen                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**CSS-Regeln:**
- Hintergrundton: `#F0EBE3` (etwas dunkler als Seite, nie grau-kalt)
- Keine Schloss-Icons, keine roten Ränder, keine Warn-Farben
- Text in `Text Sekundär (#57534E)`, nicht in Grau
- Der Name der Person KANN angezeigt werden, wenn er nicht sensitiv ist
  (API liefert Stub mit `display_name`)

### Epochenspezifische Texte

**30er (ungeplanter Fall, z.B. durch Admin gesperrt):**
„Dieses Dokument ist derzeit nicht zugänglich. Bitte wenden Sie sich an das Projektteam."

**90er (Standard-Fall):**
„Diese Protokolle stammen aus einer Zeit, in der viele der Beteiligten noch leben.
Aus Rücksicht auf ihre Persönlichkeitsrechte sind sie nur für eingeloggte Mitglieder
zugänglich. [Einloggen]"

---

## 6. Interaktionszustände

### Hover

```
- Links im Fließtext: Unterstrichen + Epochenfarbe (kein reines Blau)
- EntityCards: leichter box-shadow-Anstieg (0 8px 32px rgba(28,25,23,0.15))
  + 2px Epochenfarbe-Rand links
- Buttons: 10% dunkler als Ruhezustand, kein Outline-Effekt

Transition: 150ms ease-in-out.
```

### Fokus (Accessibility)

```
- Alle interaktiven Elemente: outline: 2px solid [Epochenfarbe], outline-offset: 3px
- Keine outline: none-Overrides. Niemals.
```

### Ladezeiten / Skeleton-States

```
- Skeleton-Animation: pulsierendes #E8E2D9 → #D6CFC4 (warme Töne, nie Grau)
- Kein Spinner für Seitenübergänge — nur für lokale Komponenten
- Seitenübergang: 200ms fade-in auf page-root-Ebene
```

---

## 7. Sonderfall: Historisch sensible Inhalte

Für Dokumente aus dem Zeitraum 1933–1937 und beim Vereinsausschluss 1937:

```
HistoricalContextBox:

┌── [Kontexthinweis] ─────────────────────────────────┐
│ Dieses Dokument stammt aus dem Jahr 1934.           │
│ Der Rotary Club Dresden wurde 1937 durch das        │
│ NS-Regime aufgelöst. Diese Protokolle sind          │
│ Zeugnisse einer bürgerlichen Vereinskultur kurz     │
│ vor ihrem erzwungenen Ende.                         │
└─────────────────────────────────────────────────────┘

Styling: linker Border 3px in Ocker (#8B7355), kein roter Alarm-Stil.
         Typografie: Lora Kursiv, Text Sekundär. Leise, nicht schockierend.
         Platzierung: unterhalb des Metadaten-Headers, vor dem Haupttext.
```

---

## 8. Design-Token-Übersicht (für T6 Coding)

```css
:root {
  /* Basis */
  --color-bg:             #F5F0E8;
  --color-surface:        #FDFAF5;
  --color-text-primary:   #1C1917;
  --color-text-secondary: #57534E;
  --color-border:         #D6CFC4;
  --color-stub:           #A09890;

  /* Epochen — werden per Klasse überschrieben */
  --color-epoch-primary:  #2C4A3E;   /* Default: 30er */
  --color-epoch-accent:   #8B7355;
  --color-epoch-badge:    #E8E0D4;

  /* Funktional */
  --color-success:        #3B6E4A;
  --color-warning:        #92640A;
  --color-error:          #8B2E2E;

  /* Typografie */
  --font-serif:           'Lora', Georgia, serif;
  --font-sans:            'Inter', system-ui, sans-serif;

  /* Spacing */
  --space-xs:    4px;
  --space-s:     8px;
  --space-m:    16px;
  --space-l:    24px;
  --space-xl:   40px;
  --space-2xl:  64px;
  --space-3xl:  96px;

  /* Grid */
  --grid-max:    1200px;
  --grid-gutter:   24px;

  /* Transitions */
  --transition-fast: 150ms ease-in-out;
  --transition-page: 200ms ease-in;
}

/* Epochen-Override: Die 30er */
.epoch-30er {
  --color-epoch-primary: #2C4A3E;
  --color-epoch-accent:  #8B7355;
  --color-epoch-badge:   #E8E0D4;
}

/* Epochen-Override: Die 90er */
.epoch-90er {
  --color-epoch-primary: #1A3A5C;
  --color-epoch-accent:  #7A6E8A;
  --color-epoch-badge:   #E0E4EC;
}
```
