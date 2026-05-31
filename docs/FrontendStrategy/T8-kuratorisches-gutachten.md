# T8-kuratorisches-gutachten.md
# Kuratorisch-historisches Gutachten — RotaryArchiv

> **Version:** 1.0 — 2026-05-03
> **Thread:** T8 Kurator / Historiker
> **Gutachter-Rolle:** Historiker und Kurator digitaler Ausstellungen
> **Grundlage:** project-brief_v04.md, T1-emotionaler-kern.md, T5-designsystem-v1.1.md, T5-wow-features-v2.md
> **Rahmenbedingungen (geklärt):**
> - Keine professionellen Redakteure — Kuratierung durch LLM-gestützte Workflows
> - Begrenzte Reichweite, Community-nahe Öffentlichkeit
> - Sekundärquellen punktuell (Memoiren), keine systematisch erschlossene Forschungsliteratur

---

## Vorbemerkung zur Bewertungsgrundlage

Dieses Gutachten bewertet das Projekt unter realen Bedingungen: **kein Redaktionsteam,
kein historisches Fachpersonal, punktuelle Quellenlage.** Das verändert mehrere
Bewertungen gegenüber einem musealen Standardsetting. Wo das Projekt unter Idealbedingungen
„tragfähig" wäre, kann es unter diesen Bedingungen „Verbesserungsbedarf" haben —
nicht weil die Idee schlecht ist, sondern weil die Ausführung menschliche Kapazität
voraussetzt, die nicht vorhanden ist.

Eine konsequente Empfehlung zieht sich durch das gesamte Gutachten:
**LLM-gestützte Redaktionsassistenz muss als expliziter Workflow im Projekt
verankert werden, nicht als gelegentliches Hilfsmittel.**

---

## 1. HISTORISCHE INTEGRITÄT

### 1.1 Epochenbezeichnung „Die 30er" für den Zeitraum 1927–1937

**Bewertung: ⚠️ Verbesserungsbedarf**

Die Bezeichnung „Die 30er" für einen Zeitraum, der 1927 beginnt, ist historisch
unscharf. Der Club wurde gegründet, bevor die 30er Jahre begannen — und das ist
kein Zufall, sondern Teil der Geschichte: die Weimarer Republik-Jahre 1927–1932
sind historisch grundverschieden von den NS-Jahren 1933–1937. Beide Phasen in
einer Epochenbezeichnung zu bündeln, die implizit auf die 30er Jahre verweist,
erzeugt ein stilles Narrativ: als wäre die gesamte Epoche vom Schatten des NS
geprägt.

**Was konkret passiert:** Ein Besucher, der die Epochen-Übersicht sieht, nimmt
„Die 30er" als Einheit wahr. Die interne Periodisierung Weimar/NS existiert nicht
als sichtbare Struktur. Die Protokolle von 1929 werden visuell gleichgestellt mit
denen von 1935 — obwohl sie historisch in verschiedenen Welten entstanden.

**Empfehlung:** Keine Umbenennung der Epoche, aber eine **sichtbare Binnendifferenzierung**
auf V02: ein kurzer kuratorischer Einführungstext, der 1927–1932 und 1933–1937 explizit
als zwei Phasen benennt. Kein technisches Feature, kein Redesign — ein Absatz Text,
der den Kontext setzt, bevor der Amtsstrahl beginnt.

---

### 1.2 Kuratorische Haltung „ehrlicher Zeuge, nicht Ankläger"

**Bewertung: ✅ Tragfähig — mit einer wichtigen Einschränkung**

Die Haltung ist kuratorisch valide. Sie entspricht der Praxis seriöser Ausstellungsprojekte
zu lokaler NS-Geschichte: Das Dokumentieren ohne Verurteilen ist legitim, solange
das Projekt **nicht durch Schweigen schützt, was Sprache braucht.**

Das Projekt tut das an den entscheidenden Stellen nicht: Das Vereinsverbot 1937 wird
in der Epochen-Übersicht explizit benannt (laut T1-emotionaler-kern.md). Die
HistoricalContextBox ist als Instrument vorhanden. Das Leitprinzip „Muster zeigen,
nicht behaupten" ist methodisch sauber.

**Die Einschränkung:** Die Haltung ist nur dann „ehrlicher Zeuge", wenn der Zeuge
tatsächlich spricht — wenn redaktionelle Kontextboxen auch gesetzt werden. Unter
den gegebenen Bedingungen (kein Redaktionsteam) besteht die Gefahr, dass die
Haltung de facto zu „schweigender Zeuge" wird. Die Haltung ist richtig — die
operative Absicherung fehlt noch. Dazu mehr unter Prüfpunkt 1.4.

---

### 1.3 Feature H — „Die stille Welle": Austritte als sichtbares Muster ohne Kommentar

**Bewertung: ⚠️ Verbesserungsbedarf**

Feature H ist museumspädagogisch das heikelste Element des gesamten Projekts —
und gleichzeitig eines der wirkungsvollsten. Die Verdichtung der Austritte 1933–1935
als visuelles Muster ohne Kommentar zu zeigen, folgt dem Prinzip „Muster zeigen,
nicht behaupten" — das ist methodisch integer.

**Das Problem liegt nicht in der Visualisierung, sondern in der Rahmungslosigkeit.**
Ein Besucher ohne historisches Vorwissen sieht die Welle und kann mehrere Narrative
konstruieren:

1. *Natürliche Fluktuation* — ohne Kontext ist das nicht ausgeschlossen
2. *Politischer Druck* — das intendierte Verständnis
3. *Clubinterne Krise* (Finanzen, Führungsstreit) — ebenfalls ohne Gegennachweis
   nicht ausschließbar

Das Projekt verlässt sich darauf, dass der Besucher das richtige Narrativ
mitbringt. Das ist unter einer kleinen, historisch versierten Community akzeptabel.
Sobald das Archiv auch von Personen besucht wird, die keinen Kontext mitbringen
(Schüler, Zufallsbesucher, Journalisten), wird das zum Problem.

**Konkrete Empfehlung:** Feature H braucht **einen einzigen kuratorischen Rahmentext**
auf V02a, der vor dem Amtsstrahl erscheint — nicht als Erklärung jedes einzelnen
Austritts, sondern als historischer Kontext für die Epoche insgesamt. Dieser Text
kann LLM-generiert und redaktionell freigegeben sein. Er muss nicht jeden Fall
auflösen — er muss dem Besucher das Werkzeug geben, das Muster einzuordnen.

---

### 1.4 Feature E — Kontexthinweis bei Austritt: Wann Pflicht, wann optional?

**Bewertung: ⚠️ Verbesserungsbedarf**

Das aktuelle Konzept überlässt die Entscheidung vollständig dem Admin. Das ist unter
Idealbedingungen (kompetenter Redakteur, Zeit, Quellenlage) richtig. Unter den
tatsächlichen Bedingungen dieses Projekts ist es **strukturell riskant**, weil der
Hinweis systematisch fehlen wird — nicht aus böser Absicht, sondern weil die
Kapazität fehlt.

**Vorschlag: Drei-Stufen-Pflichtigkeit**

| Bedingung | Handlung |
|---|---|
| Austritt mit Datum zwischen 1933–1937 | **Pflicht-Trigger:** HistoricalContextBox erscheint automatisch mit einem **generischen Epochentext** (kein Urteil über die Person, nur Kontext zur Zeit). Kann vom Admin durch einen spezifischeren Text ersetzt, aber nicht stumm geschaltet werden. |
| Austritt mit Formulierung „persönliche Gründe" oder ähnlich in 1933–1937 | **Verstärkter Pflicht-Trigger:** Generischer Text + Hinweis auf Forschungsstand zur Euphemisierung dieser Formulierung in dieser Zeit. |
| Austritt außerhalb 1933–1937 oder mit erklärbarem Grund | **Optional:** Admin entscheidet frei. |

Der generische Epochentext für Stufe 1 und 2 kann einmalig LLM-generiert,
redaktionell freigegeben und als Template hinterlegt werden. Das ist einmalige Arbeit,
kein laufender Aufwand.

---

## 2. NARRATIVE ARCHITEKTUR

### 2.1 Rabbit-Hole-Prinzip: Welche Geschichten entstehen automatisch?

**Bewertung: ⚠️ Verbesserungsbedarf**

Das Rabbit-Hole-Prinzip erzeugt Narrative durch Klickpfade. Das ist kein Fehler —
es ist das Kernprinzip. Aber es ist nicht neutral. Jede Architekturentscheidung
bevorzugt bestimmte Geschichten.

**Geschichten, die automatisch entstehen (durch die Architektur begünstigt):**
- Die Geschichte des aktiven, präsenten Mitglieds (Heatmap zeigt Anwesenheit)
- Die Geschichte des Amtsinhabers (Amtsstrahl macht ihn sichtbar)
- Die Geschichte des Aufgenommenen und des Ausgetretenen (Feature E)
- Die Geschichte der Lücke (GapInline, unleserlicher Text)

**Geschichten, die systematisch unsichtbar werden:**
- Die Geschichte des stillen Mitglieds, das immer da war, aber nie ein Amt innehatte
  und nie namentlich im Protokoll erwähnt wurde — es existiert im Archiv faktisch nicht
- Die Geschichte der Frauen: Rotary war in dieser Epoche eine reine Männerorganisation.
  Die Abwesenheit von Frauen in den Protokollen ist selbst ein historisches Faktum —
  das Interface erzeugt aber keine Sichtbarkeit dieser strukturellen Abwesenheit
- Die Geschichte des gesellschaftlichen Umfelds: Das Archiv ist clubzentriert. Dresden
  1933–1937 außerhalb des Clubs existiert nur als Kontext-Box, nie als eigenständige
  Erzählschicht

**Empfehlung:** Kein Redesign. Aber ein kuratorischer Hinweis auf V12 (Über das
Projekt), der transparent macht, welche Perspektiven das Archiv strukturell nicht
abbilden kann. Das ist keine Schwäche — es ist wissenschaftliche Ehrlichkeit.

---

### 2.2 Feature D — Amtsstrahl: Normalität als Norm?

**Bewertung: ⚠️ Verbesserungsbedarf**

Der Amtsstrahl ist das stärkste strukturelle Feature des Projekts. Die Entscheidung,
jährliche Rotation als „das ist Rotary — das ist normal" zu codieren, ist historisch
korrekt und vermittlungspolitisch sauber.

**Das blinde Fleck:** Was passiert in den Jahren, in denen die „normale Rotation"
nicht stattfand? Das Interface zeigt: `░░░░ 34/35` — eine Lücke, klickbar.
Aber: Die Lücke kommuniziert „unbekannt", nicht „ausgefallen". Ein leeres Feld
im Amtsstrahl für 1934/35 könnte bedeuten:

a) Der Präsident dieses Jahres ist aus den Protokollen nicht rekonstruierbar  
b) Es gab in diesem Jahr aus politischen Gründen keinen regulären Amtswechsel  
c) Das Amt wurde durch Druck von außen besetzt

Das Interface unterscheidet diese Fälle nicht. Die Lücke ist stumm.

**Empfehlung:** Drei Lücken-Typen visuell und semantisch differenzieren:
- `░░░░` = Quelle unleserlich / Name unbekannt (aktueller Stand)
- `—` (Gedankenstrich, gedimmt) = Kein Amtswechsel in diesem Jahr dokumentiert
- Ocker-Hinterlegung = Amtswechsel dokumentiert, aber außerordentlich (kein regulärer Wahlvorgang)

Das ist eine kleine Designerweiterung mit erheblichem historischen Aussagegewinn.

---

### 2.3 Fehlendes explizites kuratorisches Narrativ

**Bewertung: ❌ Überarbeitung nötig**

Das ist der gravierendste Befund des gesamten Gutachtens.

Das Projekt hat eine emotionale Rahmung (Leitprinzip), ein technisches Prinzip
(Rabbit Hole), und ein Designsystem. Es hat **keine kuratorische Stimme**, die
dem Besucher sagt: *Warum ist dieses Archiv so gebaut, wie es gebaut ist? Wer
hat entschieden, was gezeigt wird — und nach welchen Kriterien? Was fehlt, und warum?*

Das ist kein V12-Problem (Über das Projekt). V12 erklärt das Projekt als Projekt.
Was fehlt, ist eine **„Stimme des Archivs"** — ein kuratorisches Rahmendokument,
das dem Besucher die Haltung des Archivs transparent macht:

- Welche Quellen liegen vor, welche fehlen?
- Nach welchen Prinzipien wurden Entscheidungen zur Sichtbarkeit getroffen?
- Was kann dieses Archiv nicht leisten — und warum?
- Wie soll der Besucher mit widersprüchlichen Quellen umgehen?

Ohne diese Stimme übernimmt das Interface de facto die Funktion des Kurators —
durch seine Architektur, nicht durch seinen Inhalt. Das ist die präzise Definition
eines unkontrollierten Narrativs.

**Empfehlung:** Eine eigene View — oder ein persistent zugängliches Element auf
V12 — die explizit als „Kuratorisches Statement" gekennzeichnet ist. Umfang:
400–600 Wörter. Inhalt: Quellenlage, Auswahlprinzipien, strukturelle Blindstellen,
Haltung zu den schwierigen Jahren. Dieser Text kann LLM-generiert und einmalig
freigegeben werden. Er ist kein laufender Aufwand — aber er ist unbedingt nötig.

---

## 3. COMMUNITY-BEITRÄGE UND KONTROLLE

### 3.1 Anonyme Beiträge über historische Personen ohne Quellenbelege

**Bewertung: ⚠️ Verbesserungsbedarf**

Das Modell — anonyme Beiträge in Moderationswarteschlange, nach Freigabe sichtbar —
ist für einen Community-nahen Kontext akzeptabel. Das Risiko liegt nicht im
Missbrauch (zu kleine Plattform, zu spezifisches Thema), sondern in der
**epistemischen Gleichstellung**: Ein freigegebener Community-Beitrag neben einem
Primärquelle hat im Interface visuell denselben Status wie ein redaktioneller Text —
wenn die Differenzierung nicht konsequent durchgehalten wird.

**Das spezifische Risiko für dieses Projekt:** Familienerzählungen zur NS-Zeit
sind häufig retrospektiv entlastet. Memoiren beschönigen. Ein Enkelbeitrag, der
seinen Großvater als „Widerständler" rahmt, der aus dem Club austrat, weil er
„die Nazis nicht mochte", ist schwer zu falsifizieren — und schwer freizugeben,
ohne ihn zu bestätigen.

**Empfehlung:** Drei operative Maßnahmen:
1. **Pflicht-Quellenfeld** im Beitragsformular (nicht optional): „Worauf stützt
   sich dieser Beitrag?" — auch wenn die Antwort „mündliche Überlieferung meiner
   Familie" ist. Transparenz über die Quelle ist wichtiger als Quellenqualität.
2. **Sichtbares Herkunfts-Label** auf jedem freigegebenen Beitrag:
   „Community-Beitrag · Quelle: [Familienüberlieferung / Dokument / Memoiren]" —
   kein verstecktes Metadaten-Tag, sondern lesbarer Hinweis direkt im Beitragstext.
3. **LLM-gestütztes Freigabe-Screening:** Vor der Admin-Entscheidung automatisch
   eine LLM-Analyse des Beitrags: enthält er historische Behauptungen, die eine
   Kontextbox erfordern würden? Das entlastet den Admin und schützt vor unbewusster
   Gleichstellung.

---

### 3.2 Story-Typografie: Community vs. Editorial — Erkennbarkeit für Besucher

**Bewertung: ⚠️ Verbesserungsbedarf**

Das technische Unterscheidungsmerkmal (`story_type: community / editorial`) ist
vorhanden. Die inhaltliche Erkennbarkeit ist es nicht.

**Was heute im Konzept fehlt:** Ein Besucher, der eine Story liest, muss verstehen,
dass „community" nicht dasselbe ist wie „editorial" — nicht nur durch ein Icon oder
ein Badge, sondern durch einen kurzen Satz, der erklärt, was der Unterschied bedeutet:

- Editorial: „Dieser Text wurde vom Redaktionsteam des RotaryArchivs erstellt und
  auf Basis der vorliegenden Quellen geprüft."
- Community: „Dieser Beitrag wurde von einem Besucher eingereicht und vom
  Redaktionsteam freigegeben, aber nicht inhaltlich überprüft."

Das ist keine Designfrage — das ist eine Transparenz- und Vertrauensfrage.

**Empfehlung:** Feste Disclaimer-Texte für beide Story-Typen, die unterhalb des
Titels jeder Story erscheinen — immer, nicht nur auf Hover.

---

### 3.3 Feature C — Consent-Selbstidentifikation: Missbrauchspotenzial

**Bewertung: ⚠️ Verbesserungsbedarf**

Das Risiko einer Falsch-Identifikation ist im Kontext der 90er-Epoche (lebende
Personen!) erheblich. Jemand identifiziert sich als Person X → erhöht den
Consent-Score → ermöglicht ggf. Freischaltung von Dokumenten, die diese Person
lieber nicht öffentlich sehen würde.

Das aktuelle Konzept hat keine Verifikationsstufe zwischen Selbstidentifikation
und Consent-Effekt.

**Empfehlung:** Für die 90er-Epoche: Selbstidentifikation löst **keinen
automatischen Consent-Score-Anstieg** aus, bevor ein Admin die Identifikation
bestätigt hat (nicht inhaltlich — nur: „wirkt dieser Account plausibel?").
Das ist ein kleiner Workflow-Schritt, verhindert aber systematischen Missbrauch.
Für historische Personen (30er, verstorben): kein Consent-System nötig —
Freischaltung liegt bei Admin.

---

## 4. DESIGN ALS AUSSAGE

### 4.1 Epochenfarben: Archivgrün vs. Mauerfall-Blau

**Bewertung: ✅ Tragfähig — mit einer Nuancierung**

Die Farbentscheidungen sind gut begründet und historisch reflektiert. Archivgrün
für die bürgerliche Weimarer/NS-Übergangszeit, Mitternachtsblau für die Nachwendezeit —
das ist keine naive Romantisierung, sondern eine bewusste Absetzung von
NS-Ästhetik-Assoziationen. Die Begründung in T5-designsystem.md (Aktendeckel,
Schreibtischunterlagen der Zwischenkriegszeit) ist kuratorisch integer.

**Die Nuancierung:** Die Farbe codiert die Epoche — aber sie codiert sie als
Einheit. Wie unter Punkt 1.1 beschrieben, sind 1927–1932 und 1933–1937 historisch
verschiedene Phasen. Das Archivgrün gilt für beide gleichmäßig. Das ist kein
Designfehler — aber es verstärkt die unter 1.1 beschriebene Rahmungslosigkeit.

Wenn die unter 1.1 empfohlene Binnendifferenzierung auf V02 als Text eingeführt
wird, ist dieser Befund damit adressiert. Keine eigene Maßnahme nötig.

---

### 4.2 „Vergessene Namen werden wieder zu Menschen" — Rahmung für alle Personen?

**Bewertung: ⚠️ Verbesserungsbedarf**

Der emotionale Kern ist stark, ehrlich und für die überwiegende Mehrheit der
archivierten Personen richtig: Clubmitglieder, die in den Protokollen namentlich
erwähnt werden und deren Geschichte sonst unsichtbar geblieben wäre.

**Das Problem entsteht an den Rändern:** Was, wenn ein Name im Archiv auftaucht,
der historisch belastet ist — ein Mitglied, das nachweislich aktiv in der NSDAP
war, das andere zur Aufgabe der Mitgliedschaft drängte, das vom Club profitierte,
während andere ausgeschlossen wurden?

Den Satz „vergessene Namen werden wieder zu Menschen" auf diese Person anzuwenden,
ist nicht falsch — aber er ist unvollständig. Menschen können Täter sein. Namen
können belastete Namen sein. Das Leitprinzip transportiert implizit eine
Rehabilitierungs-Erwartung, die nicht für alle Personen gilt.

**Empfehlung:** Das Leitprinzip muss nicht geändert werden — es ist der richtige
emotionale Kompass für den Regelfall. Aber es braucht eine **kuratorische Ergänzung**,
die explizit festhält: Das Archiv macht Namen sichtbar — ohne damit eine
Wertung der Person zu verbinden. Sichtbarkeit ist nicht Rehabilitation.
Dieser Satz gehört ins kuratorische Statement (siehe 2.3) — nicht in die UI.

---

### 4.3 HistoricalContextBox nur auf redaktionelle Entscheidung

**Bewertung: ❌ Überarbeitung nötig**

Unter den gegebenen Bedingungen — kein Redaktionsteam, kein laufendes
historiografisches Monitoring — ist die rein manuelle Aktivierung der
HistoricalContextBox **strukturell unzureichend**. Sie wird für die meisten
sensiblen Dokumente nicht gesetzt werden — nicht aus Nachlässigkeit, sondern
weil die Kapazität fehlt.

Das Ergebnis: Das Interface suggeriert durch das Fehlen der Box, dass kein
Kontext nötig ist. Das ist ein stilles Narrativ durch Unterlassung.

**Empfehlung — Drei-Stufen-Modell für automatische Kontextualisierung:**

**Stufe 1 — Automatisch, kein redaktioneller Aufwand:**
Alle Dokumente mit Datum 1933–1937 erhalten automatisch einen generischen
Epochenkontext-Banner — einmalig verfasst, systemweit eingesetzt. Kein
individueller Aufwand pro Dokument.

**Stufe 2 — LLM-gestützt, einmaliger Freigabe-Aufwand:**
Bei Dokumenten, die Austritte, Formulierungen wie „persönliche Gründe" oder
fehlende Sitzungsteilnehmer in 1933–1937 enthalten: automatisch eine
LLM-generierte Kontextbox vorschlagen, die der Admin mit einem Klick freigeben
oder anpassen kann. Kein Schreiben — nur Entscheiden.

**Stufe 3 — Manuell, für Ausnahmefälle:**
Spezifische, personalisierende Kontextboxen für einzelne Personen oder
Dokumente, die besondere Aufmerksamkeit verdienen. Das ist der aktuelle
Ist-Stand — er bleibt als höchste Stufe erhalten, wird aber nicht mehr
die einzige Stufe sein.

---

## Zusammenfassende Übersicht der Befunde

| Prüfpunkt | Befund | Bewertung |
|---|---|---|
| 1.1 Epochenbezeichnung „Die 30er" | Historisch unscharf, Binnendifferenzierung fehlt | ⚠️ |
| 1.2 Haltung „ehrlicher Zeuge" | Valide, aber operativ ungesichert | ✅ (mit Einschränkung) |
| 1.3 Feature H — stille Welle | Rahmungslos ohne Epochenkontext-Text | ⚠️ |
| 1.4 Feature E — Kontexthinweis wann Pflicht | Keine Pflichtstruktur definiert | ⚠️ |
| 2.1 Rabbit-Hole — unsichtbare Geschichten | Strukturelle Blindstellen nicht kommuniziert | ⚠️ |
| 2.2 Feature D — Amtsstrahl Lückentypen | Lücke kommuniziert nicht, was fehlt | ⚠️ |
| 2.3 Fehlende kuratorische Stimme | Kein kuratorisches Statement vorhanden | ❌ |
| 3.1 Anonyme Beiträge / Quellenbelege | Epistemische Gleichstellung riskant | ⚠️ |
| 3.2 Story-Typografie community/editorial | Inhaltliche Erkennbarkeit fehlt | ⚠️ |
| 3.3 Feature C — Consent-Missbrauch | Keine Verifikationsstufe für 90er | ⚠️ |
| 4.1 Epochenfarben | Tragfähig, durch 1.1-Maßnahme adressiert | ✅ |
| 4.2 Leitprinzip — belastete Personen | Implizite Rehabilitierungs-Erwartung | ⚠️ |
| 4.3 HistoricalContextBox nur manuell | Strukturell unzureichend ohne Redaktionsteam | ❌ |

---

*Dieses Gutachten ist Input für T8-iterationsauftraege.md.*
*Jeder ⚠️- und ❌-Befund hat dort einen adressierten Iterationsauftrag.*
