# T8-iterationsauftraege.md
# Iterationsaufträge aus kuratorischem Gutachten

> **Version:** 1.1 — 2026-05-03
> **Thread:** T8 Kurator / Historiker
> **Grundlage:** T8-kuratorisches-gutachten.md
> **Adressaten:** T1 (Konzept & UX), T5 (Frontend/Design)
> **Hinweis:** Aufträge sind nach Adressat und Priorität geordnet.
>   Priorität A = vor erstem öffentlichen Release unbedingt nötig.
>   Priorität B = vor breiterem Rollout nötig.
>   Priorität C = empfohlen, bei Kapazität.

---

## AUFTRÄGE AN T1 (Konzept & UX)

---

### T1-IT-01 — Binnendifferenzierung der 30er-Epoche

**Gutachten-Bezug:** Befund 1.1 (⚠️), Befund 4.1 (verknüpft)
**Datei:** T1-informationsarchitektur.md
**Abschnitt:** V02 Epochen-Übersicht — Beschreibung der 30er-Ansicht
**Priorität:** A

**Was zu ändern ist:**
Ergänze in der Beschreibung von V02a (Die 30er) einen Pflicht-Inhaltsblock:
Kuratorischer Einführungstext, der **vor** dem Amtsstrahl erscheint und
explizit zwei Phasen benennt:

- Phase 1 (1927–1932): Gründungsphase in der Weimarer Republik
- Phase 2 (1933–1937): Fortbestand und erzwungenes Ende unter NS-Herrschaft

Dieser Text ist kein Feature, kein neues Datenmodell — er ist ein
redaktioneller Pflichtbestandteil von V02a, der einmalig verfasst und
statisch eingebettet wird.

**Format der Änderung in T1-informationsarchitektur.md:**
Füge unterhalb der V02-Beschreibung hinzu:
> Pflichtbestandteil V02a: `<EpochenEinleitung>` — statischer redaktioneller Text,
> sichtbar vor dem Amtsstrahl. Enthält explizite Phasenbeschreibung 1927–1932 /
> 1933–1937. Wird einmalig LLM-generiert und vom Projektinhaber freigegeben.

---

### T1-IT-02 — Drei-Stufen-Pflichtigkeit für Kontexthinweis bei Austritt (Feature E)

**Gutachten-Bezug:** Befund 1.4 (⚠️)
**Datei:** T1-emotionaler-kern.md
**Abschnitt:** „Historische Sensibilität — Tonalität bei schwierigen Inhalten"
**Priorität:** A

**Was zu ändern ist:**
Die aktuelle Formulierung lässt Kontextboxen vollständig im Admin-Ermessen.
Ergänze einen Regelabschnitt „Pflichtstruktur für Kontexthinweise", der definiert:

**Stufe 1 — Automatisch zwingend (kein Admin-Aufwand):**
Jedes Austrittsereignis (MembershipEvent.event_type = leave) mit Datum
zwischen 01.01.1933 und 31.12.1937 erhält automatisch den **generischen
Epochenkontext-Template-Text**. Dieser Text kann vom Admin durch einen
spezifischeren Text ersetzt, aber **nicht deaktiviert** werden.

**Stufe 2 — Automatisch verstärkt (kein Admin-Aufwand):**
Wenn `protocol_wording` die Muster „persönliche Gründe", „berufliche Gründe",
„familiäre Gründe" o.ä. enthält: Zusatz zum generischen Text mit Hinweis auf
die zeitgenössische Verwendung dieser Formeln als Euphemismus.

**Stufe 3 — Manuell optional:**
Alle anderen Fälle: Admin-Entscheidung wie bisher.

Füge außerdem hinzu: **Texttemplate-Pflicht** — das Projektteam muss vor
dem Launch einmalig den generischen Epochenkontext-Text für Stufe 1 und 2
verfassen und im System hinterlegen. Empfehlung: LLM-Entwurf, menschliche
Freigabe.

---

### T1-IT-03 — Kuratorisches Statement als Pflichtbestandteil

**Gutachten-Bezug:** Befund 2.3 (❌), Befund 4.2 (verknüpft)
**Datei:** T1-informationsarchitektur.md
**Abschnitt:** V12 Über das Projekt
**Priorität:** A

**Was zu ändern ist:**
V12 muss um einen Pflichtabschnitt „Kuratorisches Statement" erweitert werden.
Dieser Abschnitt ist kein generischer „Über uns"-Text, sondern ein explizites
kuratorisches Rahmendokument (400–600 Wörter) mit folgenden Pflichtinhalten:

1. **Quellenlage:** Welche Quellen liegen vor, welche fehlen systematisch?
2. **Auswahlprinzipien:** Nach welchen Kriterien wird entschieden, was gezeigt wird?
3. **Strukturelle Blindstellen:** Was kann dieses Archiv nicht abbilden —
   und warum? (Explizit: fehlende Frauenperspektive, Außenperspektive auf den Club,
   Schicksale von Personen außerhalb der Mitgliederprotokolle)
4. **Haltung:** Wie geht das Archiv mit widersprüchlichen Quellen um?
   Wie mit historisch belasteten Personen?
5. **Sichtbarkeit ≠ Rehabilitation:** Expliziter Satz, dass die Aufnahme in
   das Archiv keine Wertung der Person darstellt.

**Arbeitsweg:** LLM-Entwurf auf Basis des Projektbriefs und dieses Gutachtens,
Freigabe durch Projektinhaber. Kein laufender Aufwand.

**Verknüpfung mit T5:** V12-View braucht eine neue, permanent sichtbare
Sektion für diesen Text — keine versteckte Unterseite.

> **Notiz aus Meta-Thread (2026-05-03):**
> Dieser Text muss zwei Leser gleichzeitig ansprechen — den interessierten
> Besucher UND den skeptischen Vorstand. Der Abschnitt „Was der Club kontrolliert"
> ist kein technisches Detail, sondern ein **Vertrauensversprechen an den Club**.
> Das ändert den Ton dieses Teils grundlegend: weniger museumspädagogisch,
> mehr institutionell. Der Besucher soll verstehen, wie das Archiv funktioniert.
> Der Vorstand soll verstehen, dass der Club Herr des Verfahrens bleibt.
> Beide Lesarten müssen im selben Text aufgehen — ohne dass eine die andere
> dominiert. Das ist eine Tonalitätsaufgabe, keine Strukturaufgabe.

---

### T1-IT-04 — Story-Disclaimer: Community vs. Editorial

**Gutachten-Bezug:** Befund 3.2 (⚠️)
**Datei:** T1-emotionaler-kern.md
**Abschnitt:** Tonalität der Sprache — Ergänzung
**Priorität:** A

**Was zu ändern ist:**
Ergänze im Abschnitt „Tonalität" zwei Pflicht-Disclaimer-Texte für Story-Typen:

**Editorial-Disclaimer:**
> „Dieser Text wurde vom RotaryArchiv-Redaktionsteam erstellt und auf Basis
> der vorliegenden Quellen geprüft."

**Community-Disclaimer:**
> „Dieser Beitrag wurde von einem Besucher eingereicht. Das RotaryArchiv hat ihn
> freigegeben, aber nicht inhaltlich überprüft. Die Angaben spiegeln die
> Perspektive der Beitragenden wider."

Diese Texte erscheinen **immer** direkt unterhalb des Story-Titels —
nicht als Hover-Element, nicht als Metadaten-Tag, sondern als lesbarer
Fließtext. Format: Lora Kursiv, Text Sekundär, kleine Schriftgröße (Caption).

---

### T1-IT-05 — Pflichtfeld „Quellenangabe" im Beitragsformular

**Gutachten-Bezug:** Befund 3.1 (⚠️)
**Datei:** T1-informationsarchitektur.md
**Abschnitt:** V09 Story einreichen
**Priorität:** B

**Was zu ändern ist:**
Das Beitragsformular V09 muss ein Pflichtfeld „Quellenangabe" enthalten.
Formathinweis: freitextlich, aber mit erklärendem Platzhalter-Text:

> „Worauf stützt sich dieser Beitrag? (z.B. „Memoiren meines Großvaters,
> ca. 1985" oder „Stadtarchiv Dresden, Bestand X" oder „mündliche Überlieferung
> in meiner Familie") — Auch ungesicherte Erinnerungen sind wertvolle Hinweise,
> wenn sie als solche gekennzeichnet sind."

Das Feld ist ein Pflichtfeld — ohne Angabe kein Einreichen. Es darf aber jede
Antwort enthalten: Die Transparenz über die Quelle ist wichtiger als ihre Qualität.

---

### T1-IT-06 — Consent-Verifikationsstufe für 90er-Epoche (Feature C)

**Gutachten-Bezug:** Befund 3.3 (⚠️)
**Datei:** T1-informationsarchitektur.md oder project-brief_v04.md (Beitragsmodell)
**Abschnitt:** Consent-Modell / Feature C
**Priorität:** B

**Was zu ändern ist:**
Ergänze im Beitragsmodell und in der Feature-C-Beschreibung eine explizite Regel:

**Für die 30er-Epoche (verstorbene Personen):**
Selbstidentifikation ist nicht anwendbar — Consent-System gilt nicht.
Freischaltung liegt ausschließlich beim Admin.

**Für die 90er-Epoche (potenziell lebende Personen):**
Selbstidentifikation erhöht den Consent-Score **erst nach Admin-Bestätigung**
der Identifikation. Der Admin bestätigt nicht die Identität (das kann er nicht),
sondern nur, dass der Account plausibel wirkt (kein frisch erstelltes Konto,
keine offensichtlichen Widersprüche). Automatischer Score-Anstieg ohne diesen
Schritt ist deaktiviert.

---

## AUFTRÄGE AN T5 (Frontend/Design)

---

### T5-IT-01 — Amtsstrahl: Drei semantische Lücken-Typen

**Gutachten-Bezug:** Befund 2.2 (⚠️)
**Datei:** T5-wow-features-v2.md
**Abschnitt:** Feature D — Amtsstrahl, Visuelle Codierung-Tabelle
**Priorität:** B

**Was zu ändern ist:**
Die aktuelle Lücken-Codierung kennt nur einen Lückentyp (`░░░░` = unleserlich/unbekannt).
Erweitere die Codierungstabelle um zwei weitere Typen:

| Zeichen | Bedeutung | Visuell |
|---|---|---|
| `░░░░` (Schraffur) | Quelle unleserlich — Name unbekannt | Aktueller Stand, unverändert |
| `—` (Gedankenstrich, zentriert, gedimmt) | Kein Amtswechsel in diesem Jahr dokumentiert | Text Sekundär (#57534E), italic, nicht klickbar |
| Ocker-hinterlegtes Segment | Amtswechsel außerordentlich — kein regulärer Wahlvorgang | Hintergrund: #8B7355 bei 20% Opacity, kurze Tooltip-Erklärung |

**Warum:** Ein leeres/fehlendes Feld kommuniziert derzeit „wir wissen es nicht".
Das unterscheidet sich fundamental von „es gab in diesem Jahr keinen regulären
Wechsel" — letzteres ist selbst eine historische Aussage.

**Input für T6:** Neues Feld `role_gap_type` (Enum: unknown / undocumented / irregular)
auf dem MembershipEvent- oder Amtsstrahl-Datenmodell.

---

### T5-IT-02 — HistoricalContextBox: Automatische Trigger-Stufen

**Gutachten-Bezug:** Befund 4.3 (❌)
**Datei:** T5-designsystem-v1.1.md und T5-wow-features-v2.md
**Abschnitt:** Designsystem Abschnitt 7 (Historisch sensible Inhalte) + Feature E
**Priorität:** A

**Was zu ändern ist:**
Die HistoricalContextBox darf nicht länger ausschließlich manuell aktivierbar sein.
Ergänze in der Komponentendokumentation drei Aktivierungs-Modi:

**Modus AUTO-GENERIC:**
Trigger: Dokument-Datum liegt zwischen 1933–1937.
Inhalt: Generischer Epochenkontext-Text (einmalig verfasst, systemweit).
Styling: Wie bisher — Ocker-Rand, Lora Kursiv.
Admin-Eingriff: Kann durch spezifischeren Text ersetzt, aber nicht
deaktiviert werden.

**Modus AUTO-SPECIFIC (LLM-gestützt):**
Trigger: MembershipEvent.event_type = leave AND Datum 1933–1937 AND
protocol_wording enthält Euphemismus-Muster.
Inhalt: LLM-generierter Kontextvorschlag, sichtbar im Admin-Interface
mit Klick-Freigabe.
Styling: Identisch mit Modus AUTO-GENERIC, aber mit zusätzlichem Label
„Redaktionell geprüft" nach Freigabe.

**Modus MANUAL:**
Wie bisher — Admin setzt Box individuell.

**Visueller Unterschied zwischen Modi:**
- AUTO-GENERIC: Kein zusätzliches Label (systemweit, kein individueller Anspruch)
- AUTO-SPECIFIC + MANUAL: Kleines Label „Redaktioneller Hinweis" — signalisiert,
  dass ein Mensch diese Box bewusst gesetzt hat

---

### T5-IT-03 — V12 Kuratorisches Statement: Neue persistente Sektion

**Gutachten-Bezug:** Befund 2.3 (❌), T1-IT-03
**Datei:** T5-komponenten-v1.2.md (oder neue Designspezifikation für V12)
**Abschnitt:** V12 Über das Projekt
**Priorität:** A

**Was zu ändern ist:**
V12 braucht eine eigene Designsektion für das kuratorische Statement — keine
gewöhnliche About-Page-Sektion, sondern einen visuell ausgezeichneten Block:

```
┌── Kuratorisches Statement ──────────────────────────────────┐
│  Wie wir arbeiten — und was dieses Archiv nicht kann        │
│                                                             │
│  [Fließtext, 400–600 Wörter, Lora, volle Lesbreite]        │
│                                                             │
│  Letzte Aktualisierung: [Datum]                             │
└─────────────────────────────────────────────────────────────┘
```

- Eigene Section-Headline (H2, Lora)
- 3px Ocker-Rand links (wie HistoricalContextBox — visueller Verwandtschaft
  zu historischem Kontext, nicht zu technischen Infos)
- Direkt verlinkbar (`/ueber#kuratorisches-statement`)
- Link auf diesen Abschnitt soll von V01 (Startseite, Footer-Bereich) und
  von jeder HistoricalContextBox aus zugänglich sein: „Mehr zu unserer
  kuratorischen Haltung →"

---

### T5-IT-04 — Story-Disclaimer: Typografische Umsetzung

**Gutachten-Bezug:** Befund 3.2 (⚠️), T1-IT-04
**Datei:** T5-komponenten-v1.2.md
**Abschnitt:** K-Story / V08 Story-Detail
**Priorität:** A

**Was zu ändern ist:**
Füge in der Story-Komponentenspezifikation einen Pflichtblock unterhalb des
Story-Titels ein:

```
[Story-Titel — H1, Lora]
[Autor, Datum — Caption, Inter]
──────────────────────────────────────────────────────
[DISCLAIMER-BLOCK:]
  Stil: Lora Kursiv, Caption-Größe (0.875rem), Text Sekundär (#57534E)
  Abstand: 16px unter dem Metadatenblock, 24px vor dem ersten Absatz
  Inhalt: je nach story_type editorial / community (Texte → T1-IT-04)
──────────────────────────────────────────────────────
[Story-Fließtext]
```

Der Disclaimer ist **kein optionales Element** — er erscheint bei jeder
freigegebenen Story, editorial wie community.

---

### T5-IT-05 — Community-Beitrag: Quellen-Label in der Darstellung

**Gutachten-Bezug:** Befund 3.1 (⚠️)
**Datei:** T5-komponenten-v1.2.md
**Abschnitt:** K-Story oder Beitragsdarstellung
**Priorität:** B

**Was zu ändern ist:**
Jede Community-Story zeigt das Quellenfeld aus dem Einreichungsformular
als sichtbares Label in der veröffentlichten Ansicht an:

```
[Story-Text]

────────────────────────────────────────────
Quelle laut Beitragender:
„Memoiren meines Großvaters, ca. 1985"
────────────────────────────────────────────
```

Styling: Caption, Inter, Text Sekundär, leichter Trennstrich oben.
Platzierung: Am Ende des Story-Textes, vor den verknüpften Dokumenten.

Nicht am Anfang — das würde die Story sofort misstrauisch einrahmen.
Am Ende — nach dem Inhalt, als transparente Verortung, nicht als Warnung.

---

## Überblick: Alle Aufträge nach Priorität

| ID | Adressat | Priorität | Befund | Kurztitel |
|---|---|---|---|---|
| T1-IT-01 | T1 | A | 1.1 ⚠️ | Binnendifferenzierung 30er auf V02 |
| T1-IT-02 | T1 | A | 1.4 ⚠️ | Drei-Stufen-Pflichtigkeit Kontexthinweis |
| T1-IT-03 | T1 | A | 2.3 ❌ | Kuratorisches Statement V12 |
| T1-IT-04 | T1 | A | 3.2 ⚠️ | Story-Disclaimer Texte |
| T5-IT-02 | T5 | A | 4.3 ❌ | HistoricalContextBox Automatik-Modi |
| T5-IT-03 | T5 | A | 2.3 ❌ | V12 Kuratorisches Statement Design |
| T5-IT-04 | T5 | A | 3.2 ⚠️ | Story-Disclaimer Typografie |
| T1-IT-05 | T1 | B | 3.1 ⚠️ | Pflichtfeld Quellenangabe V09 |
| T1-IT-06 | T1 | B | 3.3 ⚠️ | Consent-Verifikation 90er |
| T5-IT-01 | T5 | B | 2.2 ⚠️ | Amtsstrahl drei Lücken-Typen |
| T5-IT-05 | T5 | B | 3.1 ⚠️ | Quellen-Label Community-Story |
| — | T1 | C | 2.1 ⚠️ | Blindstellen-Hinweis V12 (in T1-IT-03 integrierbar) |

---

## Hinweis zu LLM-gestützten Workflows

Mehrere Aufträge empfehlen LLM-gestützte Textgenerierung als Ersatz für
fehlendes Redaktionspersonal. Das betrifft konkret:

| Aufgabe | Einmalaufwand | Laufender Aufwand |
|---|---|---|
| Generischer Epochenkontext-Text 1933–1937 | 1× LLM-Entwurf + Freigabe | Keiner |
| Kuratorisches Statement V12 | 1× LLM-Entwurf + Freigabe | Jährliche Revision |
| Story-Disclaimer-Texte (2 Varianten) | 1× LLM-Entwurf + Freigabe | Keiner |
| LLM-Kontextbox-Vorschlag für Austritt-Events | Technische Integration T6 | Pro Dokument: 1 Klick Admin |

**Empfehlung für den Einsatz von LLMs im redaktionellen Workflow:**
LLMs übernehmen Erstfassung und Musterprüfung. Ein Mensch (Projektinhaber)
gibt frei oder lehnt ab — er schreibt nie selbst von null. Das ist der
realistisch umsetzbare Workflow ohne Redaktionsteam.

---

*Ende der Iterationsaufträge.*
*Nächste Aktualisierung: nach Bearbeitung durch T1 und T5.*
