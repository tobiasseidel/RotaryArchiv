# RotaryArchiv — T1.1: User-Archetypen & Jobs to be Done

> **Version:** 1.1 — 2026-05-01  
> **Thread:** T1 Konzept & UX  
> **Input für:** T5 Frontend/Design, T6 Coding  
> **Abhängigkeiten:** project-brief.md v0.1  
> **Änderungen v1.1:** Epochen umbenannt in „30er" / „90er"; Zugriffsmodell auf Objekt-Flags vereinfacht; Beiträge ohne Account möglich (mit Admin-Freigabe)

---

## Vorbemerkung: Die Herausforderung dieser Nutzerschaft

Das RotaryArchiv richtet sich an eine außergewöhnlich heterogene Nutzerschaft: Vom Gelegenheitsbesucher, der zufällig landet, bis zum Historiker, der Primärquellen sucht. Das verbindende Moment ist **nicht** ein gemeinsamer Kenntnisstand, sondern ein gemeinsames Erleben: das Gefühl, in eine vergessene Welt einzutauchen und immer tiefer hineingezogen zu werden.

Die vier Archetypen beschreiben keine trennscharf abgrenzbaren Segmente, sondern **Nutzungsmodi** — dieselbe Person kann je nach Kontext in verschiedene Rollen wechseln.

---

## Archetyp 1: „Die Familiendetektivin" — Karoline

### Profil

| Attribut | Ausprägung |
|---|---|
| **Name** | Karoline, 52 Jahre |
| **Beruf** | Lehrerin, Teilzeit |
| **Digitale Kompetenz** | Mittel — nutzt Ancestry.de, kennt Wikipedia |
| **Zugang** | Überwiegend öffentliche Inhalte; einzelne Objekte ggf. nicht-öffentlich |
| **Anlass** | Ihre Großmutter hat einen Namen erwähnt: „Dein Urgroßvater war in diesem Klub" |

### Narrative Beschreibung

Karoline kommt nicht als Historikerin. Sie kommt mit einem Namen und einer Hoffnung. Sie will wissen, ob ihr Urgroßvater wirklich dabei war — und wer er war, bevor er „nur" Großvater war. Sie ist bereit, Zeit zu investieren, wenn sie das Gefühl hat: *Hier passiert etwas. Hier finde ich etwas.*

Sie wird frustriert, wenn sie sucht und nichts findet. Sie wird begeistert, wenn sie auf einem Personenprofil ein Protokollfragment liest, das ihren Vorfahren namentlich erwähnt. Wenn sie etwas weiß, das im Archiv fehlt, will sie es beitragen — auch ohne Konto, wenn es ihr einfach gemacht wird.

### Jobs to be Done

1. **„Finde mir alle Einträge zu Person X"** — Personensuche mit Namensauflösung über den Triplestore, auch bei Schreibvarianten
2. **„Zeige mir, was diese Person getan, gesagt, erlebt hat"** — kontextualisiertes Personenprofil mit verknüpften Protokollstellen
3. **„Ich weiß etwas über diese Person — ich will es hinzufügen"** — niedrigschwelliger Beitragspfad ohne verpflichtende Registrierung

---

## Archetyp 2: „Der Insider" — Wolfgang

### Profil

| Attribut | Ausprägung |
|---|---|
| **Name** | Wolfgang, 68 Jahre |
| **Beruf** | Pensionierter Unternehmer, aktives Rotary-Mitglied seit 1994 |
| **Digitale Kompetenz** | Niedrig bis mittel — E-Mail, WhatsApp, manchmal Google |
| **Zugang** | Eingeloggt; Objekte der 90er sind für ihn sichtbar, weil er Mitglied ist |
| **Anlass** | Er selbst kommt in den Protokollen vor und möchte „nachschauen" |

### Narrative Beschreibung

Wolfgang ist nicht neugierig auf Geschichte im abstrakten Sinne — er *ist* die Geschichte. Er war dabei, als bestimmte Entscheidungen getroffen wurden. Er sucht sein eigenes Gesicht in alten Spiegeln. Er möchte Begegnungen wiederfinden, Namen zuordnen, vielleicht auch korrigieren, was falsch erschlossen wurde.

Er ist der wichtigste Qualitätsprüfer des Systems: Er weiß, wenn eine Zuordnung falsch ist. Und er ist motiviert genug, das zu melden — wenn man ihm einen einfachen Weg gibt. Als eingeloggter Nutzer wird sein Beitrag direkt sichtbar, ohne auf Freigabe zu warten.

### Jobs to be Done

1. **„Zeige mir Protokolle aus meiner aktiven Zeit"** — chronologischer oder personenbezogener Einstieg in die 90er (Objekte sind für ihn sichtbar, weil er eingeloggt ist und die Objekte seinen Zugang freigeben)
2. **„Ich erkenne jemanden, aber der Name ist falsch erschlossen"** — Korrektur-Workflow mit sofortiger Sichtbarkeit für eingeloggte Nutzer
3. **„Ich will eine Story über ein Ereignis beisteuern, das ich selbst erlebt habe"** — strukturierter Beitragsfluss, Story geht ohne Freigabe-Wartezeit live

---

## Archetyp 3: „Die Geschichtsforscherin" — Dr. Miriam

### Profil

| Attribut | Ausprägung |
|---|---|
| **Name** | Dr. Miriam, 38 Jahre |
| **Beruf** | Historikerin, Schwerpunkt Zivilgesellschaft in der Weimarer Republik |
| **Digitale Kompetenz** | Hoch — kennt Archivdatenbanken, Findmittel, Linked Data |
| **Zugang** | Eingeloggt mit freigeschalteten Objekten nach Absprache mit Admin |
| **Anlass** | Forschungsprojekt zu bürgerlichen Netzwerken in Dresden 1927–1933 |

### Narrative Beschreibung

Miriam kommt mit einer Forschungsfrage, nicht mit einem Namen. Sie will Netzwerke verstehen: Wer kannte wen? Wer war gleichzeitig in welchen Ämtern? Was wurde in bestimmten Monaten diskutiert — und was *nicht*? Sie braucht Exportfunktionen, Zitierbarkeit, stabile URLs.

Sie ist die Nutzerin, die das Projekt in wissenschaftliche Netzwerke trägt — wenn das System ihre Arbeit erleichtert statt behindert. Wenn sie auf ein nicht-öffentliches Objekt trifft, erwartet sie eine klare Erklärung und einen Kontaktweg.

### Jobs to be Done

1. **„Zeige mir Netzwerke: Wer war mit wem verbunden, wann?"** — Graph-/Zeitstrahlansicht von Personen- und Ereignisbeziehungen aus dem Triplestore
2. **„Ich brauche den Volltext und die Originalquelle als zitierfähiges Objekt"** — stabile Dokument-URLs, bibliografische Metadaten, Download/Export
3. **„Durchsuche alle Protokolle nach einem Thema"** — Volltext-Suche mit Datumsfilter, Quellenangabe und Ergebnis-Export

---

## Archetyp 4: „Der Neugierige Vorbeikommende" — Jannik

### Profil

| Attribut | Ausprägung |
|---|---|
| **Name** | Jannik, 29 Jahre |
| **Beruf** | Grafikdesigner, lebt in Dresden |
| **Digitale Kompetenz** | Sehr hoch — sozialer Teiler, konsumiert Wikipedia-Rabbit-Holes |
| **Zugang** | Öffentlich, ohne Login — sieht alles, was als öffentlich markiert ist |
| **Anlass** | Hat einen Link auf Social Media gesehen: „Protokolle aus dem Dresden der 30er Jahre" |

### Narrative Beschreibung

Jannik hat keine spezifische Frage. Er hat Neugier und 20 Minuten. Er braucht sofort etwas Faszinierendes, um nicht wegzuklicken. Wenn er bleibt, klickt er sich tiefer — von einer Person zur nächsten, von einem Ereignis zu einem Ort. Er teilt, was ihn berührt oder überrascht.

Er ist die Einstiegsdroge für Karoline und Wolfgang: er zeigt ihnen, dass das Archiv existiert. Er konvertiert nie ohne ein emotionales Ersterlebnis. Der erste Satz, den er liest, entscheidet alles.

### Jobs to be Done

1. **„Überrasche mich mit etwas Konkretem aus dieser Zeit"** — kuratorierter Einstieg: eine Szene, ein Zitat, ein Datum aus einem Protokoll
2. **„Zeige mir, wie das alles zusammenhängt"** — visuelle Exploration: Zeitstrahl, Karte, Personen-Graph — ohne Login, nur öffentliche Objekte
3. **„Ich will das teilen / bookmarken"** — stabile, linkbare Einzelseiten für alle öffentlichen Entitäten

## Archetyp 5: „Der Vorstand" — Klaus-Peter

### Profil

| Attribut | Ausprägung |
|---|---|
| **Name** | Klaus-Peter, 61 Jahre |
| **Funktion** | Präsident oder Vorstandsmitglied, Rotary Club Dresden |
| **Digitale Kompetenz** | Mittel — E-Mail, PDF, gelegentlich LinkedIn |
| **Zugang** | Interne Preview / Demo-Version; entscheidet über Freigabe des Projekts |
| **Anlass** | Ihm wird das Projekt vorgestellt. Er muss entscheiden, ob der Club zustimmt. |

### Narrative Beschreibung

Klaus-Peter ist kein Feind des Projekts — er ist sein Gatekeeper. Er schätzt Geschichte und Clubtradition, aber er trägt Verantwortung: für lebende Mitglieder, deren Namen in alten Protokollen stehen, für den Ruf des Clubs nach außen, für das, was er nicht kontrollieren kann, sobald etwas öffentlich ist.

Sein Bauchgefühl ist Skepsis, nicht Ablehnung. Er fragt nicht „Warum sollten wir das machen?", sondern „Was passiert, wenn etwas schiefläuft?" Wenn er eine klare Antwort auf diese Frage bekommt — und das System selbst diese Antwort verkörpert — kann er Ja sagen.

Er ist **kein dauerhafter Nutzer des Frontends.** Er ist die Person, die einmalig überzeugt werden muss, damit alle anderen Archetypen überhaupt Zugang bekommen.

### Kernbedenken

| Bedenken | Konkrete Befürchtung |
|---|---|
| **Kontrollverlust** | „Sobald das online ist, können wir nicht mehr zurück" |
| **Reputationsrisiko** | „Was, wenn Dokumente aus den 30ern falsch interpretiert werden?" |
| **Datenschutz** | „Lebende Mitglieder müssen zustimmen, bevor ihre Namen erscheinen" |
| **Kompetenz-Zweifel** | „Wer pflegt das? Was passiert, wenn der Projektinhaber aufhört?" |
| **Präzedenzfall** | „Wenn wir das freigeben, was erwarten andere dann als nächstes?" |

### Jobs to be Done

1. **„Ich muss sicher sein, dass wir das kontrollieren können, bevor wir zustimmen"** — Das System muss Kontrolle nicht versprechen, sondern demonstrieren: das `is_public`-Flag als sichtbares, verständliches Instrument
2. **„Zeige mir, was ein normaler Besucher sieht — und was er *nicht* sieht"** — Eine klare, nicht-technische Erklärung des Zugriffsmodells; idealerweise direkt im Frontend sichtbar (V12)
3. **„Ich will wissen, was mit den 90ern passiert"** — Explizite Zusicherung: Protokolle und Personen der 90er sind standardmäßig nicht-öffentlich; jede Freigabe ist eine bewusste Entscheidung des Clubs

### Design-Konsequenz

Klaus-Peter wird das Frontend einmal, konzentriert, in einer Vorstandssitzung oder per geteiltem Link sehen. **Erster Eindruck ist alles.** Das System muss in dieser einen Begegnung Vertrauen aufbauen — durch Transparenz, nicht durch Überzeugungsrhetorik.

- V12 (Über das Projekt) ist für Klaus-Peter die wichtigste Seite des gesamten Frontends
- Der Satz „Was der Club kontrolliert" muss dort explizit stehen
- Das `is_public`-Flag darf nicht nur technisch existieren — es muss für einen nicht-technischen Vorstand verständlich sein

---

## Konsequenzen für Design & Entwicklung (aktualisiert v1.2)

1. **Keine „One size fits all"-Startseite.** Die Startseite muss mehrere Einstiege gleichzeitig ermöglichen: Suchfeld (Karoline/Miriam), kuratorierter Story-Block (Jannik), Login-CTA für Mitglieder (Wolfgang).

2. **Jede Entität ist ein Rabbit-Hole-Eingang.** Jede Person, jedes Dokument, jeder Ort muss querverlinkt sein — nicht als Feature, sondern als Grundprinzip der IA.

3. **Beitragen ohne Hürde.** Das Einreichen von Stories und Korrekturen muss ohne Account möglich sein — mit dem Unterschied, dass der Beitrag dann in eine Moderationswarteschlange geht statt direkt live zu gehen.

4. **Zugang als Objekteigenschaft, nicht als Rolle.** Ein einziges `is_public`-Boolean auf jeder Tabelle — flexibel, verständlich, kontrollierbar.

5. **Klaus-Peter zuerst.** In Phase 1 (vor Club-Freigabe) ist der Vorstand die primäre Zielgruppe. Das Frontend ist ein Demonstrator, der Vertrauen aufbaut — nicht ein vollständiges System, das alles zeigt. Wenige gut erschlossene Personen und ein überzeugend erklärtes Kontrollmodell sind wichtiger als Vollständigkeit.
'''



---

## Archetyp-Übersicht

| | Karoline | Wolfgang | Dr. Miriam | Jannik |
|---|---|---|---|---|
| **Einstieg** | Suche nach Name | Eigene Biografie | Forschungsfrage | Entdeckung |
| **Account** | Optional | Ja | Ja | Nein |
| **Primärepoche** | 30er | 90er | 30er | Beide |
| **Verweildauer** | Lang, episodisch | Mittel, wiederkehrend | Sehr lang, intensiv | Kurz, aber tief wenn getriggert |
| **Beitrag** | Mit oder ohne Account (dann Freigabe) | Direkt sichtbar | Direkt sichtbar | Mit oder ohne Account |
| **Kernemotion** | Entdeckung & Verbindung | Wiedererkennung & Zugehörigkeit | Erkenntnisgewinn | Faszination & Staunen |

---

## Konsequenzen für Design & Entwicklung

1. **Keine „One size fits all"-Startseite.** Die Startseite muss mehrere Einstiege gleichzeitig ermöglichen: Suchfeld (Karoline/Miriam), kuratorierter Story-Block (Jannik), Login-CTA für Mitglieder (Wolfgang).

2. **Jede Entität ist ein Rabbit-Hole-Eingang.** Jede Person, jedes Dokument, jeder Ort muss querverlinkt sein — nicht als Feature, sondern als Grundprinzip der IA.

3. **Beitragen ohne Hürde.** Das Einreichen von Stories und Korrekturen muss ohne Account möglich sein — mit dem Unterschied, dass der Beitrag dann in eine Moderationswarteschlange geht statt direkt live zu gehen. Das ist kein Nachteil, sondern ein kommunizierbarer Unterschied.

4. **Zugang als Objekteigenschaft, nicht als Rolle.** Es gibt keine festen „Mitglieder-Seiten" — stattdessen trägt jede Person, jedes Protokoll, jede Story ein Flag (`öffentlich` / `nicht-öffentlich`). Das macht das System flexibel: Ein einzelnes Dokument aus den 90ern kann öffentlich gemacht werden, ohne die gesamte Epoche freizuschalten.
