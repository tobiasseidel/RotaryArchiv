# T6-projektstruktur.md — Vue 3 + Vite Projektstruktur

> **Version:** 1.0 — 2026-05-03
> **Thread:** T6 Frontend-Entwickler
> **Phase:** Planning Phase
> **Input aus:** T5-framework-entscheidung.md, T5-designsystem-v1.1.md, T5-komponenten-v1.3.md
>
> **⚠️ Aktualisiert durch T9-dev-strategie.md:** Dieses Dokument referenziert
> T3-nginx-config (Split-Architektur) als Basis für den History-Mode.
> Die Projektstruktur selbst ist von T9 nicht betroffen — Frontend bleibt
> gleich, nur das API-Backend ist aktuell ein Single-Service.
> Siehe [T9-dev-strategie.md](T9-dev-strategie.md).

---

## 1. Verzeichnisstruktur

```
rotary-frontend/
├── public/
│   └── portraits/              ← Portrait-Bilder, slug-basiert benannt
├── src/
│   ├── assets/
│   │   ├── main.css            ← Design-Tokens (:root), Epochen-Klassen
│   │   └── fonts/              ← Lora + Inter (WOFF2)
│   ├── components/
│   │   ├── AppShell.vue        ← K01
│   │   ├── HeroBlock.vue       ← K02
│   │   ├── EntityCard.vue      ← K03
│   │   ├── PersonProfile.vue   ← K04
│   │   ├── DocumentDualView.vue ← K05
│   │   ├── TimelineBlock.vue   ← K06
│   │   ├── NetworkGraph.vue    ← K07
│   │   ├── SearchBar.vue       ← K08
│   │   ├── ContributionForm.vue ← K09
│   │   ├── HistoricalContextBox.vue ← K10
│   │   ├── StoryTeaser.vue     ← K11
│   │   ├── MapView.vue         ← K12
│   │   └── ConsentProgress.vue ← K13
│   ├── composables/
│   │   ├── useApi.js           ← Zentrale API-Abstraktion + Mock-Modus
│   │   ├── usePersons.js       ← Personenbezogene API-Calls
│   │   ├── useDocuments.js     ← Dokumentbezogene API-Calls
│   │   ├── useSearch.js        ← Suchfunktion
│   │   └── useAuth.js          ← JWT-Auth-State
│   ├── mocks/
│   │   ├── persons.json        ← Phase-1-Mockdaten
│   │   ├── documents.json
│   │   ├── featured.json
│   │   └── stories.json
│   ├── router/
│   │   └── index.js            ← Vue Router (12 Routen)
│   ├── stores/
│   │   ├── auth.js             ← Pinia: JWT, User-Rolle
│   │   └── epoch.js            ← Pinia: Aktive Epoche (30er/90er)
│   └── views/
│       ├── V01Home.vue         ← Startseite
│       ├── V02Epochs.vue       ← Epochen-Übersicht
│       ├── V03Person.vue       ← Personenprofil
│       ├── V04Document.vue     ← Dokumentansicht
│       ├── V05Search.vue       ← Suchergebnisse
│       ├── V06Map.vue          ← Kartenansicht
│       ├── V07Network.vue      ← Netzwerk-Graph
│       ├── V08StoryDetail.vue  ← Story-Detail
│       ├── V09StorySubmit.vue  ← Story einreichen
│       ├── V10CorrectionSubmit.vue ← Korrektur einreichen
│       ├── V11Profile.vue      ← Nutzerprofil
│       └── V12About.vue        ← Über das Projekt
├── index.html
├── vite.config.js
├── package.json
└── .env                        ← VITE_USE_MOCK=true für Phase 1
```

---

## 2. Komponenten-Mapping (T5 → .vue)

| T5-Komponente | Vue-Komponente | View(s) |
|---|---|---|
| K01 AppShell | `AppShell.vue` | Alle 12 |
| K02 HeroBlock | `HeroBlock.vue` | V01 |
| K03 EntityCard | `EntityCard.vue` | V01, V02, V03, V05 |
| K04 PersonProfile | `PersonProfile.vue` | V03 |
| ↳ MembershipBlock | Innerhalb `PersonProfile.vue` | V03 |
| K05 DocumentDualView | `DocumentDualView.vue` | V04 |
| ↳ GapInline | `GapInline.vue` (eingebettet) | V04 |
| ↳ DocumentLinkPanel | `DocumentLinkPanel.vue` | V03, V04 |
| K06 TimelineView | `TimelineBlock.vue` | V02, V03 |
| ↳ AmtsStrahl | `AmtsStrahl.vue` | V02 |
| K07 NetworkGraph | `NetworkGraph.vue` | V03 (Mini), V07 (Voll) |
| K08 SearchBar/SearchResults | `SearchBar.vue` / `SearchResults.vue` | Alle / V05 |
| K09 ContributionForm | `ContributionForm.vue` | V09, V10, inline |
| K10 HistoricalContextBox | `HistoricalContextBox.vue` | V02, V03, V04, V12 |
| K11 StoryTeaser | `StoryTeaser.vue` | V01, V03, V08 |
| ↳ StorySourcePanel | `StorySourcePanel.vue` | V08 |
| K12 MapView | `MapView.vue` | V06 |
| K13 ConsentProgress | `ConsentProgress.vue` | V02, V04 |

---

## 3. CSS Custom Properties — Globale Integration

### main.css — Design-Tokens

```css
/* src/assets/main.css */

/* ── Basis-Tokens ── */
:root {
  --color-bg:             #F5F0E8;
  --color-surface:        #FDFAF5;
  --color-text-primary:   #1C1917;
  --color-text-secondary: #57534E;
  --color-border:         #D6CFC4;
  --color-stub:           #A09890;

  --color-success:        #3B6E4A;
  --color-warning:        #92640A;
  --color-error:         #8B2E2E;

  --font-serif:          'Lora', serif;
  --font-sans:           'Inter', sans-serif;

  --space-xs:   4px;
  --space-s:   8px;
  --space-m:  16px;
  --space-l:   24px;
  --space-xl:  40px;
  --space-2xl: 64px;
  --space-3xl: 96px;

  --grid-max:    1200px;
  --grid-gutter: 24px;

  --transition-fast: 150ms ease-in-out;
  --transition-page: 200ms ease-in;

  /* Epochen-Default (30er) */
  --color-epoch-primary: #2C4A3E;
  --color-epoch-accent:  #8B7355;
  --color-epoch-badge:   #E8E0D4;
}

/* ── Epochen-Klassen (per :class binding) ── */
.epoch-30er {
  --color-epoch-primary: #2C4A3E;
  --color-epoch-accent:  #8B7355;
  --color-epoch-badge:   #E8E0D4;
}

.epoch-90er {
  --color-epoch-primary: #1A3A5C;
  --color-epoch-accent:  #7A6E8A;
  --color-epoch-badge:   #E0E4EC;
}

/* Import Fonts (lokal, keine Google Fonts) */
@font-face {
  font-family: 'Lora';
  src: url('./fonts/lora.woff2') format('woff2');
  font-weight: 400 700;
  font-display: swap;
}

@font-face {
  font-family: 'Inter';
  src: url('./fonts/inter.woff2') format('woff2');
  font-weight: 400 600;
  font-display: swap;
}
```

### Konsum in Vue-Komponenten

**Variante A: App-level (App.vue)**

```vue
<!-- App.vue -->
<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

// Epochen-Klasse basierend auf Route oder Store
const epochClass = computed(() => {
  // Logik: aus Route-Parameter, Store oder Default
  return 'epoch-30er'
})
</script>

<template>
  <div :class="['app', epochClass]">
    <RouterView />
  </div>
</template>
```

**Variante B: Per Provide/Inject (empfohlen für saubere Trennung)**

```vue
<!-- App.vue -->
<script setup>
import { provide } from 'vue'
import { useEpochStore } from '@/stores/epoch'

const epochStore = useEpochStore()
provide('epoch', epochStore)
</script>

<template>
  <div :class="['app', epochStore.currentEpochClass]">
    <RouterView />
  </div>
</template>
```

```vue
<!-- EpochBadge.vue -->
<script setup>
import { inject } from 'vue'

const epoch = inject('epoch')
</script>

<template>
  <span :class="['epoch-badge', epoch.currentClass]">
    {{ epoch.label }}
  </span>
</template>
```

**Variante C: Pinia-Store (für komplexe View-Logik)**

```js
// stores/epoch.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useEpochStore = defineStore('epoch', () => {
  const current = ref('30er')

  const epochClass = computed(() => `epoch-${current.value}`)

  const setEpoch = (epoch) => { current.value = epoch }

  return { current, epochClass, setEpoch }
})
```

### Empfehlung

**Pinia-Store (Variante C)** für globale Epochen-Steuerung:
- Zentraler Ort für Epochen-Wechsel
- Einfache Integration mit Vue Router (Navigation-Guards)
- Leicht erweiterbar für Feature-Flags
- Keine Prop-Drilling durch viele Komponenten

---

## 4. Namenskonventionen

### Komponenten

| Typ | Schema | Beispiel |
|---|---|---|
| View-Komponenten | `V{nummer}{Name}.vue` | `V03Person.vue` |
| UI-Komponenten | `{Funktion}.vue` | `EntityCard.vue`, `EpochBadge.vue` |
| Sub-Komponenten | `{Parent}{Unterfunktion}.vue` | `PersonProfileMembership.vue` |

### Props und Events

- **Props:** camelCase, prägnant — `displayName`, `isPublic`, `epoch`
- **Events:** kebab-case — `@update:modelValue`, `@submit-form`
- **Slots:** deskriptiv — `<template #default>`, `<template #header>`

### Dateinamen

- **Vue-Komponenten:** PascalCase — `EntityCard.vue`
- **Composables:** camelCase, `use`-Präfix — `usePersons.js`
- **Stores:** camelCase, kein Präfix — `auth.js`
- **JSON-Mockdaten:** camelCase — `persons.json`

---

## 5. Routing — Phase 1 vs. Phase 2

### Phase 1 (Demonstrator)

```js
// router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/V01Home.vue') },
  { path: '/person/:slug', name: 'person', component: () => import('@/views/V03Person.vue') },
  { path: '/dokument/:id', name: 'document', component: () => import('@/views/V04Document.vue') },
  // Phase 2
  { path: '/epochen', name: 'epochs', component: () => import('@/views/V02Epochs.vue') },
  { path: '/suche', name: 'search', component: () => import('@/views/V05Search.vue') },
  // ... etc
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})
```

### Router-Mode

**History-Mode** — `createWebHistory()` (nicht Hash)
- Begründung: Nginx `try_files $uri $uri/ /index.html` ist bereits konfiguriert (T3-nginx-config.md)
- Funktioniert out-of-the-box ohne Hash-Routing

---

## 6. Dependencies (package.json)

```json
{
  "dependencies": {
    "vue": "^3.4",
    "vue-router": "^4.3",
    "pinia": "^2.1",
    "leaflet": "^1.9",
    "d3": "^7"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5",
    "vite": "^5",
    "@fontsource/lora": "^5",
    "@fontsource/inter": "^5"
  }
}
```

**Begründung:**
- `@fontsource/lora` + `@fontsource/inter` — lokale Fonts, kein Google Fonts CDN
- Leaflet + D3 via onMounted — keine speziellen Vue-Wrapper nötig
- Pinia — minimaler Overhead für globalen State

---

## 7. Offene Punkte

| Frage | Empfehlung | Status |
|---|---|---|
| Epoch-Store vs. Provide/Inject | Pinia (Variante C) | ✅ Empfohlen |
| TypeScript in Phase 1? | Nein — vereinfacht Einstieg | 🟡 Offen |
| Portrait-Pfad | `/public/portraits/{slug}.jpg` | 🟡 Offen |
| Porträt-Format | 3:4 Aspect Ratio | 🟡 Offen |

---

*Weiter zu: T6-mock-daten.md*
