# T9-dev-strategie.md — Lokale Entwicklung & Migrationspfad

> **Version:** 1.0 — 2026-06-02
> **Status:** Beschlossen
> **Kernaussage:** Single-Backend-Architektur für lokale Entwicklung ist kein Dead End,
> sondern ein sauberer Monolith-zu-Microservice-Pfad.

---

## 1. Aktuelle Architektur (Entwicklung)

```
┌─ Frontend (Vite Dev) ─┐      ┌── Backend (uvicorn :8000) ───────┐
│                        │      │                                  │
│  /api/v1/*             │─────>│  src/rotary_archiv/api/v1.py    │
│  /scans/*              │      │                                  │
│                        │      │  src/rotary_archiv/api/          │
│  (same-origin via      │      │  ├── ocr.py                      │
│   Vite-Proxy)          │      │  ├── review.py                   │
│                        │      │  ├── pages.py                    │
└────────────────────────┘      │  ├── quality.py                  │
                                │  └── settings.py                 │
                                │                                  │
                                │  + static/index.html (Admin-UI)  │
                                └──────────────────────────────────┘
```

- **Ein** FastAPI-Prozess, alle Routen auf Port 8000
- Vite-Proxy leitet `/api` und `/scans` an `localhost:8000` weiter
- Admin-Frontend (Vanilla JS) wird direkt von FastAPI unter `/static` geserved
- Kein CORS nötig — alles same-origin via Proxy

---

## 2. Geplante Ziel-Architektur (laut T3-docker-compose.md)

```
┌─ Nginx ────────────────────┐
│  /api/*    → backend_b     │
│  /admin/*  → backend_a     │
│  /scans/*  → direkt        │
│  /*         → Frontend SPA │
└────────────────────────────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│backend_a│ │backend_b │ │  fuseki  │
│ :8101   │ │ :8085    │ │ :3030    │
│ Admin   │ │ Public   │ │ SPARQL   │
│ OCR     │ │ API      │ │          │
└─────────┘ └─────────┘ └──────────┘
```

---

## 3. Migrationspfad

Die Umstellung ist jederzeit möglich und erfordert keine Änderungen am Frontend-Code.

### Schritt 1: `rotary_core` extrahieren (Vorbereitung)

- Existierende Shared-Logik (Datenbank-Models, Basis-Config) in `packages/rotary_core/` auslagern
- Kein Frontend betroffen

### Schritt 2: Backend B als separaten Service starten

- `src/rotary_archiv/api/v1.py` + Abhängigkeiten in `backend_b/` kopieren
- Eigene `main.py` nur mit Public-Endpoints
- Läuft auf Port 8085

### Schritt 3: Vite-Proxy umbiegen

```js
// vite.config.js — einzige Änderung
proxy: {
  '/api': 'http://localhost:8085',   // vorher: :8000
  '/scans': 'http://localhost:8085',
}
```

### Schritt 4: Nginx-Routing in Produktion

Laut T3-nginx-config.md routet Nginx dann:
- `/api` → `backend_b:8085` (Public API)
- `/admin` → `backend_a:8101` (Admin)
- `/scans` → direkt aus Volume

### Schritt 5: Admin-UI aus Backend A entfernen

- `static/index.html` wandert in Backend A
- Backend B serviert kein Admin-UI mehr

---

## 4. Warum das aufgeht

| Frontend-Code | Migrationsaufwand |
|---|---|
| `useApi.js` (Composable) | Keine Änderung — ruft `/api/v1/*` auf |
| `mocks/*.json` | Keine Änderung |
| Vue Router, Stores, Views | Keine Änderung |
| `vite.config.js` | **1 Zeile** (Proxy-Target) |
| Nginx Config | Macht ohnehin der DevOps-Teil |

Der Vite-Proxy ist ein reines Dev-Routing-Tool. Er beeinflusst weder die API-Verträge noch die Frontend-Logik. Die Endpoints können heute auf dem Single-Backend entwickelt und getestet werden — beim Split ändert sich nur die Ziel-Adresse im Proxy.

---

## 5. Fazit

**Single-Backend-Entwicklung ist der richtige Weg für Phase 1.** Sie reduziert Komplexität, beschleunigt Iterationen und blockiert keine späteren Architektur-Entscheidungen. Der Split in Backend A und B erfolgt erst wenn:
1. Der Public-Bereich tatsächlich veröffentlicht wird
2. Fuseki/SPARQL als zweite Datenquelle hinzukommt
3. Unterschiedliche Skalierung oder Deployment-Zyklen nötig werden
