# TODO

## Phase A: Auth-System

**Status: ABGESCHLOSSEN** ✅

### Erledigte Punkte:
- [x] `core/models.py`: User-Model mit UserRole Enum (admin/editor/viewer)
- [x] `services/auth_service.py`: Auth-Service mit bcrypt, Sessions, CRUD
- [x] `api/auth.py`: Auth-API (login, logout, me, users CRUD)
- [x] `alembic/versions/20260902000000_add_users_table.py`: Migration
- [x] Auto-Admin-User beim Start (admin/admin)
- [x] Frontend: V00Login.vue, V10Admin.vue, auth.js Store
- [x] Route Guards fuer geschuetzte Admin-Routes
- [x] Vite Proxy + nginx /auth Proxy
- [x] passlib[bcrypt] + bcrypt==4.2.1 Kompatibilitaet

---

## Phase B: Upload & Queue (Vue.js Admin)

**Status: OFFEN**

Ziel: PDF-Upload und Job-Queue in die Vue.js-UI ueberfuehren (erster Admin-Tab).

### Aufgaben
- [ ] Admin-Layout mit Sidebar-Navigation (`components/AdminLayout.vue`)
- [ ] PDF-Upload mit Drag & Drop (`views/V11Upload.vue`)
- [ ] Job-Queue Tabelle mit Status, Filter, Batch-Aktionen
- [ ] Live-Updates fuer Queue-Status (Polling)
- [ ] API-Endpoints fuer Admin: `/api/admin/documents`, `/api/admin/ocr/jobs`

### Tech-Details
- Komponenten: `UploadZone.vue`, `JobQueue.vue`, `JobRow.vue`
- Store: `stores/admin.js` (Dokumente, Jobs)
- Sidebar-Gruppen: Upload, Seiten, Erschließung, OCR, Stories

### Aufwand: ~2-3 Tage

---

## Phase C: Document Units + Erschließung (Vue.js Admin)

**Status: OFFEN**

Ziel: Document-Units und Erschliessungs-Daten in Vue.js verwalten.

### Aufgaben
- [ ] Document-Units Liste + Detail-Ansicht
- [ ] Unit erstellen/bearbeiten/loeschen
- [ ] Erschliessung mit 6 Sub-Tabs:
  - [ ] Personen-Liste
  - [ ] Seiten-Zuordnung
  - [ ] BBox-Boxen
  - [ ] Karte (Leaflet)
  - [ ] Events
  - [ ] Notizen
- [ ] Unassigned Pages anzeigen und zuordnen

### Aufwand: ~3-4 Tage

---

## Phase D: Seiten-Bearbeitung + BBox (Vue.js Admin)

**Status: OFFEN**

Ziel: OCR-Review, Qualitaetsmanagement und BBox-Verwaltung.

### Aufgaben
- [ ] Review-Ansicht: OCR-Ergebnisse pruefen und korrigieren
- [ ] Seiten-Management: Qualitaetsmetriken, Status
- [ ] Winkel/Deskew: Ausrichtung korrigieren
- [ ] BBox-Liste: Alle Bounding Boxes mit Filtern
- [ ] Persistente Regionen: Regionen-Verwaltung

### Aufwand: ~3-4 Tage

---

## Phase E: OCR & Analyse + Stories (Vue.js Admin)

**Status: OFFEN**

Ziel: OCR-Einstellungen, Content-Analyse und Story-Management.

### Aufgaben
- [ ] OCR-Sichtung: Einstellungen fuer Ollama Vision
- [ ] Content-Analyse: Analyse-Einstellungen
- [ ] Stories CRUD (Editor mit Markdown-Preview)
- [ ] Story-Notizen: Zuordnung von Notes zu Stories
- [ ] Featured-Toggle fuer Stories

### Aufwand: ~2-3 Tage

---

## Phase F: UI-Polish + Responsive

**Status: OFFEN**

Ziel: Finale UI-Qualitaet und Mobile-Unterstuetzung.

### Aufgaben
- [ ] Klare Sidebar-Struktur mit Gruppen
- [ ] Responsive Design (Mobile-freundlich)
- [ ] Loading States und Error Handling
- [ ] Toast-Notifications fuer Aktionen
- [ ] Keyboard Shortcuts
- [ ] Dark Mode (optional)

### Aufwand: ~2 Tage

---

## Phase G: Legacy-UI Deaktivierung

**Status: OFFEN**

Ziel: Legacy-Frontend (static/index.html) abschalten sobald Vue.js Admin komplett ist.

### Aufgaben
- [ ] Pruefen welche Legacy-Features noch fehlen
- [ ] Restliche Features migrieren oder als unnoetig markieren
- [ ] Legacy-Index-Route deaktivieren/nur noch Admin-Login zeigen
- [ ] Alte JS/CSS-Dateien entfernen

### Aufwand: ~1 Tag

---

## Phase 1-5: Fruehere Phasen (abgeschlossen)

| Phase | Beschreibung | Status |
|-------|--------------|--------|
| Phase 1 | Story-Datensatz (Curated Stories) | ✅ ABGESCHLOSSEN |
| Phase 2 | Admin-UI fuer Stories | ⏩ Wird in Phase G integriert |
| Phase 3 | Future (AI-Draft, Citations, Story-Liste) | ⏩ Wird in Phase E integriert |
| Phase 4 | Service Layer (TDD) | ✅ ABGESCHLOSSEN |
| Phase 5 | MCP Server + Agenten (litellm) | ✅ ABGESCHLOSSEN |

---

## Gesamtplan-Uebersicht

```
Phase A (Auth)         ✅ Fertig
    ↓
Phase B (Upload)       ~2-3 Tage
    ↓
Phase C (Units)        ~3-4 Tage
    ↓
Phase D (Review)       ~3-4 Tage
    ↓
Phase E (OCR+Stories)  ~2-3 Tage
    ↓
Phase F (Polish)       ~2 Tage
    ↓
Phase G (Legacy weg)   ~1 Tag
    ↓
FERTIG                 ~13-17 Tage
```

### Prioritaet
1. Phase B (Upload) - naechster Schritt
2. Phase C (Units) - Kernfunktionalitaet
3. Phase D (Review) - OCR-Workflow
4. Phase E (OCR+Stories) - Restliche Admin-Funktionen
5. Phase F (Polish) - Qualitaet
6. Phase G (Legacy) - Aufraeumen
