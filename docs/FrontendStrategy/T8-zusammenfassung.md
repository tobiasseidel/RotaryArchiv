# T8-zusammenfassung.md
# T8 Kuratorisch-historisches Review — Abschlusszusammenfassung

> **Version:** 1.0 — 2026-05-03
> **Thread:** T8 Kurator / Historiker
> **Dokumente dieses Threads:**
> - T8-kuratorisches-gutachten.md — vollständige Bewertung (13 Befunde)
> - T8-iterationsauftraege.md — 11 Aufträge an T1 und T5
> - T8-llm-historiker-workflow.md — Betriebskonzept ohne Redaktionsteam

---

## Das Urteil in einem Satz

> Das Projekt ist konzeptionell integer — aber es vertraut zu sehr darauf,
> dass gute Absichten ohne operative Absicherung ausreichen.

---

## Was funktioniert

Das RotaryArchiv hat eine kuratorische Grundhaltung, die historisch
vertretbar ist: kein Ankläger, kein Verteidiger, ehrlicher Zeuge.
Das Designsystem trägt diese Haltung visuell. Die Entscheidung, keine
automatischen Kategorisierungen vorzunehmen, ist methodisch sauber.
Feature H (stille Welle), Feature D (Amtsstrahl) und Feature F
(Zwei Dokumente) sind im Kern starke, museumspädagogisch solide Ideen.

---

## Die zwei kritischen Lücken

**1. Keine kuratorische Stimme.**
Das Interface ist derzeit sein eigener Kurator — durch seine Architektur,
nicht durch einen menschlichen Standpunkt. Es fehlt ein kuratorisches
Statement, das dem Besucher sagt: Wer hat entschieden, was gezeigt wird?
Was kann dieses Archiv nicht? Was fehlt, und warum?
Ohne diese Stimme entstehen unkontrollierte Narrative — nicht durch
böse Absicht, sondern durch Stille.

**2. HistoricalContextBox nur manuell.**
Unter realen Bedingungen (kein Redaktionsteam) bedeutet „nur manuell"
faktisch „selten bis nie". Sensible Dokumente aus 1933–1937 werden ohne
Kontext erscheinen. Das Fehlen der Box ist selbst eine Aussage —
und eine falsche.

---

## Die fünf wichtigsten Maßnahmen vor dem Launch

| Priorität | Maßnahme | Aufwand |
|---|---|---|
| 1 | Kuratorisches Statement für V12 schreiben und freigeben | 1 Nachmittag (LLM-Entwurf + Freigabe) |
| 2 | Generischen Epochenkontext 1933–1937 als System-Template hinterlegen | 2 Stunden |
| 3 | HistoricalContextBox: automatischen Trigger für alle Dokumente 1933–1937 einbauen | T5/T6-Aufwand |
| 4 | Story-Disclaimer (Community vs. Editorial) in jede Story-Ansicht einbauen | T5-Aufwand |
| 5 | Zeithistoriker-Konsultation (HAIT Dresden / Stadtarchiv) — Texte prüfen lassen | 1 Gespräch |

---

## Was danach wartbar ist

Nach dem Launch ist das Archiv mit überschaubarem Aufwand betreibbar:
LLM screent Community-Beiträge vor, schlägt Kontextboxen vor,
der Projektinhaber klickt frei. 5–15 Minuten pro Beitrag.
Die Grundlagentexte stehen — kein laufender Schreibaufwand.

Das Archiv braucht kein Redaktionsteam.
Es braucht einen einmaligen sorgfältigen Launch.

---

## Der Satz, der bleibt

> Sichtbarkeit ist nicht Rehabilitation.
> Das Archiv macht Namen sichtbar — ohne damit eine Wertung der Person
> zu verbinden. Dieser Grundsatz muss explizit im Archiv stehen,
> nicht nur in seiner Konzeption.

---

*T8 abgeschlossen.*
