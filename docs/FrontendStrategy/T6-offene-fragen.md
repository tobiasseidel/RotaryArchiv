# T6-offene-fragen.md — Offene Fragen vor dem Build-Start

> **Version:** 1.0 — 2026-05-03
> **Thread:** T6 Frontend-Entwickler
> **Phase:** Planning Phase

---

## Technische Fragen

| Frage | Antwort | Priorität |
|---|---|---|
| **Pinia oder Composables für globalen State?** | **Pinia** — für Auth-State und Epoch-Store. Composables für API-Logik. | 🔴 Vor Build-Start |
| **Vue Router: Hash oder History Mode?** | **History Mode** — `createWebHistory()`. Nginx `try_files` ist bereits konfiguriert (T3-nginx-config.md). | 🔴 Vor Build-Start |
| **TypeScript in Phase 1?** | **Nein** — vereinfacht Einstieg für gelegentliche Entwickler. Optional in Phase 2. | 🟡 Vor Phase 1 Launch |
| **D3.js oder vis-network für Graph?** | **D3.js** — flexibler, bessere Kontrolle über Custom Properties. vis-network als Fallback. | 🟡 Vor Phase 2 |
| **Leaflet: Client-only?** | **Ja** — `onMounted` reicht, kein SSR. Kein Leaflet-SSR-Problem bei reinem SPA. | 🔴 Vor Build-Start |

---

## Inhaltliche Fragen

| Frage | Antwort | Priorität |
|---|---|---|
| **Welche 3 konkreten Personen für Demonstrator?** | ✅ Victor Klemperer, Fritz Busch, Heinrich Arnhold — alle 30er, alle mit Portrait | ✅ Erledigt |
| **Gibt es Portrait-Scans?** | Ja, einige vorhanden im Triplestore. Für fehlende: Initialen-Placeholder. | 🟡 Vor Phase 1 Launch |
| **Scan-Bilder für Mock-Dokumente?** | Werden als Platzhalter-Pfade eingetragen (`/scans/1929-05-15-p1.jpg`). | 🟡 Vor Phase 1 Launch |
| **BBox-Koordinaten für GapInline?** | Manuell oder aus OCR-Export. Confidence < 0.6 = GapInline. | 🟡 Vor Phase 1 Launch |

---

## Designfragen

| Frage | Antwort | Priorität |
|---|---|---|
| **Lokale Fonts oder Google Fonts CDN?** | **Lokale Fonts** — `@fontsource/lora` + `@fontsource/inter`. Kein Google Fonts CDN. | 🔴 Vor Build-Start |
| **Portrait-Format (3:4) durchsetzen?** | Ja — Aspect Ratio per CSS `aspect-ratio: 3/4`. | 🟡 Vor Phase 1 Launch |
| **Dark Mode Support?** | **Nein** — Phase 1 nicht vorgesehen. Basis-Farben aus T5-designsystem-v1.1.md. | 🟢 Vor Phase 2 |

---

## Deployment-Fragen

| Frage | Antwort | Priorität |
|---|---|---|
| **Nginx-Volume-Mount korrekt?** | Ja — `frontend_b/dist:/var/www/rotary-frontend` bereits in T3-docker-compose.md konfiguriert. | 🔴 Vor Build-Start |
| **rsync oder SFTP für Deployment?** | **rsync** — effizienter für inkrementelle Updates. `rsync -avz dist/ user@nas:/path/`. | 🟡 Vor Phase 1 Launch |
| **Smoke-Test nach Deployment?** | Manuell im Browser — Startseite, Personenprofil, Dokument. Keine automatisierten Tests in Phase 1. | 🟡 Vor Phase 1 Launch |

---

## Backend-Abhängigkeiten (für Phase 2)

| Frage | Status | Priorität |
|---|---|---|
| **Backend B lauffähig?** | ❌ Noch nicht. Frontend Phase 1 nutzt Mock-Daten. | 🟢 Vor Phase 2 |
| **REST-API Endpoints definiert?** | ✅ Ja — T2-migrations-plan.md listet alle Endpoints. | 🟢 Vor Phase 2 |
| **JWT-Auth in Backend B?** | ✅ Ja — T3-auth-konzept.md definiert JWT. | 🟢 Vor Phase 2 |
| **Stub-Response Implementierung?** | ✅ Ja — T2-migrations-plan.md spezifiziert `{ stub: true, ... }`. | 🟢 Vor Phase 2 |

---

## Zusammenfassung: Must-Haves vor Build-Start

| Priorität | Frage | Entscheidung |
|---|---|---|
| 🔴 | Pinia oder Composables? | **Pinia** |
| 🔴 | Router Mode? | **History** |
| 🔴 | Font-Quelle? | **Lokal (@fontsource)** |
| 🔴 | Nginx SPA-Fallback? | **Bereits konfiguriert** |
| 🟡 | Konkrete Personen? | ✅ Victor Klemperer, Fritz Busch, Heinrich Arnhold |
| 🟡 | Portrait-Verfügbarkeit? | ✅ 7 Personen mit Wikimedia Commons Portraits |
| 🟡 | TypeScript? | **Nein (Phase 1)** |

---

*Alle 4 Planungsdokumente erstellt. Bereit für Build-Phase.*

**Erzeugte Dateien:**
- `T6-projektstruktur.md` — Verzeichnisstruktur, Komponenten-Mapping, CSS-Tokens, Epochen-System
- `T6-mock-daten.md` — JSON-Mockdaten, useApi-Interface, Stub-Responses
- `T6-build-reihenfolge.md` — Phase 1 (11 Tage) + Phase 2 (5–6 Wochen)
- `T6-offene-fragen.md` — Technische, Inhaltliche, Design-Fragen mit Prioritäten
