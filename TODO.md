# TODO

## Phase 1: Story-Datensatz (Curated Stories)

### Backend – Datenmodell & Migration
- [ ] `core/models.py`: Neues Model `Story` mit Feldern:
  `id, slug, title, teaser, body (Text/Markdown), epoch, image_url,
   is_published (bool), is_featured (bool), created_at, updated_at, created_by`
- [ ] `core/models.py`: Spalte `story_id` (nullable FK → Story.id) an `BBox`-Model anhängen
- [ ] Alembic-Migration: `stories`-Tabelle + `bboxes.story_id`
- [ ] `api/schemas.py`: Pydantic-Schemas `StoryResponse`, `StoryDetail`

### Backend – Admin API (`/api/`)
- [ ] `api/stories.py` (neu): CRUD-Router für Stories
  - `GET /api/stories` – Alle Stories
  - `GET /api/stories/{id}` – Inkl. zugehöriger Notes
  - `POST /api/stories` – `{ title, note_ids: [...] }` → erstellt Story + setzt `story_id` auf Notes
  - `PATCH /api/stories/{id}` – Update (body, notes, featured, published)
  - `DELETE /api/stories/{id}` – Notes werden wieder unassigned
- [ ] `api/erschliessung_overview.py`: `GET /notes` erweitern
  - Response um `story_id` ergänzen
  - Query-Parameter `unassigned=true` → nur Notes ohne Story

### Backend – Public API (`/api/v1/`)
- [ ] `api/v1.py`: Neue Public Endpoints
  - `GET /api/v1/stories/featured` – Die eine gefeaturete Story für Homepage
  - `GET /api/v1/stories` – Publizierte Stories (Liste)
  - `GET /api/v1/stories/{slug}` – Story-Detail + Notes als Quellen

### Frontend – Mock-Daten
- [ ] `mocks/stories.json`: Curated Stories ergänzen (Teaser, Body mit Markdown, Epoch, Document-Referenzen)

### Frontend – API-Layer (`useApi.js`)
- [ ] `getFeaturedStory()` → `/api/v1/stories/featured`
- [ ] `getStories()` → `/api/v1/stories`
- [ ] `getStory(slug)` → `/api/v1/stories/{slug}`

### Frontend – Homepage Hero
- [ ] `HeroBlock.vue`: Umbau auf Story-Darstellung
  - Teaser statt raw-quote
  - Link zur Story-Detailseite
  - Link zu verknüpften Personen/Dokumenten
- [ ] `V01Home.vue`: Ruft `getFeaturedStory()` statt `getFeatured()` auf

### Frontend – Story-Detail
- [ ] `views/V02Story.vue` (neu): Story-Detail mit:
  - Markdown-Rendering (z. B. `marked`-Library einbinden)
  - Quellenblock: verknüpfte Notes als Belegzitate mit Seitenlink
  - Personen-Netzwerk / Document-Links aus der Story
- [ ] `router/index.js`: Route `/geschichte/:slug` aktivieren
- [ ] Package: `marked` als dependency hinzufügen

### Frontend – CSS/Theming
- [ ] Story-spezifische Styles (Artikel-Layout, Quellenblock, Zitate)

---

## Phase 2: Admin-UI für Stories

- [ ] Neuer Tab "Stories" unter Erschließung in der Admin-Oberfläche
- [ ] Notizen-Multiselect (Checkboxen) mit "Create Story"-Button
- [ ] Story-Editor: Titel, Body (Markdown mit Preview), Featured-Toggle
- [ ] Notes in einer Story: anzeigen, entfernen, hinzufügen

---

## Phase 3: Future

- [ ] AI-Draft aus Notizen via Ollama generieren
- [ ] Inline-Citation-Parsing (Wiki-Stil `[^1]` → Fußnote/Quelle)
- [ ] Story-Listenseite im Frontend (`/geschichten`)
- [ ] Story-Card-Komponente für Listendarstellung
