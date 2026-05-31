# T6-mock-daten.md — Mock-Daten für Phase 1

> **Version:** 1.0 — 2026-05-03
> **Thread:** T6 Frontend-Entwickler
> **Phase:** Planning Phase
> **Input aus:** T2-migrations-plan.md, T5-komponenten-v1.3.md

---

## 1. Übersicht

Phase 1 nutzt **Mock-Daten** statt echter API — um den Demonstrator ohne laufendes Backend B zu zeigen.
Das Composable `useApi.js` schaltet zwischen Mock und echtem Backend um.

```
src/mocks/
├── persons.json       ← 3 echte Personen aus Triplestore (30er, mit Portrait)
├── documents.json    ← 2 Protokolle mit BBox-Daten
├── featured.json     ← Hero-Block Zitate
└── stories.json      ← (Phase 2)
```

**Hinweis:** Die echten Triplestore-Daten liegen in `data/triplestore.ttl`. Wir extrahieren die Personen direkt daraus (kein separater Export nötig).

---

## 2. Personen-Mockdaten (persons.json)

### Auswahl für Phase 1

3 echte Personen aus dem Triplestore (alle 30er, alle mit Portrait):

| Person | Begründung |
|---|---|
| Victor Klemperer von Klemenau | Bekanntester Name, vollständige Wikidata-Daten |
| Fritz Busch | International bekannter Musikdirektor |
| Heinrich Arnhold | Lokal prominenter Industrieller |

*Alle Daten stammen aus `data/triplestore.ttl` — Wikidata-URLs, Geburts-/Sterbedaten, Portraits.*

### Datenstruktur (exakt nach T2-migrations-plan.md)

```json
[
  {
    "id": 1,
    "slug": "max-mueller-1887",
    "display_name": "Max Müller",
    "born_year": 1887,
    "died_year": 1951,
    "epoch": "30er",
    "wikidata_id": "Q123456",
    "is_public": true,
    "notes": "Vorsitzender 1931–1933",
    "portrait_url": "/portraits/max-mueller-1887.jpg",
    "membership": {
      "joined": "1929-05-15",
      "joined_document_id": 101,
      "joined_quote": "Herr Müller wird einstimmig als Mitglied aufgenommen. Der Präsident begrüßt ihn herzlich.",
      "left": "1934-03-09",
      "left_document_id": 107,
      "left_quote": "Herr Müller tritt aus persönlichen Gründen aus.",
      "role": "Präsident"
    },
    "timeline": [
      { "date": "1933-03-14", "document_id": 42, "snippet": "...eröffnet die Sitzung...", "role": "Vorsitzender" },
      { "date": "1933-02-28", "document_id": 41, "snippet": "...begrüßt Herrn Müller...", "role": "Vorsitzender" }
    ],
    "attendance": {
      "total": 61,
      "present": 47,
      "period": "1927–1934"
    },
    "network": {
      "nodes": [
        { "id": 1, "slug": "max-mueller-1887", "display_name": "Max Müller", "epoch": "30er" },
        { "id": 2, "slug": "ernst-weber-1892", "display_name": "Ernst Weber", "epoch": "30er" },
        { "id": 3, "slug": "karl-bauer-1885", "display_name": "Karl Bauer", "epoch": "30er" }
      ],
      "edges": [
        { "source": 1, "target": 2, "weight": 5 },
        { "source": 1, "target": 3, "weight": 12 }
      ]
    }
  },
  {
    "id": 2,
    "slug": "ernst-weber-1892",
    "display_name": "Ernst Weber",
    "born_year": 1892,
    "died_year": 1962,
    "epoch": "30er",
    "wikidata_id": "Q234567",
    "is_public": true,
    "notes": "Sekretär 1929–1936",
    "portrait_url": null,
    "membership": {
      "joined": "1929-01-10",
      "joined_document_id": 38,
      "joined_quote": "Herr Ernst Weber wird als Schriftführer aufgenommen.",
      "left": null,
      "left_document_id": null,
      "left_quote": null,
      "role": "Sekretär"
    },
    "timeline": [
      { "date": "1932-11-15", "document_id": 89, "snippet": "...protokolliert Herr Weber...", "role": "Sekretär" }
    ],
    "attendance": {
      "total": 52,
      "present": 49,
      "period": "1929–1936"
    },
    "network": {
      "nodes": [],
      "edges": []
    }
  },
  {
    "id": 3,
    "slug": "wolfgang-hartmann-1952",
    "display_name": "Wolfgang Hartmann",
    "born_year": 1952,
    "died_year": null,
    "epoch": "90er",
    "wikidata_id": null,
    "is_public": false,
    "notes": null,
    "portrait_url": null,
    "stub": true,
    "consent_progress": {
      "total_persons": 8,
      "identified": 2,
      "consented": 0,
      "score": 0.25,
      "ready_for_release": false
    }
  }
]
```

### Stub-Response (nicht-öffentlich)

Wenn `is_public = false` und kein Auth-Token:

```json
{
  "stub": true,
  "display_name": "Wolfgang Hartmann",
  "epoch": "90er",
  "born_year": 1952,
  "consent_progress": {
    "total_persons": 8,
    "identified": 2,
    "consented": 0,
    "score": 0.25,
    "ready_for_release": false
  }
}
```

---

## 3. Dokument-Mockdaten (documents.json)

### Datenstruktur (exakt nach T2-migrations-plan.md)

```json
[
  {
    "id": 101,
    "title": "Sitzungsprotokoll vom 15. Mai 1929",
    "date": "1929-05-15",
    "epoch": "30er",
    "is_public": true,
    "type": "protocol",
    "pages": [
      {
        "page_number": 1,
        "image_url": "/scans/1929-05-15-p1.jpg",
        "ocr_text": "Anwesend: Max Müller, Ernst Weber, Karl Bauer, Heinrich Sch..."
      }
    ],
    "bbox_data": [
      {
        "id": "bbox-101-001",
        "page": 1,
        "x1": 120,
        "y1": 340,
        "x2": 480,
        "y2": 380,
        "text": "Herr Müller wird einstimmig als Mitglied aufgenommen.",
        "confidence": 0.94,
        "entity_uri": "rotary:Mention_101_001",
        "role": "mention"
      },
      {
        "id": "bbox-101-002",
        "page": 1,
        "x1": 200,
        "y1": 420,
        "x2": 460,
        "y2": 460,
        "text": null,
        "confidence": 0.12,
        "entity_uri": null,
        "role": "unreadable"
      }
    ],
    "transcription": "Herr Müller wird einstimmig als Mitglied aufgenommen. Der Präsident begrüßte ihn herzlich.",
    "context_snippet": "Herr Müller wird einstimmig als Mitglied aufgenommen."
  },
  {
    "id": 107,
    "title": "Sitzungsprotokoll vom 9. März 1934",
    "date": "1934-03-09",
    "epoch": "30er",
    "is_public": true,
    "type": "protocol",
    "pages": [
      {
        "page_number": 1,
        "image_url": "/scans/1934-03-09-p1.jpg",
        "ocr_text": "Protokoll der 47. Sitzung des Rotary Club Dresden..."
      }
    ],
    "bbox_data": [
      {
        "id": "bbox-107-001",
        "page": 1,
        "x1": 80,
        "y1": 200,
        "x2": 520,
        "y2": 260,
        "text": "Herr Müller tritt aus persönlichen Gründen aus.",
        "confidence": 0.88,
        "entity_uri": "rotary:Mention_107_001",
        "role": "mention"
      }
    ],
    "transcription": "Herr Müller tritt aus persönlichen Gründen aus.",
    "context_snippet": "Herr Müller tritt aus persönlichen Gründen aus."
  }
]
```

### GapInline-Datenstruktur

Die `bbox_data` mit `confidence < 0.6` oder `text: null` werden im Frontend als GapInline gerendert:

```vue
<!-- GapInline.vue -->
<span
  class="gap-inline"
  :class="{ 'gap-submitted': isSubmitted }"
  @click="openContributionForm(bbox.id)"
>
  ░░░░░
</span>
```

---

## 4. Featured-Mockdaten (featured.json)

```json
{
  "date": "2026-05-03",
  "quote_text": "Der Vorsitzende eröffnet die Sitzung. Es fehlen sieben Mitglieder.",
  "quote_source": "Sitzungsprotokoll Nr. 47 vom 14. März 1933",
  "document_id": 42,
  "person_slug": "max-mueller-1887"
}
```

---

## 5. useApi Composable — Interface

### Kern-Interface

```js
// src/composables/useApi.js
import { ref } from 'vue'
import personsJson from '@/mocks/persons.json'
import documentsJson from '@/mocks/documents.json'
import featuredJson from '@/mocks/featured.json'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_BASE = '/api/v1'

// Helper für Stub-Handling
const toStub = (data) => ({ stub: true, ...data })

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  // ── Personen ──
  async function getPersons(params = {}) {
    loading.value = true
    try {
      if (USE_MOCK) {
        let data = [...personsJson]
        if (params.epoch) data = data.filter(p => p.epoch === params.epoch)
        if (params.q) data = data.filter(p => p.display_name.toLowerCase().includes(params.q.toLowerCase()))
        return data
      }
      const query = new URLSearchParams(params).toString()
      const res = await fetch(`${API_BASE}/persons?${query}`)
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getPerson(slug) {
    loading.value = true
    try {
      if (USE_MOCK) {
        const person = personsJson.find(p => p.slug === slug)
        if (!person) throw new Error('Person not found')
        // Stub-Response simulieren
        if (!person.is_public && !isAuthenticated()) return toStub(person)
        return person
      }
      const res = await fetch(`${API_BASE}/persons/${slug}`)
      if (res.status === 404) throw new Error('Person not found')
      const data = await res.json()
      if (data.stub) return data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // ── Dokumente ──
  async function getDocuments(params = {}) {
    loading.value = true
    try {
      if (USE_MOCK) {
        let data = [...documentsJson]
        if (params.epoch) data = data.filter(d => d.epoch === params.epoch)
        return data
      }
      const query = new URLSearchParams(params).toString()
      const res = await fetch(`${API_BASE}/documents?${query}`)
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getDocument(id) {
    loading.value = true
    try {
      if (USE_MOCK) {
        const doc = documentsJson.find(d => d.id === parseInt(id))
        if (!doc) throw new Error('Document not found')
        return doc
      }
      const res = await fetch(`${API_BASE}/documents/${id}`)
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // ── Featured ──
  async function getFeatured() {
    if (USE_MOCK) return featuredJson
    const res = await fetch(`${API_BASE}/featured`)
    return await res.json()
  }

  // ── Auth-Helper ──
  function isAuthenticated() {
    return !!localStorage.getItem('access_token')
  }

  return {
    loading,
    error,
    getPersons,
    getPerson,
    getDocuments,
    getDocument,
    getFeatured
  }
}
```

### Austauschbarkeit (Mock → Echt)

Der Wechsel von Mock zu echtem Backend erfordert **keine Änderungen an Komponenten**:

1. `.env.development`: `VITE_USE_MOCK=true`
2. `.env.production`: `VITE_USE_MOCK=false` (oder entfernen)
3. API-Base-URL in Vite konfigurieren

Komponenten rufen ausschließlich `useApi()`-Funktionen auf — keine direkten `fetch()`-Calls.

---

## 6. Konkrete Personen (aus Triplestore)

*Aus `data/triplestore.ttl` — Stand Mai 2026. Alle 7 Personen haben Portrait.*

| Slug | Name | Geburt | Tod | Epoche | Portrait |
|---|---|---|---|---|---|
| `victor-klemperer-von-klemenau` | Victor Klemperer von Klemenau | 1876-06-20 | 1943-03-13 | 30er | ✅ Wikimedia Commons |
| `fritz-busch` | Fritz Busch | — | 1951-09-14 | 30er | ✅ Wikimedia Commons |
| `hugo-grille` | Hugo Grille | 1870-08-14 | 1962-06-12 | 30er | ✅ Wikimedia Commons |
| `gustav-brandes` | Gustav Brandes | 1862-05-02 | 1941-07-17 | 30er | ✅ Wikimedia Commons |
| `bernhard-blueher` | Bernhard Blüher | 1864-04-11 | 1938-07-12 | 30er | ✅ Wikimedia Commons |
| `heinrich-arnhold` | Heinrich Arnhold | 1885-07-22 | 1935-10-10 | 30er | ✅ Wikimedia Commons |
| `karl-von-frenckell` | Karl von Frenckell | 1880-04-11 | 1952 | 30er | ✅ Wikimedia Commons |

### Empfohlene Auswahl für Phase-1-Demonstrator

| # | Person | Begründung |
|---|---|---|
| 1 | **Victor Klemperer von Klemenau** | Bekanntester Name, vollständige Daten |
| 2 | **Fritz Busch** | Musikdirektor, international bekannt |
| 3 | **Heinrich Arnhold** | Lokal prominent, Industrieller |

---

## 7. Echte Personen-Daten (persons.json)

Die folgenden 3 Personen werden für Phase 1 verwendet:

```json
[
  {
    "id": 1,
    "slug": "victor-klemperer-von-klemenau",
    "display_name": "Victor Klemperer von Klemenau",
    "born_year": 1876,
    "died_year": 1943,
    "epoch": "30er",
    "wikidata_id": "Q16857741",
    "is_public": true,
    "notes": "Präsident des Rotary Club Dresden",
    "portrait_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Robert_Sterl_-_Victor_von_Klemperer_1922.jpg?width=200",
    "membership": {
      "joined": "1927-00-00",
      "joined_document_id": null,
      "joined_quote": "Victor Klemperer von Klemenau wurde als Mitglied aufgenommen.",
      "left": null,
      "left_document_id": null,
      "left_quote": null,
      "role": "Präsident"
    },
    "timeline": [],
    "network": { "nodes": [], "edges": [] }
  },
  {
    "id": 2,
    "slug": "fritz-busch",
    "display_name": "Fritz Busch",
    "born_year": null,
    "died_year": 1951,
    "epoch": "30er",
    "wikidata_id": "Q213569",
    "is_public": true,
    "notes": "Generalmusikdirektor der Semperoper",
    "portrait_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Fritz_busch_image1.jpg?width=200",
    "membership": {
      "joined": null,
      "joined_document_id": null,
      "joined_quote": null,
      "left": null,
      "left_document_id": null,
      "left_quote": null,
      "role": null
    },
    "timeline": [],
    "network": { "nodes": [], "edges": [] }
  },
  {
    "id": 3,
    "slug": "heinrich-arnhold",
    "display_name": "Heinrich Arnhold",
    "born_year": 1885,
    "died_year": 1935,
    "epoch": "30er",
    "wikidata_id": "Q1596590",
    "is_public": true,
    "notes": "Kaufmann und Industrieller",
    "portrait_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Heinrich_Gustav_Arnhold.jpg?width=200",
    "membership": {
      "joined": null,
      "joined_document_id": null,
      "joined_quote": null,
      "left": null,
      "left_document_id": null,
      "left_quote": null,
      "role": null
    },
    "timeline": [],
    "network": { "nodes": [], "edges": [] }
  }
]
```

---

## 8. Offene Punkte

| Frage | Status |
|---|---|
| Konkrete Personennamen aus Triplestore | ✅ Erledigt — 7 Personen mit Portrait |
| Scan-Bilder für Mock-Dokumente | 🟡 Offen — Platzhalter-Pfade ok |
| BBox-Koordinaten aus OCR-Export | 🟡 Offen — manuell oder Export |

---

*Weiter zu: T6-build-reihenfolge.md*
