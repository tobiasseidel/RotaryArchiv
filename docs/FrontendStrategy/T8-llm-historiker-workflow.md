# T8-llm-historiker-workflow.md
# Workflow-Konzept: LLM-gestützte Kuratorik mit Fachkonsultation

> **Version:** 1.0 — 2026-05-03
> **Thread:** T8 Kurator / Historiker
> **Input aus:** T8-kuratorisches-gutachten.md, T8-iterationsauftraege.md
> **Adressaten:** Projektinhaber, zukünftige Fachpartner
> **Status:** Konzept — zur Freigabe durch Projektinhaber

---

## Ausgangslage

Das RotaryArchiv wird ohne professionelles Redaktionsteam betrieben.
Die kuratorischen Aufgaben, die das Projekt stellt, übersteigen jedoch
die Kapazität einer einzelnen Person ohne historiografische Ausbildung —
besonders für die 30er-Epoche mit ihrer NS-Dimension.

Dieses Dokument beschreibt, wie diese Lücke durch eine strukturierte
Arbeitsteilung zwischen LLM-Assistenz, Projektinhaber und einmaligen
Fachkonsultationen geschlossen werden kann.

**Das Grundprinzip:**
> LLM entwirft. Projektinhaber entscheidet. Fachmensch prüft — einmalig,
> nicht laufend. Verantwortung trägt immer ein Mensch.

---

## 1. Was das LLM zuverlässig leistet

### 1.1 Einmalige Grundlagentexte (Priorität A)

Diese Texte werden einmal erstellt, freigegeben und dann systemweit verwendet.
Kein laufender Aufwand nach der Freigabe.

| Text | Aufwand LLM | Aufwand Projektinhaber | Fachkonsultation |
|---|---|---|---|
| Generischer Epochenkontext 1933–1937 (Template für HistoricalContextBox Stufe 1) | Entwurf in einem Prompt | Lesen, ggf. anpassen, freigeben | Empfohlen (Historiker, Punkt 3.1) |
| Erweiterungstext Euphemismus-Formulierungen (Template Stufe 2) | Entwurf in einem Prompt | Lesen, freigeben | Empfohlen |
| Kuratorisches Statement V12 (400–600 Wörter) | Entwurf auf Basis von T8-Gutachten | Lesen, anpassen, freigeben | Pflicht vor Launch (Punkt 3.1) |
| Story-Disclaimer Editorial / Community (je 2 Sätze) | Entwurf in einem Prompt | Lesen, freigeben | Nicht nötig |
| Binnendifferenzierungstext 30er auf V02a | Entwurf in einem Prompt | Lesen, freigeben | Empfohlen |

**Wie der Prompt-Workflow aussieht:**

```
Prompt-Struktur für alle Grundlagentexte:

1. Kontext geben: „Du bist Kurator des RotaryArchivs Dresden. Das Archiv
   dokumentiert die Geschichte des Rotary Club Dresden 1927–1937 und 1990–2008.
   Hier ist die kuratorische Haltung des Projekts: [T1-emotionaler-kern.md
   Abschnitt 'Historische Sensibilität' einfügen]"

2. Aufgabe stellen: „Schreib [Text X] in folgendem Ton: warm, ehrlich,
   nicht anklagend, nicht verharmlosend. Maximallänge: [X] Wörter."

3. Ausgabe prüfen gegen: Stimmt die Faktenlage? Klingt der Ton richtig?
   Passt es zur Haltung des Projekts?

4. Freigeben oder Prompt verfeinern und wiederholen.
```

---

### 1.2 Laufende redaktionelle Aufgaben

Diese Aufgaben fallen regelmäßig an — bei jedem neuen Community-Beitrag,
jeder neu erschlossenen Person, jeder neuen Dokumentverknüpfung.

**Community-Beitragsscreening:**

Vor jeder Admin-Freigabe einer eingereichten Story:

```
Prompt-Vorlage:

„Ich zeige dir einen Community-Beitrag für ein historisches Archiv.
Prüfe ihn auf folgendes und liste deine Befunde auf:

1. Enthält der Beitrag historische Behauptungen über konkrete Personen?
   Wenn ja: welche, und wie belegt sind sie laut Quellenangabe?

2. Widerspricht der Beitrag erkennbar den folgenden Protokollstellen?
   [relevante Protokollzitate einfügen]

3. Sollte eine HistoricalContextBox ergänzt werden? Wenn ja: welchen
   Inhalt würdest du vorschlagen?

4. Gibt es Formulierungen, die als Werturteil über eine Person wirken
   könnten, ohne dass eine Quelle genannt wird?

Beitrag: [Beitragstext einfügen]
Quellenangabe des Beitragenden: [Quellenfeld aus Formular]"
```

Ausgabe: strukturierter Befundbericht. Ihr entscheidet, freigeben oder ablehnen.

---

**HistoricalContextBox-Vorschlag für Austritt-Events (Stufe 2):**

Wenn ein Austritt 1933–1937 mit Euphemismus-Formulierung im System erscheint:

```
Prompt-Vorlage:

„Für folgendes Austritt-Ereignis soll eine HistoricalContextBox
formuliert werden. Die Box erklärt ohne zu verurteilen. Sie spricht
von der Person nicht im Urteil, sondern vom historischen Kontext.

Protokollwortlaut: [protocol_wording]
Datum: [event_date]
Weitere verknüpfte Dokumente: [falls vorhanden]

Formuliere einen Kontexthinweis von maximal 60 Wörtern.
Ton: sachlich, würdevoll, nicht anklagend, nicht rehabilitierend."
```

Ausgabe: Textvorschlag. Admin klickt „Freigeben" oder passt an.

---

**Epocheneinordnung für neu erschlossene Personen:**

Wenn eine Person neu ins System kommt und auffällige Muster zeigt
(letzter Eintrag 1934, nie mehr erwähnt):

```
Prompt-Vorlage:

„Ich zeige dir die Aktivitätsdaten einer Person aus dem Archiv.
Ordne ein, ob das Muster historisch auffällig ist und welche
Kontextinformationen für das Personenprofil hilfreich wären.
Keine Urteile über die Person — nur historische Einordnung des Musters.

Erste Erwähnung: [Datum]
Letzte Erwähnung: [Datum]
Ämter: [Liste]
Anwesenheitsrate: [Heatmap-Zusammenfassung]
Protokollwortlaut Austritt (falls vorhanden): [Wortlaut]"
```

---

### 1.3 Musteranalyse auf dem Gesamtbestand

Einmalig oder bei größeren Erschließungsfortschritten:

```
Aufgaben, die ein LLM auf dem Gesamtbestand leisten kann:

- Alle Austritte 1933–1937 tabellarisch mit Datum, Wortlaut, letzter
  Erwähnung vor Austritt zusammenfassen
- Häufigste Formulierungen in Austrittsprotokollen identifizieren
  und clustern
- Personen identifizieren, die nach einem bestimmten Datum nicht mehr
  erwähnt werden, ohne dass ein Austritt protokolliert ist
- Amtswechsel identifizieren, die nicht dem Rotary-Jahres-Rhythmus
  entsprechen
- Sitzungen identifizieren, in denen ungewöhnlich viele Personen fehlen
```

Diese Analysen sind **Ausgangspunkte für kuratorische Entscheidungen**,
keine Entscheidungen selbst. Die Ausgabe wird in Redaktions-Queue eingestellt
und vom Projektinhaber bewertet.

---

## 2. Wo das LLM nicht hinreicht

Diese Aussage gilt absolut — nicht als Tendenz, sondern als Grenze:

### 2.1 Lokale Personenrecherche

Ein LLM kennt keine lokalen Dresdner Quellen. Wenn ein Name aus euren
Protokollen in Stadtarchiv-Beständen, Entnazifizierungsakten, Gestapo-Akten
oder anderen lokalen Quellen auftaucht — das ist Archivarbeit.

**Was konkret gemeint ist:** Wenn ihr beim Erschließen auf Personen stoßt,
die in einem der folgenden Kontexte erwähnt werden könnten, braucht ihr
externe Recherche:

- NSDAP-Mitgliedschaft oder -Funktion
- Beteiligung an Arisierungsmaßnahmen
- Denunziationen oder Kooperation mit NS-Behörden
- Opfer-Status (Emigration, KZ, Ermordung)

Das LLM produziert für solche Fragen plausibel klingende Antworten,
die faktisch falsch sein können. Das ist die gefährlichste Konstellation
für ein Archiv: nicht grob falsches, sondern subtil falsches.

### 2.2 Rechtliche Einordnung

Datenschutz für lebende Personen (90er-Epoche), Persönlichkeitsrechte,
mögliche Haftungsfragen beim Consent-Modell — das ist juristische,
keine historische Arbeit. Kein LLM kann rechtliche Sicherheit geben.

### 2.3 Wissenschaftliche Zitierfähigkeit

Ob das Archiv den Anforderungen von Archetyp Dr. Miriam (Historikerin,
braucht zitierfähige Quellen) genügt, muss einmalig jemand mit
historiografischer Ausbildung bestätigen. Ein LLM kann die Standards
beschreiben — nicht bestätigen, dass ihr sie erfüllt.

### 2.4 Das finale Urteil über belastete Personen

Das Projekt hat die Designentscheidung getroffen: „Das Interface urteilt nicht."
Das ist richtig. Aber wenn ein Redakteur eine HistoricalContextBox setzt,
die implizit eine Person belastet oder entlastet — das ist ein Urteil.
Dieses Urteil muss ein Mensch verantworten, nicht ein LLM.

---

## 3. Die einmaligen Fachkonsultationen

Das Ziel ist **ein Qualitäts-Gate vor dem Launch**, keine laufende Zusammenarbeit.
Drei Kontakte, jeder einmalig, unterschiedliche Expertise.

---

### 3.1 Zeithistoriker: Dresden / NS-Vereinsgeschichte

**Zweck:** Prüfung der Grundlagentexte und der kuratorischen Haltung.

**Was ihr vorbereitet:**
- Kuratorisches Statement (LLM-Entwurf, von euch vorgeprüft)
- Generischer Epochenkontext-Text
- Liste der Austritte 1933–1937 (Datum, Wortlaut) — anonymisiert

**Was ihr fragt:**
1. Ist die Einordnung der Austrittsformulierungen als möglicher Euphemismus
   dem Stand der Forschung angemessen?
2. Gibt es bekannte Mitglieder des Rotary Club Dresden in dieser Epoche,
   die historisch relevant oder belastet sind und besonderer Behandlung bedürfen?
3. Ist das kuratorische Statement historiografisch vertretbar?

**Wo ihr diese Person findet:**
- Hannah-Arendt-Institut für Totalitarismusforschung (HAIT), Dresden —
  spezialisiert auf NS-Geschichte in Sachsen, offen für Zivilgesellschaftsprojekte
- Stadtarchiv Dresden — kennt lokale Vereinsgeschichte
- TU Dresden, Institut für Geschichte — Zeithistoriker mit regionalem Fokus
- Gedenkstätte Münchner Platz Dresden

**Aufwand für die Fachperson:** 2–3 Stunden. Viele solcher Institutionen
helfen Projekten wie eurem ohne oder gegen geringe Aufwandsentschädigung.

---

### 3.2 Rechtliche Einschätzung: Datenschutz und Persönlichkeitsrechte

**Zweck:** Absicherung des Consent-Modells und der 90er-Epoche.

**Was ihr vorbereitet:**
- Beschreibung des `is_public`-Modells (aus project-brief_v04.md)
- Beschreibung des Consent-Systems (Feature C, T5-wow-features-v2.md)
- Beschreibung der Stub-Response-Logik für nicht-öffentliche Personen

**Was ihr fragt:**
1. Ist das Consent-Modell für lebende Personen datenschutzrechtlich vertretbar?
2. Gibt es bei der Selbstidentifikation Risiken, die wir absichern müssen?
3. Reicht die Stub-Response-Logik als Schutzmaßnahme?

**Wo ihr diese Person findet:**
- Kanzleien mit Schwerpunkt IT-Recht / Datenschutz (Erstberatung oft kostenlos
  oder günstig für Nicht-kommerzielle Projekte)
- Verbraucherzentrale Sachsen (für erste Orientierung)
- Rotary-interner Kontakt: Im Club selbst sind häufig Juristen — die kennen
  das Projekt und haben Interesse, es abzusichern

---

### 3.3 Wissenschaftliche Qualitätsprüfung: Zitierfähigkeit

**Zweck:** Sicherstellen, dass Dr. Miriam das Archiv tatsächlich nutzen kann.

**Was ihr vorbereitet:**
- Beschreibung der Erschließungsmethodik (OCR → BBox → Triplestore)
- Beispiel-Exportdatei (BibTeX, sobald implementiert)
- Beschreibung, wie Quellenangaben im Archiv strukturiert sind

**Was ihr fragt:**
1. Welche Mindeststandards muss eine digitale Edition erfüllen, um in
   wissenschaftlichen Kontexten zitierbar zu sein?
2. Was fehlt aktuell noch?

**Wo ihr diese Person findet:**
- Digitale Geisteswissenschaften / Digital Humanities: TU Dresden,
  Uni Leipzig — haben Erfahrung mit genau dieser Frage
- Sächsische Landesbibliothek (SLUB) — betreibt selbst Digitalisierungsprojekte
  und berät

---

## 4. Der laufende Workflow im Betrieb

Nach dem Launch läuft das Archiv mit diesem wiederkehrenden Rhythmus:

### Bei jedem neuen Community-Beitrag

```
1. Eingang in Moderationswarteschlange
2. LLM-Screening (Prompt aus 1.2) — automatisch oder manuell
3. Befundbericht landet im Admin-Interface
4. Projektinhaber liest Befund + Originaltext
5. Entscheidung: Freigeben / Ablehnen / Rückfrage an Beitragenden
6. Bei Freigabe: HistoricalContextBox nötig? → LLM-Vorschlag oder manuell
```

Zeitaufwand pro Beitrag (geschätzt): **5–15 Minuten**

---

### Bei jeder neuen Erschließungscharge (Protokolle)

```
1. OCR und Triplestore-Erschließung (automatisch, T7)
2. LLM-Musteranalyse auf neuen Personen und Ereignissen
3. Auffälligkeiten in Redaktions-Queue
4. Projektinhaber priorisiert: Was bekommt eine HistoricalContextBox?
5. LLM-Vorschlag für priorisierte Einträge → Freigabe
```

Zeitaufwand pro Erschließungscharge: **2–4 Stunden**, abhängig von Umfang

---

### Jährliche Revision (empfohlen)

```
1. Kuratorisches Statement auf Aktualität prüfen
2. Epochenkontext-Templates gegen neue Forschungslage abgleichen
   (LLM kann recherchieren, Projektinhaber entscheidet)
3. Offene Community-Beiträge in der Queue abarbeiten
4. Fachkontakte (3.1) kurz anfragen: Gibt es neue relevante Forschung
   zu Rotary Dresden / NS-Vereinsgeschichte?
```

---

## 5. Entscheidungsmatrix: LLM oder Fachmensch?

Wenn ihr bei einer konkreten Aufgabe unsicher seid, welcher Weg richtig ist:

```
Frage 1: Geht es um eine bekannte historische Tatsache
         (NS-Gleichschaltung, Rotary international, Weimarer Republik)?
         → LLM als Ausgangspunkt, Projektinhaber prüft

Frage 2: Geht es um eine lokale Dresdner Person oder Institution,
         die nicht allgemein dokumentiert ist?
         → Stadtarchiv / Fachhistoriker. LLM nicht verlässlich.

Frage 3: Geht es um Tonalität, Formulierung, Struktur eines Textes?
         → LLM allein (mit eurer Freigabe)

Frage 4: Geht es um ein Urteil über eine Person
         (belastet / Opfer / Täter / Mitläufer)?
         → Niemals LLM. Immer Mensch — und wenn möglich Fachmensch.

Frage 5: Geht es um rechtliche Fragen (Datenschutz, Persönlichkeitsrechte)?
         → Niemals LLM. Jurist.

Frage 6: Ist die Ausgabe des LLM im Archiv öffentlich sichtbar
         und mit einer konkreten Person verknüpft?
         → Immer menschliche Freigabe. Keine Ausnahme.
```

---

## 6. Zusammenfassung: Was ihr wirklich braucht

Ihr braucht **kein Redaktionsteam**. Ihr braucht:

| Was | Wer | Wann | Aufwand |
|---|---|---|---|
| Grundlagentexte (Statement, Epochenkontext, Disclaimer) | LLM-Entwurf + eure Freigabe | Einmalig vor Launch | 1 Nachmittag |
| Zeithistoriker-Konsultation | HAIT / Stadtarchiv / TU Dresden | Einmalig vor Launch | 2–3 Std. der Fachperson |
| Rechtliche Einschätzung | Jurist (intern im Club?) | Einmalig vor Launch | 1–2 Std. |
| Zitierfähigkeitsprüfung | Digital Humanities / SLUB | Einmalig vor Launch | 1–2 Std. |
| Laufendes Beitragsscreening | LLM-Vorprüfung + eure Entscheidung | Bei jedem Beitrag | 5–15 Min./Beitrag |
| Laufende Kontextualisierung | LLM-Vorschlag + euer Klick | Bei Erschließung | 2–4 Std./Charge |
| Jährliche Revision | LLM + ihr | 1× pro Jahr | 1 Tag |

**Der einmalige Aufwand vor dem Launch ist der entscheidende.**
Was danach kommt, ist wartbar — auch allein.

---

*Dieses Dokument ersetzt keine Fachberatung.*
*Es beschreibt einen Workflow, der unter den gegebenen Ressourcenbedingungen*
*historiografisch vertretbar und operativ realistisch ist.*
