# RotaryArchiv — T1.3: Emotionaler Kern & Tonalität

> **Version:** 1.1 — 2026-05-01  
> **Thread:** T1 Konzept & UX  
> **Input für:** T5 Frontend/Design, T6 Coding  
> **Abhängigkeiten:** project-brief.md v0.1, T1-ux-archetypen.md v1.1, T1-informationsarchitektur.md v1.1  
> **Änderungen v1.1:** Epochenbezeichnungen angepasst; Community-Beitrag ohne Account als emotionales Moment ergänzt

---

## Die Kernfrage

> **Was soll ein Besucher *fühlen*, wenn er RotaryArchiv besucht?**

Die Antwort ist nicht eine einzelne Emotion, sondern eine **emotionale Reise in drei Akten** — passend zum Rabbit-Hole-Prinzip, das diesem Projekt zugrunde liegt.

---

## Die drei emotionalen Akte

### Akt 1: Anziehung — *„Moment mal."*

Der Besucher landet auf der Seite ohne Erwartung — oder mit einer sehr spezifischen (einem Namen, einer Frage). In beiden Fällen muss innerhalb von **10 Sekunden** eine emotionale Reaktion ausgelöst werden.

**Zielgefühl:** Neugier, leichtes Staunen. Das Gefühl, an etwas Realem, Konkretem, fast Greifbarem vorbeizulaufen.

**Wie:** Nicht durch Abstraktion („Wir digitalisieren Geschichte"), sondern durch Unmittelbarkeit. Ein Datum. Ein Satz. Ein Name. *„14. März 1933. Der Vorsitzende eröffnet die Sitzung. Es fehlen sieben Mitglieder."* — Das ist stärker als jede Willkommensseite.

---

### Akt 2: Versenkung — *„Ich will mehr wissen."*

Der Besucher klickt. Liest. Klickt wieder. Das Rabbit Hole öffnet sich. Jede neue Seite gibt eine Antwort — und stellt zwei neue Fragen.

**Zielgefühl:** Das Gefühl von *Tiefe*. Die Ahnung, dass da noch viel mehr ist. Die Entdeckerfreude beim Querlesen. Das leise Erschrecken, wenn eine Sitzung von 1934 plötzlich politisch bedrückend wird.

**Wie:** Durch konsequente Quervernetzung aller Entitäten. Durch Textausschnitte, die Atmosphäre transportieren. Durch den Moment, in dem der Besucher merkt: *Das waren echte Menschen.*

---

### Akt 3: Verbindung — *„Ich bin ein Teil davon."*

Nicht jeder Besucher erreicht diesen Akt. Aber wer ihn erreicht, ist gewonnen — als Beitragender, als Botschafter, als wiederkehrender Besucher.

**Zielgefühl:** Zugehörigkeit und Handlungsfähigkeit. Das Gefühl, nicht nur Konsument zu sein, sondern Mitgestalter. Für Wolfgang: *„Hier bin ich. Hier war ich dabei."* Für Karoline: *„Jetzt kenne ich meinen Urgroßvater."* Für Dr. Miriam: *„Diese Quelle ist zitierfähig."* Für Jannik: *„Das muss ich teilen."*

**Wie:** Durch Beitragsmechanismen, die nicht wie Formulare wirken, sondern wie Einladungen — und die keine Registrierung voraussetzen. Der Satz *„Ich kenne mehr über diese Person"* muss wie eine echte Einladung klingen, nicht wie ein Bürokratiepfad.

---

## Der emotionale Kern in einem Satz

> **„RotaryArchiv ist der Ort, an dem vergessene Namen wieder zu Menschen werden."**

Dieser Satz ist der interne Kompass für alle gestalterischen Entscheidungen. Jede Design-Entscheidung, jede UI-Formulierung, jeder Leerstand und jede Fehlermeldung wird daran gemessen: *Hilft das dabei, dass Namen wieder zu Menschen werden?*

---

## Tonalität der Sprache (UI-Text, Labels, Leerstände)

Das RotaryArchiv hat eine eigene Stimme. Diese Stimme ist:

| Eigenschaft | Bedeutung in der Praxis |
|---|---|
| **Konkret, nie abstrakt** | „14. März 1933" statt „historisches Dokument" |
| **Respektvoll, nie distanziert** | „Diese Person ist noch nicht vollständig erschlossen" statt „Keine Daten verfügbar" |
| **Neugierig, nie belehrend** | „Wissen Sie mehr über diese Person?" statt „Beitrag einreichen" |
| **Ehrlich bei Lücken** | „Dieser Abschnitt ist unleserlich" statt Leerzeichen oder [ERROR] |
| **Transparent bei Zugriffsschranken** | Erklärt *warum* etwas nicht sichtbar ist, nie nur *dass* es nicht sichtbar ist |
| **Einladend bei Beiträgen** | Kein Unterschied im Ton zwischen „mit Konto" und „ohne Konto" — nur der Prozess ist anders |

### Beispiele: Gute vs. schlechte UI-Texte

| Schlechte Version | Gute Version |
|---|---|
| „Keine Ergebnisse gefunden" | „Für diesen Namen gibt es noch keine Einträge. Wissen Sie etwas über diese Person?" |
| „Login erforderlich" | „Diese Protokolle stammen aus einer Zeit, in der viele der Beteiligten noch leben. Aus Rücksicht auf ihre Persönlichkeitsrechte sind sie nur für eingeloggte Mitglieder zugänglich." |
| „Beitrag einreichen" | „Ich kenne mehr über diese Person" |
| „Fehler melden" | „Stimmt etwas nicht?" |
| „Ihr Beitrag wurde gespeichert" | „Danke. Dein Beitrag wird von einem Admin geprüft und danach hier sichtbar sein." |
| „Willkommen im RotaryArchiv" | „14. März 1933. Der Vorsitzende eröffnet die Sitzung." |
| „Erschließungsstand: 43%" | „43 % dieser Seite sind bisher entziffert — die Arbeit läuft weiter." |

---

## Historische Sensibilität — Tonalität bei schwierigen Inhalten

Der Zeitraum der 30er endet mit dem erzwungenen Ende des Rotary Club Dresden unter dem NS-Regime (1937). Das Archiv dokumentiert diesen Übergang — auch wenn er in den Protokollen selbst kaum explizit thematisiert wird.

**Haltung des Projekts:** Nicht Ankläger, nicht Verteidiger, sondern **ehrlicher Zeuge**. Das bedeutet:

- Historische Hinweistexte werden eingebettet, nicht versteckt
- Kontextkästen mit erklärendem Text bei sensiblen Epochen und Dokumenten
- Keine Verharmlosung durch überformatierten Enthusiasmus auf Seiten, die politisch schwere Inhalte zeigen
- Expliziter Hinweis auf das Vereinsverbot 1937 und dessen Umstände in der Epochen-Übersicht der 30er
- Die Sprache der UI bleibt ruhig und würdevoll, auch wenn Dokumente aus einer schwierigen Zeit stammen

---

## Design-Implikationen für T5 Frontend/Design

### Visueller Ton

- **Warm, nicht steril.** Archivarische Materialität: etwas Papier, etwas Tinte, etwas Zeit. Kein kaltes Tech-Blau.
- **Authentisch, nicht nostalgisch-kitschig.** Kein Sepia-Filter auf allem. Die Vergangenheit soll real wirken, nicht verniedlicht.
- **Typografie mit Haltung.** Eine Satzschrift (Serif) für Protokoll-Transkriptionen, die Würde und Lesbarkeit verbindet. Navigationselemente dürfen davon abweichen.
- **Viel Weißraum beim Lesen.** Lesetexte aus den Protokollen brauchen Luft — 65–72 Zeichen Zeilenlänge, großzügiger Zeilenabstand.

### Zwei-Epochen-Differenzierung

| | Die 30er | Die 90er |
|---|---|---|
| **Atmosphäre** | Schwerer, gediegener, historisch aufgeladen | Lebendiger, näher, zeitgenössischer |
| **Farbrichtung** | Warme Erdtöne, dunkler Akzent (Dunkelgrün oder Dunkelblau) | Heller, wärmeres Beige, leichterer Akzent |
| **Typografie** | Seriöser, gewichtiger Satz | Etwas zugänglicher, moderner |
| **Zugangsmarkierung** | Kein besonderer Hinweis nötig (öffentlich) | Subtile Kennzeichnung nicht-öffentlicher Objekte |

Beide Epochen teilen: neutrale Grundpalette, hohe Lesekomfortqualität, konsistente IA.

### Interaktive Momente mit emotionaler Wirkung

1. **Hover über Personenname im Protokolltext** → Tooltip mit Name, Lebensdaten, Rolle. Buchstabenfolgen werden sofort zu Menschen.
2. **Zeitstrahl-Scrollen** → sanfte Übergänge, keine harten Sprünge. Zeit fließt.
3. **Protokoll-Dual-View** (Scan + Transkription) → synchrones Scrollen. Der Scan macht die Handschrift greifbar.
4. **Erschließungsfortschritt** → visuell als „X Seiten von Y sind bisher lesbar gemacht" — nicht als trockener Prozentwert.
5. **Beitrag ohne Account** → Nach dem Einreichen: wärmende Bestätigung, kein bürokratischer Ton. Das Formular verschwindet, an seiner Stelle: „Danke. Wir schauen es uns an."
6. **Nicht-öffentliches Objekt** → Kein Schloss-Icon, kein roter Hinweis. Ein ruhiger Platzhalter mit erklärendem Satz.

---

## Zwei Phasen des Projekts

Das RotaryArchiv ist kein fertiger Auftrag des Clubs — es ist zunächst ein **Argument**. Diese Doppelrolle prägt Tonalität, Priorisierung und das Design des gesamten Frontends.

### Phase 1 — Überzeugungsarbeit (vor Club-Freigabe)

**Zielgruppe:** Vorstand und Mitglieder des Rotary Club Dresden  
**Funktion des Frontends:** Demonstrator — zeigt, was möglich ist, und beweist, dass es kontrollierbar ist  
**Emotionales Ziel:** Vertrauen, nicht Staunen

In dieser Phase ist das Frontend ein Instrument der internen Überzeugung. Der Vorstand (Archetyp Klaus-Peter) muss sehen, dass:
- das Zugriffsmodell funktioniert und verständlich ist
- sensible Inhalte der 90er standardmäßig nicht sichtbar sind
- die historisch schwierigen Inhalte der 30er würdevoll und kontextualisiert präsentiert werden
- der Club das System jederzeit kontrolliert

**Priorisierung in Phase 1:** Ein überzeugender Prototyp mit wenigen, aber tief erschlossenen Personen ist wichtiger als ein vollständiges System. Qualität schlägt Quantität. Eine einzige Personenseite, die vollständig, querverlinkt und erklärend ist, überzeugt mehr als hundert leere Einträge.

### Phase 2 — Öffentliches Archiv (nach Club-Freigabe)

**Zielgruppe:** Alle vier ursprünglichen Archetypen (Karoline, Wolfgang, Dr. Miriam, Jannik)  
**Funktion des Frontends:** Öffentliches digitales Archiv mit Community-Beteiligung  
**Emotionales Ziel:** Entdeckung → Versenkung → Verbindung

In dieser Phase gelten alle Prinzipien des emotionalen Kerns uneingeschränkt. Das Rabbit-Hole-Prinzip, die offenen Beitragsflüsse und die vollständige IA entfalten ihre Wirkung.

### Konsequenz für die Entwicklungsreihenfolge

```
Phase 1 — Demonstrator
├── V03 Personenprofil (2–3 vollständig erschlossene Personen)
├── V04 Dokumentansicht (3–5 repräsentative Protokolle)
├── V12 Über das Projekt (mit Vertrauens-Abschnitten für den Vorstand)
└── Zugriffsmodell sichtbar und erklärbar

Phase 2 — Vollausbau
├── Alle 12 Views
├── Suchfunktion
├── Netzwerk-Graph und Karte
├── Beitragsflüsse (Story einreichen, Korrektur melden)
└── Nutzerprofil
```

**Tonalitäts-Unterschied zwischen den Phasen:**  
In Phase 1 ist der wichtigste Satz auf der Seite nicht *„Vergessene Namen werden wieder zu Menschen"*, sondern *„Der Club entscheidet, was sichtbar ist."* Beide Sätze müssen wahr sein — aber die Gewichtung ist phasenabhängig.

---

## Zusammenfassung als Input-Paket für T5 (aktualisiert v1.2)

| Parameter | Wert |
|---|---|
| **Emotionaler Kern** | „Vergessene Namen werden wieder zu Menschen" |
| **Primäre Emotion** | Entdeckung → Versenkung → Verbindung |
| **Ton** | Warm, konkret, ehrlich, respektvoll |
| **Visueller Stil** | Archivarisch-warm, nicht nostalgisch-kitschig, hohe Typografiequalität |
| **Interaktionsprinzip** | Rabbit Hole — jeder Klick öffnet neue Türen |
| **Schwierige Inhalte** | Ehrlich eingebettet, kontextualisiert, würdevoll |
| **Community-Beitrag** | Ohne Konto möglich, Ton identisch — nur der Prozess (Moderation) unterscheidet sich |
| **Zwei-Epochen-Differenzierung** | Visuell unterscheidbar, strukturell identisch |
| **Zugangskommunikation** | Erklärender Platzhalter statt harter Sperre — immer mit Begründung |
| **Phase 1 / Demonstrator** | Wenige, tiefe Inhalte — Vertrauen vor Vollständigkeit |
| **Phase 2 / Vollausbau** | Alle Archetypen, alle Views, Community-Beteiligung aktiv |
'''
