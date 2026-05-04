# RotaryArchiv — T1.2: Informationsarchitektur

> **Version:** 1.1 — 2026-05-01  
> **Thread:** T1 Konzept & UX  
> **Input für:** T5 Frontend/Design, T6 Coding  
> **Abhängigkeiten:** project-brief.md v0.1, T1-ux-archetypen.md v1.1  
> **Änderungen v1.1:** Epochen → „30er" / „90er"; Zugriffsmodell auf Objekt-Flags umgestellt; anonyme Beiträge mit Moderationspfad ergänzt

---

## Architekturprinzipien

Bevor die einzelnen Views beschrieben werden, gelten folgende **nicht-verhandelbare Designprinzipien**:

1. **Entity-First-Navigation:** Jede Entität (Person, Dokument, Ort, Ereignis) hat eine eigene, stabile URL. Navigation geschieht primär durch Klick auf verknüpfte Entitäten, nicht durch Menüs.
2. **Rabbit-Hole-Prinzip:** Jede Seite muss mindestens 3 ausgehende Querverweise auf verwandte Entitäten haben. Es soll immer etwas Nächstes zu entdecken geben.
3. **Objekt-Flag statt Rollen-Gate:** Sichtbarkeit wird nicht durch Nutzerrollen, sondern durch ein `öffentlich`-Flag auf jedem Objekt gesteuert. Jede Person, jedes Protokoll, jede Story, jeder Ort trägt dieses Flag. Ein nicht-öffentliches Objekt ist für anonyme Besucher unsichtbar oder zeigt einen würdevollen Platzhalter mit Erklärung.
4. **Beiträge ohne Konto möglich:** Jeder Besucher kann Stories einreichen und Korrekturen melden. Ohne Account gehen Beiträge in eine Moderationswarteschlange; eingeloggte Nutzer bekommen sofortige Sichtbarkeit.
5. **Zwei-Epochen-Klarheit:** Die 30er und die 90er sind visuell und inhaltlich differenziert, teilen aber dieselbe IA-Struktur.

---

## Das Zugriffsmodell: Objekt-Flags

Statt starrer Nutzerrollen trägt jedes Objekt im System ein Flag:

```
Objekt-Flag: öffentlich | nicht-öffentlich
```

| Objekt-Typ | Typisches Flag | Flexibel änderbar? |
|---|---|---|
| Personen aus den 30ern | öffentlich | Ja, per Admin |
| Personen aus den 90ern | nicht-öffentlich (Standard) | Ja, einzeln freigebbar |
| Protokolle aus den 30ern | öffentlich | Ja |
| Protokolle aus den 90ern | nicht-öffentlich (Standard) | Ja, einzeln freigebbar |
| Stories (eingereicht) | nicht-öffentlich bis Freigabe | Automatisch nach Review |
| Stories (von eingeloggtem Nutzer) | öffentlich nach Einreichung | Ja |
| Orte, Ereignisse | öffentlich (Standard) | Ja |

**Was sieht ein anonymer Besucher bei einem nicht-öffentlichen Objekt?**  
Kein 403-Fehler. Stattdessen ein Platzhalter: Name des Objekts (wenn der Name selbst nicht sensitiv ist), Epoche, und ein Text wie: *„Dieses Protokoll stammt aus einer Zeit, in der viele der Beteiligten noch leben. Es ist daher nur für eingeloggte Mitglieder zugänglich."* — mit Login-CTA.

**Konsequenz für T6 Coding:** Das Flag ist ein Boolean-Feld (`is_public`) auf jeder relevanten Datenbanktabelle. Die API gibt nicht-öffentliche Objekte für anonyme Requests nicht zurück — oder gibt nur den Stub (Name + Platzhalter-Metadaten) zurück, wenn das UX-seitig gewünscht ist.

---

## Beitragsmodell: Anonyme und eingeloggte Beiträge

```
Beitrag eingereicht
        │
        ├── Eingeloggt?  ──Ja──▶  Direkt sichtbar (je nach Objekt-Flag)
        │
        └── Nein ─────────────▶  Moderationswarteschlange
                                        │
                                  Admin reviewed
                                        │
                          ┌─────────────┴─────────────┐
                        Freigabe                   Ablehnung
                     (wird öffentlich)        (mit optionaler Rückmeldung)
```

**Was darf anonym eingereicht werden?**
- Story zu einer Person, einem Dokument, einem Ereignis
- Korrekturhinweis zu einer Entität (z.B. falscher Name, falsche Zuordnung)
- Ergänzungshinweis (z.B. „Diese Person ist mein Großvater, ich habe weitere Informationen")

**Was ist beim anonymen Einreichen anders?**
- Kein dauerhafter Autorenname (nur optionales Pseudonym / „Anonym")
- Beitrag erscheint mit Label „Eingereicht — wartet auf Freigabe" in der Admin-Ansicht
- Einreicher bekommt optional eine E-Mail-Adresse angeben, um Rückmeldung zu erhalten

---

## Seitenstruktur (Views)

### 🏠 V01 — Startseite / Entdeckung

**Zweck:** Erster Eindruck, emotionaler Einstieg, multiple Einstiegspunkte  
**Primäre Archetypen:** Jannik (Entdeckung), Karoline (Suche), Wolfgang (Login-CTA)

**Elemente:**
- **Hero-Block:** Eine kuratorierte Szene — ein Zitat aus einem Protokoll, ein Datum, ein Name. Wechselt täglich oder redaktionell kuratiert. Kein generisches „Willkommen".
- **Globale Suchleiste:** Prominent, sucht über alle öffentlichen Personen, Dokumente, Orte, Ereignisse.
- **Story-Teaser:** 2–3 aktuelle freigegebene Stories, mit Vorschau und Autorenangabe.
- **Epochen-Einstieg:** Zwei visuelle Kacheln — „Die 30er" und „Die 90er" — mit je einem Teaserbild und Kurztext. Die 90er-Kachel zeigt, wie viele Objekte öffentlich sind, mit Login-CTA für mehr.
- **Entitäten-Zufallspfad:** „Entdecke eine zufällige Person / ein zufälliges Dokument" — nur öffentliche Objekte, für Jannik.
- **Statistik-Widget:** „X Personen erschlossen, Y Dokumente, Z Stories" — zeigt Projektgröße.

---

### 📅 V02 — Epochen-Übersicht

**Zweck:** Kontextualisierung, historische Einbettung, kuratorierter Einstieg  
**Primäre Archetypen:** Dr. Miriam, Jannik

**Zwei Varianten:** `V02a — Die 30er` (weitgehend öffentlich) und `V02b — Die 90er` (teils eingeschränkt)

**Elemente:**
- Kurzer Einführungstext zur Epoche (redaktionell)
- **Hinweis:** In Phase 1 (vor Club-Freigabe) ist V02 primär für den Vorstand (Klaus-Peter), um das Zugriffsmodell zu demonstrieren.
- Historischer Kontext-Block mit expliziten Hinweisen bei sensiblen Inhalten
- Zeitstrahl mit scrollbaren öffentlichen Ereignissen aus dem Triplestore
- Einstieg in Personen-Übersicht dieser Epoche (nur öffentliche Objekte)
- Einstieg in Dokument-Übersicht (nur öffentliche Objekte)
- In V02b: Hinweis auf Anzahl nicht-öffentlicher Objekte + Login-CTA

---

### 👤 V03 — Personenprofil

**Zweck:** Zentraler Rabbit-Hole-Hub, tiefste individuelle Recherche  
**Primäre Archetypen:** Karoline, Dr. Miriam

**Nur für öffentliche Personen-Objekte. Nicht-öffentliche Personen → Platzhalter.**

**Elemente:**
- Name, Lebensdaten (soweit bekannt), Ämter und Rollen im Club
- Wikidata-Infopanel: externe Hintergrunddaten (wenn verknüpft)
- **Zeitstrahl der Erwähnungen:** Protokolle, die diese Person erwähnen — mit Datum und Snippet
- Zitierte Stellen: Transkribierte Textausschnitte mit Link zum Quelldokument
- Netzwerk-Mini-Graph: Welche anderen Personen werden in denselben Protokollen erwähnt?
- Ämter und Rollen (aus Triplestore)
- Community-Beiträge zur Person (freigegebene Stories und Korrekturen)
- **Beitragsbutton:** „Ich kenne mehr über diese Person" — ohne Login möglich (→ Moderationspfad)
- **Korrekturlink:** „Stimmt etwas nicht?" — ohne Login möglich (→ Moderationspfad)
- Verwandte Personen, Orte, Ereignisse als weiterführende Links

---

### 📄 V04 — Dokumentansicht / Protokoll

**Zweck:** Primärquellenansicht, Quellenarbeit für Forscher  
**Primäre Archetypen:** Dr. Miriam, Karoline

**Nur für öffentliche Dokument-Objekte. Nicht-öffentliche Dokumente → Platzhalter mit Erklärung.**

**Elemente:**
- Metadaten-Header: Datum, Sitzungsnummer, Erschließungsstand
- **Dual-View:** Links Transkription, rechts Scan (sofern öffentlich)
- Hervorgehobene Entitäten im Text: Personen, Orte, Ereignisse sind klickbar (Triplestore-Links)
- Historische Kontextnotiz (wenn redaktionell vorhanden)
- Dokument-Navigation: Vorheriges / nächstes Protokoll in der Zeitlinie
- Export / Zitation: BibTeX, Zitatvorlage, persistente URL
- Community-Annotationen (freigegebene Stories und Korrekturen zu diesem Dokument)
- **Beitragsbutton:** Ohne Login möglich (→ Moderationspfad)

---

### 🔍 V05 — Suche & Exploration

**Zweck:** Gezielte Recherche, Filterung, Ergebnisliste  
**Primäre Archetypen:** Dr. Miriam, Karoline

**Sucht nur über öffentliche Objekte (für anonyme Besucher). Eingeloggte Nutzer sehen zusätzlich nicht-öffentliche Objekte, auf die ihr Account Zugang hat.**

**Elemente:**
- Volltext-Suche mit Autovervollständigung (Triplestore-Entitäten)
- Filterleiste: Epoche (30er / 90er), Entitätstyp, Datum
- Ergebnisliste mit Snippet-Vorschau
- Leerzustand als Einladung: „Diese Person ist noch nicht erschlossen. Wissen Sie etwas darüber?"
- Gespeicherte Suchen (nur eingeloggt)

---

### 🗺️ V06 — Karten-Ansicht

**Zweck:** Geografische Exploration  
**Primäre Archetypen:** Jannik, Dr. Miriam

**Elemente:**
- Interaktive Karte (Leaflet — bereits im Stack)
- Marker für öffentliche Orte aus dem Triplestore
- Klick auf Marker → Ortsdetailpanel mit verknüpften Personen und Dokumenten
- Toggle: „30er" / „90er" / „Beide"
- Heatmap-Option: Häufigkeit der Erwähnung

---

### 🕸️ V07 — Netzwerk-Graph

**Zweck:** Beziehungsvisualisierung, strukturelle Forschung  
**Primäre Archetypen:** Dr. Miriam, Jannik

**Elemente:**
- Interaktiver Force-Directed-Graph: öffentliche Personen als Knoten, Verbindungen aus gemeinsamen Protokollen
- Farbkodierung: Epoche, Amt, Erschließungsstand
- Klick auf Knoten → Personenprofil (V03)
- Filter: Zeitraum, Mindestanzahl gemeinsamer Dokumente
- Nicht-öffentliche Personen erscheinen als anonymisierte Knoten (nur Anzahl, kein Name)

---

### 📖 V08 — Story-Detail

**Zweck:** Kuratorierte Erzählung, Community-Beitrag lesen  
**Primäre Archetypen:** Jannik, Karoline, Wolfgang

**Nur für freigegebene / öffentliche Stories.**

**Elemente:**
- Titel, Autor (Name oder „Anonym"), Datum der Veröffentlichung
- Fließtext mit eingebetteten Entitäts-Links
- Verknüpfte Quellen: Protokollauszüge, auf die sich die Story stützt
- Weiterlesen-Empfehlungen (andere Stories, verwandte Personen)
- **Kommentar / Ergänzung:** Ohne Login möglich (→ Moderationspfad)

---

### ✍️ V09 — Story einreichen (öffentlich)

**Zweck:** Community-Beitrag, niedrigschwellig  
**Primäre Archetypen:** Karoline, Wolfgang, Dr. Miriam

**Kein Login erforderlich. Beitrag geht je nach Login-Status direkt live oder in die Moderationswarteschlange.**

**Elemente:**
- Strukturiertes Formular: Titel, Fließtext, verknüpfte Entitäten (Auswahl aus öffentlichem Triplestore)
- Quellen-Verknüpfung: Protokolle als Belege einfügen
- Optionales Pseudonym / Name / E-Mail für Rückmeldung
- Klarer Status-Hinweis: „Ohne Konto wird dein Beitrag vor Veröffentlichung von einem Admin geprüft. Das dauert typischerweise X Tage."
- Vorschau-Modus
- Hinweis auf Lizenz / Nutzungsrechte

---

### 🔧 V10 — Korrektur / Hinweis einreichen (öffentlich)

**Zweck:** Qualitätssicherung durch Community, niedrigschwellig  
**Primäre Archetypen:** Wolfgang, Karoline

**Kein Login erforderlich. Gleicher Moderationspfad wie V09.**

**Elemente:**
- Bezug auf ein konkretes Objekt (vorausgefüllt, wenn von Objekt-Seite aufgerufen)
- Freitext: Was ist falsch / was sollte ergänzt werden?
- Optionale Kontakt-E-Mail
- Status-Hinweis analog V09

---

### 👤 V11 — Nutzerprofil / Mein Bereich (nur eingeloggt)

**Zweck:** Personalisierung, eigene Beiträge verwalten  
**Primäre Archetypen:** Wolfgang, Dr. Miriam

**Elemente:**
- Eigene eingereichte Stories und ihr Status (Entwurf / Eingereicht / Live)
- Gemeldete Korrekturen und ihr Bearbeitungsstand
- Gespeicherte Suchen und gemerkte Entitäten
- Profilangabe: Name, Mitgliedschaft (für Quellenangabe in Stories)

---

### ℹ️ V12 — Über das Projekt

**Zweck:** Vertrauen aufbauen, Methodik erklären, Mitmachen einladen  
**Primäre Archetypen:** Alle

**Elemente:**
- Projektgeschichte und -ziel
- Erklärung der Erschließungsmethode (OCR, Triplestore, Wikidata)
- Hinweis auf den historisch sensiblen Zeitraum der 30er und die redaktionelle Haltung des Clubs
- Erklärung des Zugriffsmodells: Warum sind manche Inhalte nicht öffentlich? (Persönlichkeitsrechte)
- Team und Kontakt
- Mitmachen: Wie kann man beitragen — mit und ohne Account?
- Datenschutz'''

new_v12 = '''### ℹ️ V12 — Über das Projekt

> **Änderung v1.2 — 2026-05-03:** V12 hat eine erweiterte Funktion als Vertrauensdokument für den Vorstand-Archetypen (Klaus-Peter). Zwei neue Pflicht-Abschnitte ergänzt.

**Zweck:** Vertrauen aufbauen, Methodik erklären, Mitmachen einladen — und in Phase 1 den Vorstand überzeugen  
**Primäre Archetypen:** Alle — mit besonderer Relevanz für Klaus-Peter (Vorstand)

**Elemente:**
- Projektgeschichte und -ziel
- Erklärung der Erschließungsmethode (OCR, Triplestore, Wikidata)
- Hinweis auf den historisch sensiblen Zeitraum der 30er und die redaktionelle Haltung des Clubs
- Erklärung des Zugriffsmodells: Warum sind manche Inhalte nicht öffentlich? (Persönlichkeitsrechte)
- Team und Kontakt
- Mitmachen: Wie kann man beitragen — mit und ohne Account?
- Datenschutz

**Neuer Pflicht-Abschnitt: „Was der Club kontrolliert"**

Dieser Abschnitt richtet sich explizit an den Vorstand. Er erklärt das `is_public`-Modell nicht technisch, sondern als Kontrollversprechen in alltagsverständlicher Sprache:

> *„Kein Inhalt wird öffentlich sichtbar, ohne dass der Club das aktiv entschieden hat. Jede Person, jedes Protokoll, jede Story trägt eine Freigabe — die der Club jederzeit erteilen oder zurückziehen kann. Die 90er sind standardmäßig vollständig geschützt. Die 30er sind öffentlich, weil die Beteiligten nicht mehr leben und ihre Geschichte Teil des kollektiven Gedächtnisses ist."*

Dieser Abschnitt muss ohne technisches Vorwissen verständlich sein. Kein Code, kein Admin-Vokabular. Ein einfaches Beispiel (z.B. eine fiktive Person mit Toggle „sichtbar / nicht sichtbar") kann helfen.

**Neuer Pflicht-Abschnitt: „Was wir nicht zeigen ohne Freigabe"**

Dieser Abschnitt operationalisiert das Vertrauen durch eine explizite, negative Aufzählung — was das System *nicht* tut:

- Wir zeigen keine Namen lebender Mitglieder ohne deren Einwilligung oder Club-Freigabe
- Wir veröffentlichen keine Protokolle aus den 90ern ohne explizite Freigabe pro Dokument
- Wir erlauben keine anonymen Beiträge über lebende Personen ohne Moderation
- Wir verknüpfen keine externen Daten (z.B. Wikidata) für Personen der 90er ohne Prüfung
- Wir geben keine Daten an Dritte weiter

Ton dieses Abschnitts: ruhig, nicht defensiv. Nicht „wir dürfen nicht", sondern „wir haben uns entschieden, nicht". Das ist ein Unterschied in Haltung, der Vertrauen aufbaut.

**Gestaltungshinweis für T5:**  
V12 darf in Phase 1 die am sorgfältigsten gestaltete Seite des Frontends sein. Sie ist die Seite, die Klaus-Peter in der Vorstandssitzung aufruft. Jede Formulierung, jeder Abstand, jede Überschrift signalisiert: *Wir haben uns das überlegt.*'''

---

## Navigationsstruktur

```
Globale Navigation (immer sichtbar)
├── 🔍 Suche (global, alle öffentlichen Entitäten)
├── Entdecken
│   ├── Die 30er
│   ├── Die 90er
│   ├── Karte
│   └── Netzwerk
├── Stöbern
│   ├── Personen
│   ├── Dokumente
│   └── Orte & Ereignisse
├── Stories
│   ├── Alle Stories lesen
│   └── Story einreichen  ← kein Login nötig
├── Über das Projekt
└── Login / Mein Bereich
```

---

## URL-Schema (empfohlen für T6)

```
/                           → V01 Startseite
/epoche/30er                → V02a Epochen-Übersicht 30er
/epoche/90er                → V02b Epochen-Übersicht 90er
/person/{slug}              → V03 Personenprofil
/dokument/{id}              → V04 Dokumentansicht
/suche?q=...                → V05 Suche
/karte                      → V06 Karte
/netzwerk                   → V07 Netzwerk-Graph
/story/{slug}               → V08 Story-Detail
/story/neu                  → V09 Story einreichen
/korrektur/{objekt-id}      → V10 Korrektur einreichen
/profil                     → V11 Nutzerprofil
/ueber                      → V12 Über das Projekt
```

**Persistenz-Anforderung:** `/person/{slug}` und `/dokument/{id}` müssen dauerhaft stabile URLs sein — sie werden zitiert und geteilt. Slugs für Personen sollten sprechend und menschenlesbar sein (z.B. `/person/karl-mueller-1887`).

---

## Rabbit-Hole-Pfade (exemplarisch)

**Pfad Karoline (ohne Login):**  
`Startseite → Suche „Müller" → Personenprofil Karl Müller → Protokoll 1931-04-15 → nächstes Protokoll → verwandte Person → Ort Dresden-Neustadt → Karte → „Ich kenne mehr" (anonym einreichen)`

**Pfad Jannik (ohne Login):**  
`Startseite (Hero-Zitat) → Epochen-Übersicht 30er → Zufalls-Person → Netzwerk-Graph → Story → Teilen`

**Pfad Dr. Miriam (eingeloggt):**  
`Suche „Bürgermeister" → Gefilterte Ergebnisliste → Dokument mit Volltext → Export BibTeX → Personenprofil → Netzwerk → gefiltert 1930–1933`

**Pfad Wolfgang (eingeloggt, 90er sichtbar):**  
`Login → Epoche 90er (jetzt sichtbar) → Eigener Name in Suche → Personenprofil → Protokoll 1998 → Korrektur einreichen (sofort live) → Story einreichen`

---

## Datenmodell-Anforderungen (Input für T2)

Die IA erzeugt folgende Anforderungen an das Datenmodell und die API:

| Anforderung | View | Triplestore / DB |
|---|---|---|
| `is_public`-Flag auf Person, Dokument, Story, Ort, Ereignis | Alle | DB: Boolean-Feld |
| Beitragsstatus: `Entwurf / Eingereicht / Freigegeben / Abgelehnt` | V09, V10, V11 | DB: Enum-Feld |
| Optionale Kontakt-E-Mail bei anonymem Beitrag | V09, V10 | DB: verschlüsselt speichern |
| Stabile Slugs für Personen | V03 | DB: eindeutiger Slug-Index |
| Triplestore: Netzwerk-Abfrage (Person → gemeinsame Dokumente → andere Personen) | V07 | Triplestore: SPARQL-ähnlich |
| Triplestore: Zeitstrahl-Abfrage (Person → alle Erwähnungen mit Datum) | V03 | Triplestore |
| Wikidata-Verknüpfung für Personen-Infopanel | V03 | Wikidata-Sync bereits vorhanden |
| Export-Endpoint: BibTeX / Zitat-Text für Dokumente | V04 | API: neuer Endpoint |
