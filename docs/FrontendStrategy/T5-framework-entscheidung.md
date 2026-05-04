# T5-framework-entscheidung.md

> **Version:** 1.0 — 2026-05-03  
> **Thread:** T5 Frontend/Design  
> **Phase:** 4 — Framework-Entscheidung  
> **Input aus:** T5-designsystem-v1.1.md, T5-komponenten-v1.3.md, T3-nginx-config.md,  
>   T3-docker-compose.md, project-brief_v05.md, T2-migrations-plan.md  
> **Status:** Entschieden

---

## Gelesene Dateien — Bestätigung

| Datei | Status | Relevanz für diese Entscheidung |
|---|---|---|
| `T5-designsystem-v1.1.md` | ✅ gelesen | CSS Custom Properties, Epochen-Override-System, Lora/Inter |
| `T5-komponenten-v1.3.md` | ✅ gelesen | 13 Komponenten, 12 Views, Leaflet (K12), Netzwerk-Graph (K04), JWT-Auth-State |
| `T3-nginx-config.md` | ✅ gelesen | SPA-Fallback `try_files … /index.html`, statische Dateien aus Volume |
| `T3-docker-compose.md` | ✅ gelesen | `frontend_b/dist/` als Volume-Mount in Nginx-Container |
| `project-brief_v05.md` | ✅ gelesen | Zwei-Phasen-Modell, Synology NAS, manuelles Deployment, kein CI/CD |
| `T2-migrations-plan.md` | ✅ gelesen | REST-API-Struktur Backend B, Stub-Responses, Mock-Daten für Phase 1 |

---

## Entscheidungskontext — Zusammenfassung

Das Deployment-Modell ist klar definiert:  
`vite build` → `frontend_b/dist/` → Docker-Volume → Nginx serviert statische Dateien.  
Der `try_files $uri $uri/ /index.html`-SPA-Fallback ist bereits konfiguriert.  
Updates: lokaler Build auf Entwicklungsrechner → `rsync` oder SFTP auf NAS → `docker compose restart nginx` — fertig.

Das Frontend ist ein **klassisches SPA** (kein SSR benötigt), betrieben von einer Person,  
mit gelegentlicher Hilfe. Kein CDN. Kein Build-Server. Kein CI/CD.  
Langfristiger Betrieb über 5+ Jahre ist explizites Ziel.

---

## Bewertungsmatrix

### Kriterium 1: BETRIEB (Gewicht: hoch)

| | Option A — Vue 3 + Vite | Option B — SvelteKit | Option C — Astro + Islands | Option D — Vanilla JS |
|---|---|---|---|---|
| **Build-Artefakt** | ✅ `dist/` mit wenigen Chunks, Content-Hash, klar strukturiert | ⚠️ Static adapter erzeugt viele HTML-Dateien + Assets — Routing-Komplexität steigt | ⚠️ Pro Route eine HTML-Datei + JS-Islands — für SPA-Verhalten unnatürlich | ✅ Kein Build nötig — oder simples Bundling. Maximale Kontrolle |
| **Deployment** | ✅ `rsync dist/ nas:/volume1/docker/rotary-archiv/frontend_b/dist/` — trivial | ⚠️ Funktioniert, aber Static-Adapter-Konfiguration muss korrekt sein (trailing slashes, 404-Seite) | ⚠️ Funktioniert für statische Sites, aber SPA-Routing erfordert Anpassungen | ✅ Simpelstmöglich — direkt schieben |
| **Breaking Changes in 3 Jahren** | ✅ Vue 3 ist seit 2020 stabil. Vue 2→3 war die große Migration, die abgeschlossen ist. Kleine APIs brechen nie ohne langen Deprecation-Cycle | ⚠️ **Svelte 4→5 war eine Breaking Change mit neuer Reaktivitäts-API (Runes).** Das Muster ist bekannt. Svelte ist innovationsgetrieben — schön, aber riskant für Langzeitbetrieb | ❌ Astro ist jung (v1: 2022, v2: 2023, v3: 2023, v4: 2024). Schnelle Major-Releases signalisieren noch laufende Reifung. Island-Architektur für ein SPA ist ein Mismatch | ✅ Web Components und Custom Elements sind W3C-Standard. Browser-nativ. Kein Framework-Risiko |
| **Wiedereinstieg nach 6 Monaten** | ✅ Options API oder Composition API — beides gut dokumentiert. Großes Ökosystem bedeutet viele aktuelle Tutorials, Stack Overflow-Antworten, Claude-Kontext | ⚠️ Svelte 5 / Runes sind neu — nach 6 Monaten Pause muss man die neue API lernen, falls Upgrade erfolgt ist | ⚠️ Astro-Konzepte (Islands, Hydration-Strategien) sind ungewöhnlich und erfordern Einarbeitung | ❌ Ohne Framework-Struktur wächst Vanilla-Code schnell in schwer navigierbaren Spagetti-Code. Wiedereinstieg hängt stark von eigener Disziplin ab |
| **Betrieb-Gesamtnote** | ✅ **Sehr gut** | ⚠️ **Mittel** | ⚠️ **Mittel** | ✅ Gut für Einfaches / ❌ Schlecht für Komplexes |

---

### Kriterium 2: ENTWICKLUNG PHASE 1 (Gewicht: mittel)

| | Option A — Vue 3 + Vite | Option B — SvelteKit | Option C — Astro + Islands | Option D — Vanilla JS |
|---|---|---|---|---|
| **Geschwindigkeit zum Demonstrator** | ✅ `npm create vue@latest` → sofortiger Dev-Server → erste Komponente in 10 Minuten. Composition API ist kompakt und leicht zu erklären | ✅ Svelte-Syntax ist minimal, sehr schnell für kleine Komponenten | ⚠️ Astro-Konzepte (`.astro` Dateien, Island-Direktiven) erfordern initiale Einarbeitung | ⚠️ Für 3–4 Komponenten schnell, aber ohne Routing/State-Abstraktion wächst der Aufwand exponentiell |
| **Boilerplate-Overhead** | ✅ Minimal. `script setup` + `template` + `style scoped` = alles in einer Datei | ✅ Noch weniger Boilerplate als Vue — Svelte gewinnt hier klar | ⚠️ Mehr Konfiguration: Frontmatter, Island-Wrapper, Adapter-Setup | ✅ Null Boilerplate — aber auch null Struktur |
| **Claude Sonnet 4.6 in Cursor** | ✅ **Maximal zuverlässig** (→ Detailbewertung am Ende) | ✅ Gut, leicht schlechter als Vue | ⚠️ Mittel — Astro-spezifische Syntax wird seltener im Training verwendet | ⚠️ Gut für Snippets, schlecht für Architektur-Entscheidungen |
| **Phase-1-Gesamtnote** | ✅ **Sehr gut** | ✅ **Gut** | ⚠️ **Mittel** | ⚠️ **Mittel** |

---

### Kriterium 3: DESIGN-SYSTEM-KOMPATIBILITÄT (Gewicht: mittel)

Das Designsystem aus `T5-designsystem-v1.1.md` basiert auf:
- CSS Custom Properties (`:root { --color-bg, --color-epoch-primary, … }`)
- Epochen-Override per Klasse (`.epoch-30er`, `.epoch-90er`)
- Google Fonts (Lora, Inter) über `@import`
- Keine Component-Library — reines CSS-Fundament

| | Option A — Vue 3 + Vite | Option B — SvelteKit | Option C — Astro + Islands | Option D — Vanilla JS |
|---|---|---|---|---|
| **CSS Custom Properties** | ✅ `<style scoped>` konsumiert globale Custom Properties problemlos. Epochen-Klassen per `:class` binding | ✅ Identisch gut — Svelte-Styles nutzen globale Tokens | ✅ Funktioniert, aber pro Island-Kontext etwas unübersichtlicher | ✅ Native CSS — keinerlei Overhead |
| **Scoped Styles** | ✅ `<style scoped>` ist erste Klasse — kein Setup erforderlich | ✅ Svelte-Styles sind standardmäßig scoped | ⚠️ Scoped Styles in Islands abhängig vom verwendeten Framework (Vue/Svelte Island) | ❌ Kein natives Scoping — Shadow DOM für Web Components ist aufwändig und hat Cascading-Komplikationen mit globalen Custom Properties |
| **Leaflet (K12 — MapView)** | ✅ `onMounted(() => { L.map(...) })` — Standardmuster, hunderte Tutorials | ✅ `onMount(() => { L.map(...) })` — identisch einfach | ⚠️ Leaflet als Island mit `client:only` — funktioniert, aber ungewohnt | ⚠️ Funktioniert, aber manuelles DOM-Lifecycle-Management erforderlich |
| **D3/vis.js Netzwerk-Graph (K04, K07)** | ✅ `onMounted` + `ref` für Container — gut etabliertes Muster | ✅ Identisch gut | ⚠️ Island-Kontext erschwert Graph-internen State | ⚠️ Funktioniert, aber State-Management komplex |
| **Design-Gesamtnote** | ✅ **Sehr gut** | ✅ **Sehr gut** | ⚠️ **Mittel** | ⚠️ **Mittel** |

---

### Kriterium 4: API-INTEGRATION (Gewicht: mittel)

Backend B liefert REST-Endpoints (`/api/v1/…`), Stub-Responses (`{ stub: true }`),  
JWT-Auth aus localStorage, Mock-Daten für Phase 1.

| | Option A — Vue 3 + Vite | Option B — SvelteKit | Option C — Astro + Islands | Option D — Vanilla JS |
|---|---|---|---|---|
| **REST-Calls strukturieren** | ✅ `composables/usePersons.js` — klare Konvention, wiederverwendbar. Pinia für globalen Auth-State | ✅ Stores + `load`-Funktionen — elegant, aber SvelteKit-spezifisch | ⚠️ API-Calls in `.astro`-Frontmatter (SSR) oder in Islands (client-side) — für ein SPA ist die client-side-Variante nötig | ⚠️ Manuelle Fetch-Wrapper ohne Konvention — jede Person löst das anders |
| **Skeleton-States / Ladezustände** | ✅ `v-if` / `v-else` auf `isLoading`-State — idiomatisch, sofort verständlich | ✅ Reactive stores — minimal und elegant | ⚠️ Island-State ist lokal — globale Ladezustände über Island-Grenzen hinweg sind komplex | ❌ Kein einheitliches Muster — entsteht organisch und inkonsistent |
| **Mock-Daten Phase 1** | ✅ JSON-Dateien in `src/mocks/` + einfache Composable-Flag `USE_MOCK=true` | ✅ Identisch einfach | ⚠️ Mock-Daten in Frontmatter einfach, in Islands manuell | ✅ Einfach — aber keine Abstraktion zur späteren Umstellung |
| **JWT-Auth** | ✅ Pinia-Store für Auth-State. `axios`-Interceptor oder einfache `fetch`-Wrapper mit Bearer-Token | ✅ Svelte-Store für Auth — minimal | ⚠️ Island-übergreifender Auth-State erfordert globales Store-Pattern | ⚠️ Manuell — fehleranfällig ohne Konvention |
| **API-Gesamtnote** | ✅ **Sehr gut** | ✅ **Gut** | ⚠️ **Mittel** | ⚠️ **Mittel–Schlecht** |

---

### Kriterium 5: LANGLEBIGKEIT (Gewicht: hoch)

| | Option A — Vue 3 + Vite | Option B — SvelteKit | Option C — Astro + Islands | Option D — Vanilla JS |
|---|---|---|---|---|
| **5-Jahres-Stabilität** | ✅ Vue wird von einem professionellen Core-Team (Evan You) mit klarer RFC-Kultur entwickelt. Breaking Changes folgen einem langen Deprecation-Cycle. Vue 3 ist die aktuelle stabile Basis | ⚠️ Svelte 5 hat gerade eine fundamentale API-Änderung (Runes) eingeführt. Das zeigt Innovationsbereitschaft — aber auch Bereitschaft zur Breaking Change. Für ein 5-Jahres-Projekt ist das ein Risiko | ⚠️ Astro ist jung und entwickelt sich schnell. Positiv: breite Adoption, gute Finanzierung. Negativ: für ein SPA ist es nicht der primäre Use-Case | ✅ Browser-APIs sind rückwärtskompatibel. Kein Veralten möglich |
| **Community & Ökosystem** | ✅ Drittgrößte JS-Framework-Community. Riesiges Ökosystem (Vue Router, Pinia, VueUse). Millionen Projekte im Einsatz | ✅ Wachsende Community, beliebt bei Entwicklern. Kleiner als Vue/React | ⚠️ Wachsende Community, aber spezifischer Use-Case (Content-Sites) | ✅ Keine Community-Abhängigkeit — aber auch keine Hilfe |
| **Bekannte Risiken** | ✅ Gering. Vue 2 EOL war kommuniziert und lang angekündigt. Vue 3 hat keine strukturellen Schulden | ⚠️ **Svelte 4→5 Breaking Change ist dokumentierter Präzedenzfall.** Runes erfordern Rewrite-Aufwand in bestehenden Codebasen | ❌ Astro v1→v4 in zwei Jahren = sehr schnelles Versioning. Integration zwischen Host-Framework und Islands erhöht Komplexität | ✅ Null Framework-Risiko, aber organisch gewachsener Code kann nach 3 Jahren nicht mehr wartbar sein |
| **Langlebigkeits-Gesamtnote** | ✅ **Sehr gut** | ⚠️ **Mittel** | ⚠️ **Mittel–Schlecht** | ✅/❌ **Gut technisch, schlecht strukturell** |

---

## Gesamtbewertung

| Kriterium | Gewicht | Vue 3 + Vite | SvelteKit | Astro + Islands | Vanilla JS |
|---|---|---|---|---|---|
| Betrieb | Hoch | ✅ | ⚠️ | ⚠️ | ⚠️ |
| Entwicklung Phase 1 | Mittel | ✅ | ✅ | ⚠️ | ⚠️ |
| Design-System-Kompatibilität | Mittel | ✅ | ✅ | ⚠️ | ⚠️ |
| API-Integration | Mittel | ✅ | ✅ | ⚠️ | ❌ |
| Langlebigkeit | Hoch | ✅ | ⚠️ | ⚠️ | ⚠️ |
| **Gesamtbewertung** | | **✅ Empfohlen** | **⚠️ Reserveoption** | **❌ Nicht empfohlen** | **❌ Nicht empfohlen** |

---

## Entscheidung: Option A — Vue 3 + Vite

**Vue 3 + Vite ist die richtige Wahl für das RotaryArchiv.**

Das Deployment-Modell ist trivial: `vite build` erzeugt ein `dist/`-Verzeichnis mit wenigen  
Hash-benannten Dateien, das direkt per `rsync` in das Nginx-Volume geschoben wird — genau  
das, was `T3-docker-compose.md` mit dem Volume-Mount `./frontend_b/dist:/var/www/rotary-frontend`  
erwartet. Kein Server-Prozess, kein Build-Container auf dem NAS, keine Überraschungen.

Die Komponenten-Architektur aus `T5-komponenten-v1.3.md` — 13 Komponenten, sauber getrennte  
Verantwortungsbereiche, Varianten statt Duplikate — passt perfekt zu Vue SFCs (Single File  
Components): eine Datei pro Komponente, `<template>`, `<script setup>`, `<style scoped>`.  
Das CSS Custom Property-System aus `T5-designsystem-v1.1.md` (`:root`-Tokens, `.epoch-30er`,  
`.epoch-90er` Class-Overrides) wird mit `:class` Bindings nativ konsumiert.

Für Phase 1 (Demonstrator in wenigen Monaten) bietet Vue mit Composition API und Vite  
den schnellsten Weg von null zu einem funktionierenden, überzeugenden Interface.  
Mock-Daten für die 3–4 Personen aus Phase 1 sind mit einem `USE_MOCK`-Flag in einem  
Composable (`useApi.js`) in einer Stunde implementiert.

Das Breaking-Change-Risiko ist bei Vue 3 am niedrigsten aller vier Optionen: Die  
Vue 2→3 Migration war die einmalige große Umstellung, sie ist abgeschlossen.  
Vue 3 hat keine strukturellen Schulden und folgt einem langen, angekündigten  
Deprecation-Cycle. Wer in 3 Jahren eine Pause macht und zurückkommt, findet  
eine vertraute Codebase.

---

## Konkrete Projekt-Konfiguration

```bash
npm create vue@latest rotary-frontend
# ✅ TypeScript: Nein (vereinfacht Einstieg für Gelegenheitsentwickler)
# ✅ Vue Router: Ja
# ✅ Pinia: Ja (Auth-State, API-State)
# ✅ ESLint: Ja
# ✅ Vitest: Optional (Phase 2)
```

### Empfohlene Verzeichnisstruktur

```
rotary-frontend/
├── src/
│   ├── assets/
│   │   └── main.css          ← Design-Token-Import (:root { --color-bg … })
│   ├── components/           ← K01–K13 aus T5-komponenten-v1.3.md
│   │   ├── AppShell.vue
│   │   ├── HeroBlock.vue
│   │   ├── EntityCard.vue
│   │   ├── PersonProfile.vue
│   │   ├── DocumentViewer.vue
│   │   ├── TimelineBlock.vue
│   │   ├── NetworkGraph.vue   ← D3/vis.js via onMounted
│   │   ├── SearchBar.vue
│   │   ├── EpochFilter.vue
│   │   ├── StoryCard.vue
│   │   ├── StoryDetail.vue
│   │   ├── MapView.vue        ← Leaflet via onMounted
│   │   └── ConsentProgress.vue
│   ├── composables/
│   │   ├── useApi.js          ← Zentrale Fetch-Abstraktion + USE_MOCK-Flag
│   │   ├── usePersons.js
│   │   ├── useDocuments.js
│   │   └── useAuth.js         ← JWT aus localStorage
│   ├── mocks/                 ← Phase-1-Mockdaten
│   │   ├── persons.json
│   │   ├── documents.json
│   │   └── featured.json
│   ├── router/
│   │   └── index.js           ← 12 Routes für V01–V12
│   ├── stores/
│   │   └── auth.js            ← Pinia — globaler Auth-State (K01 AppShell)
│   └── views/                 ← V01–V12
│       ├── V01Home.vue
│       ├── V02Epoch.vue
│       ├── V03Person.vue
│       └── …
├── vite.config.js
└── package.json
```

### Deployment-Workflow

```bash
# Lokal bauen
npm run build
# → erzeugt frontend_b/dist/ mit index.html + assets/

# Auf NAS schieben
rsync -avz dist/ user@nas:/volume1/docker/rotary-archiv/frontend_b/dist/

# Nginx neu laden (kein Restart nötig — statische Dateien)
docker exec rotary_nginx nginx -s reload
```

### Leaflet & D3 — Integration

```js
// MapView.vue
import { onMounted, ref } from 'vue'
import L from 'leaflet'

const mapContainer = ref(null)

onMounted(() => {
  const map = L.map(mapContainer.value).setView([51.05, 13.74], 13)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/voyager/{z}/{x}/{y}{r}.png').addTo(map)
  // Marker in Epochenfarbe via CSS Custom Properties
})
```

```js
// NetworkGraph.vue
import { onMounted, ref } from 'vue'
import * as d3 from 'd3'

const svgContainer = ref(null)

onMounted(async () => {
  const data = await fetch('/api/v1/persons/:slug/network').then(r => r.json())
  // D3-Force-Graph mit Epochenfarbe aus getComputedStyle(document.body)
  //   .getPropertyValue('--color-epoch-primary')
})
```

### Mock-Daten Phase 1

```js
// composables/useApi.js
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

export async function fetchPerson(slug) {
  if (USE_MOCK) {
    const data = await import('../mocks/persons.json')
    return data.default.find(p => p.slug === slug)
  }
  return fetch(`/api/v1/persons/${slug}`).then(r => r.json())
}
```

`.env.development`:
```
VITE_USE_MOCK=true
```

---

## Zusatzfrage: Claude Sonnet 4.6 als Coding-Partner in Cursor

**Vue 3 generiert den zuverlässigsten, sofort lauffähigen Code.**

Die Begründung ist datengetrieben, nicht intuitiv:

1. **Trainingskorpus-Dominanz:** Vue 3 ist mit Abstand am häufigsten in öffentlichen GitHub-Repositories  
   vertreten — zusammen mit React und Angular. Claude wurde auf diesem Corpus trainiert.  
   Die Wahrscheinlichkeit, dass generierter Code idiomatisch und sofort compilierbar ist,  
   korreliert direkt mit der Corpus-Häufigkeit.

2. **Stabile API-Oberfläche:** `script setup`, `ref`, `computed`, `onMounted`, `defineProps` —  
   diese APIs haben sich seit Vue 3.2 (2021) nicht verändert. Claude generiert diese Muster  
   konsistent korrekt, ohne Verwirrung durch API-Varianten.

3. **Svelte 5 / Runes-Problem:** Svelte 5 mit Runes ist eine neue API, die erst seit Ende 2024  
   im Trainingskorpus präsent ist. Claude generiert häufig Svelte 4-Code wenn Svelte 5  
   verlangt wird — oder mixt beide APIs. Das erzeugt stille Fehler, die schwer zu debuggen sind.

4. **Astro-spezifische Syntax:** `.astro`-Frontmatter-Syntax, `client:load`-Direktiven und  
   die Island-Architektur sind nischenspezifisch. Claude kennt sie, generiert aber seltener  
   sofort-lauffähigen Code für komplexere Island-Interaktionen.

5. **Vanilla JS — strukturelle Grenze:** Für einzelne Funktionen ist Claude mit Vanilla JS  
   exzellent. Für eine Komponentenarchitektur mit 13 Komponenten und Routing  
   fehlt die generierbare Konvention — jeder Prompt braucht mehr Kontext.

**Praktische Konsequenz für T6:** Prompts in Cursor können direkt auf die SFC-Struktur  
referenzieren: *„Erstelle eine Vue 3 Composition API Komponente `EntityCard.vue` mit Props  
`slug`, `display_name`, `epoch`, `is_public` gemäß `T5-komponenten-v1.3.md`"* — Claude  
generiert sofort lauffähigen, idiomatischen Code.

---

## Risikominimierung — Offene Punkte für T6

| Risiko | Maßnahme |
|---|---|
| Leaflet + Vue 3 SSR-Konflikt | Kein SSR (reines SPA) — kein Problem. `onMounted` ist ausreichend |
| D3 v6→v7 API-Änderungen | Version in `package.json` fixieren: `"d3": "7.x"` |
| Vue Router Hash-Mode vs. History-Mode | **History-Mode** — Nginx `try_files` ist bereits konfiguriert |
| TypeScript optional | Nein für Phase 1. Optional für Phase 2 nachrüsten — Vue 3 unterstützt beides |
| Google Fonts Datenschutz | Fonts lokal hosten: `npm install @fontsource/lora @fontsource/inter` |

---

*Input für: T6-coding-setup.md*
