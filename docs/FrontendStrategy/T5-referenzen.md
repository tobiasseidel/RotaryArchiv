# T5-referenzen.md — Referenzanalyse: Digitale Archiv-Frontends

> **Version:** 1.0 — 2026-05-02
> **Thread:** T5 Frontend/Design
> **Phase:** 1 — Referenzanalyse
> **Status:** Fertig — bestätigt

---

## Methodik

Vier Referenzprojekte wurden ausgewählt nach den Kriterien:
- Historisches oder kulturelles Archivmaterial (kein reines Bibliotheksportal)
- Frontend, das Personen/Geschichten in den Mittelpunkt stellt
- Nachweislich überzeugende UI-Entscheidungen, nicht nur vollständige Datenmenge
- Vergleichbarkeit mit RotaryArchiv in Umfang oder Mission

---

## Referenz 1: Memory of Nations / Paměť národa (memoryofnations.eu)

**Was:** Zeugnis-Archiv von Post Bellum (CZ) — über 13.000 Lebensgeschichten von
Zeitzeugen des 20. Jahrhunderts, NS-Zeit und Kommunismus. Seit 2008 öffentlich.

### Was sie besonders gut machen

- **Person als Einstiegspunkt:** Das Portal navigiert konsequent über Porträt-Fotos
  mit Namen und Jahreszahl. Man klickt nie auf einen Aktentyp — man klickt auf
  ein Gesicht. Das ist die direkteste Umsetzung des Prinzips „Namen werden zu Menschen".
- **Emotionale Eröffnung:** Kein Willkommenstext, sondern sofort ein Zitat aus einem
  Zeugnis — konkret, datiert, persönlich. Der Besucher ist in 3 Sekunden mittendrin.
- **Würdevolle Lückenbehandlung:** Wenn ein Beitrag noch nicht vollständig erschlossen
  ist, erscheint ein ruhiger Platzhalter mit dem Hinweis, dass die Arbeit weitergeht —
  kein Fehlerzustand, keine Blockierung.

### Was wir anders/besser machen würden

- Memoryofnations ist video-zentriert (Filmzeugnis). RotaryArchiv ist dokument-zentriert —
  das erfordert eine stärkere typografische Führung und weniger Thumbnail-Grid.
- Die Suche bei Memoryofnations ist primär namensbasiert. Wir brauchen zusätzlich
  Epochen-Navigation und Entity-übergreifendes Rabbit-Hole-Prinzip.
- Das Interface wirkt auf Mobile etwas eng — wir würden konsequenter mobiloptimieren.

### Direkter Inspirationsaspekt für RotaryArchiv

→ **Person-First-Einstieg:** Die Startseite und alle Listenansichten zeigen zunächst
ein Gesicht oder einen Namen mit emotionalem Anker (Datum, Rolle, ein Satz) — nie
eine abstrakte Kategorieliste. Auch wenn RotaryArchiv weniger Porträtfotos hat, kann
diese Logik auf das erste Zitat aus dem Protokoll übertragen werden.

---

## Referenz 2: Europeana Collections (europeana.eu)

**Was:** EU-weites Kulturerbe-Portal mit über 55 Millionen digitalen Objekten —
Bücher, Kunst, Fotos, Musik. Flagship-Projekt der EU-Kulturdigitalisierung.

### Was sie besonders gut machen

- **Konsistentes Designsystem:** Europeana hat ein dokumentiertes, offenes Designsystem
  (Vanilla Framework / eigenes CSS). Jede Komponente — Card, Filter, Hero — folgt
  denselben Regeln, egal welches Objekt angezeigt wird. Das schafft Orientierung
  trotz enormer Datenheterogenität.
- **Thematische Einstiege (Exhibitions):** Neben der Suchfunktion gibt es kuratierte
  Ausstellungen mit redaktionellem Text und visueller Führung — ein Modell, das das
  Rabbit-Hole-Prinzip auf eine redaktionelle Ebene hebt.
- **API-orientiertes Denken im Frontend:** Das Interface ist so gebaut, dass es API-
  Responses direkt visualisiert, ohne proprietäre Logik. Gute Vorlage für ein
  Backend-B-getriebenes SPA.

### Was wir anders/besser machen würden

- Europeana ist zu breit, zu kühl, zu bibliothekarisch für RotaryArchiv. Die Wärme
  fehlt. Beige und historische Materialität sind kein Thema bei Europeana —
  es ist ein Portal für Profis, nicht eine emotionale Einladung.
- Die Startseite ist von Suchfeld dominiert. Für RotaryArchiv, wo viele Besucher
  noch nicht wissen, wonach sie suchen (Jannik, Karoline), ist Entdecken wichtiger
  als gezieltes Suchen.
- Europeana hat kein Zwei-Epochen-Konzept — alles ist flach. Wir brauchen eine
  visuelle Zeitschicht.

### Direkter Inspirationsaspekt für RotaryArchiv

→ **Strukturelles Denken in Komponenten:** Europeanas Ansatz, jede Entität (Buch,
Person, Foto, Ort) durch dieselbe Card-Architektur darzustellen — aber mit
typenspezifischen Varianten — ist direkt übertragbar auf unsere EntityCard
(Person / Ort / Ereignis / Dokument).

---

## Referenz 3: Deutsche Digitale Bibliothek (deutsche-digitale-bibliothek.de)

**Was:** Nationales Portal für digitalisiertes Kulturerbe Deutschlands —
Bibliotheken, Archive, Museen. Relaunch 2023 mit neuem Designsystem.

### Was sie besonders gut machen

- **Zweisprachige Lesbarkeit:** Das DDB-Interface löst das Spannungsfeld zwischen
  wissenschaftlicher Vollständigkeit (Metadaten, Quellenangaben) und Laien-Lesbarkeit
  besonders gut: Metadaten sind ausklappbar, der Fließtext steht im Vordergrund.
- **Dokumentansicht mit Kontext:** Scans werden nebeneinander mit Transkription
  und Metadaten gezeigt — nicht als Anhang, sondern als gleichwertiger Inhalt.
  Direkt verwertbar für V04 Dokumentansicht.
- **Würdevolles Branding:** Kein Tech-Look, kein Museum-Kitsch. Die Farbpalette
  (dunkles Anthrazit, warmes Creme) fühlt sich institutionell an — wie eine gute
  Bibliothek aussieht. Hohe typografische Qualität.

### Was wir anders/besser machen würden

- DDB ist strukturell sehr flach — kein Netzwerk, keine Querverweise zwischen Personen.
  Wir haben das Rabbit-Hole-Prinzip mit Triplestore-Tiefe — das nutzen wir viel stärker.
- Der emotionale Ton ist bei DDB neutral-informativ. RotaryArchiv hat eine eigene Stimme
  (T1-emotionaler-kern.md) — die muss konsequent auch in Micro-Copy, Leerstände und
  Ladeanimationen einfließen.
- Die DDB-Startseite ist redaktionell und kuratiert — für ein Projekt unserer Größe
  ein zu großer Pflegeaufwand. Wir brauchen eine Startseite, die sich aus den Daten
  selbst generiert (Featured Entity, Zitat des Tages, Erschließungsfortschritt).

### Direkter Inspirationsaspekt für RotaryArchiv

→ **Dual-View für Dokumente:** Scan links, Transkription rechts, synchrones Scrollen.
DDB macht das für gescannte Bücher — wir übertragen es auf Sitzungsprotokolle.
Die Idee, den Scan nicht als separaten Download zu behandeln, sondern als primäre
Leserfahrung, ist genau die archivarische Materialität, die T1-emotionaler-kern.md fordert.

---

## Referenz 4: Mapping the Republic of Letters (Stanford)

**Was:** Digital-Humanities-Projekt der Stanford University — visualisiert
Briefkorrespondenzen europäischer Gelehrter des 16.–18. Jahrhunderts als Netzwerk.

### Was sie besonders gut machen

- **Netzwerk als primäre Navigation:** Der Einstieg ist nicht eine Liste, sondern
  ein Netzwerk-Graph — Personen als Knoten, Briefe als Kanten. Das Rabbit-Hole
  entsteht durch Klicken im Graphen, nicht durch Blättern in Tabellen.
- **Zeit + Raum kombiniert:** Neben dem Netzwerk gibt es eine Kartenansicht, die
  denselben Datenbestand räumlich darstellt — zwei Perspektiven auf dieselben Entitäten.
  Direkte Parallele zu V06 Karte und V07 Netzwerk-Graph in RotaryArchiv.
- **Wissenschaftliche Zitierbarkeit:** Jede Ressource hat eine persistente URI und
  einen zitierfähigen Export. Dr. Miriam (unsere Forscherin-Persona) würde das sofort
  verstehen und schätzen.

### Was wir anders/besser machen würden

- Das Projekt ist akademisch und technisch — es fehlt die emotionale Zugänglichkeit
  für Karoline (Familiendetektivin) oder Jannik (Neugieriger). Die Einstiegshürde
  ist hoch. RotaryArchiv braucht beide: wissenschaftliche Tiefe UND niedrigschwelligen
  Einstieg.
- Die Visualisierungen sind schön, aber langsam und Desktop-only. Unser Netzwerk-Graph
  (V07) muss auch auf mittelstarken Geräten flüssig laufen — weniger Komplexität,
  mehr Fokus.
- Das Design ist 2010er-Web — keine moderne Typografie, kein Spacing-System. Wir
  bauen auf 2026-Standards.

### Direkter Inspirationsaspekt für RotaryArchiv

→ **Netzwerk-Graph als Entdeckungswerkzeug:** Nicht als Beiwerk, sondern als
eigenständige View (V07). Der Graph ist kein Datenanhang — er ist eine Leseart
des Archivs: Wer kannte wen? Wer war bei welcher Sitzung? Das macht aus Daten
eine Geschichte. Das Interaktionsprinzip (Klick auf Knoten → Personenprofil) ist
direkt in unsere Entity-First-Navigation übertragbar.

---

## Synthese: Was RotaryArchiv von allen Vier lernt

| Referenz | Stärke | Unser Vorteil gegenüber |
|---|---|---|
| Memory of Nations | Person-First, emotionaler Einstieg | Dokument-Tiefe + Zwei-Epochen-Kontext |
| Europeana | Konsistentes Komponenten-System | Wärmere Tonalität, Rabbit-Hole-Tiefe |
| Deutsche Digitale Bibliothek | Dual-View, würdevolles Branding | Eigene Stimme, automatisch generierte Startseite |
| Republic of Letters | Netzwerk als Navigation | Niedrigschwelliger Einstieg, Mobile-tauglich |

### Das RotaryArchiv-Designprinzip als Synthese

> Jede Ansicht muss **zwei Dinge gleichzeitig** können:
> 1. Einen unvorbereiteten Besucher in 10 Sekunden emotional anfassen.
> 2. Einem Forscher alle Werkzeuge geben, die er für zitierfähige Arbeit braucht.
>
> Das ist keine Entweder-Oder-Entscheidung. Es ist eine Gestaltungsaufgabe.
