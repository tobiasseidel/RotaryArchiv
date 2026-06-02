# T6-build-reihenfolge.md — Build-Reihenfolge Phase 1 + Phase 2

> **Version:** 1.0 — 2026-05-03
> **Thread:** T6 Frontend-Entwickler
> **Phase:** Planning Phase
>
> **⚠️ Aktualisiert durch T9-dev-strategie.md:** Dieses Dokument nennt
> "Gegen echtes Backend B" als Phase-2-Ziel. Laut T9 wird Phase 1 gegen
> das **Single-Backend** entwickelt. Die Build-Reihenfolge bleibt gültig,
> nur dass das API-Ziel nicht Backend B, sondern das Single-Backend unter
> `/api/v1/` ist. Siehe [T9-dev-strategie.md](T9-dev-strategie.md).

---

## Phase 1 — Demonstrator (Ziel: Vorstand überzeugen)

### Zielkriterien

- Ein Mensch vom Rotary Club Dresden sitzt davor und versteht sofort, was das werden soll
- 3 Views funktional: V01 Startseite, V03 Personenprofil, V04 Dokumentansicht
- Mock-Daten, kein echtes Backend
- Kein Auth, kein vollständiges Routing
- Responsive auf Desktop + Tablet + Mobile

### Reihenfolge

#### Schritt 1: Projekt-Setup (Tag 1)

```
1.1  npm create vue@latest rotary-frontend
     → Vue Router ✓
     → Pinia ✓
     → ESLint ✗ (optional)
     → TypeScript ✗

1.2  @fontsource/lora + @fontsource/inter installieren

1.3  vite.config.js: base path, alias @/

1.4  main.css: Design-Tokens aus T5-designsystem-v1.1.md kopieren
     → :root { --color-* }
     → .epoch-30er, .epoch-90er Klassen

1.5  .env: VITE_USE_MOCK=true
```

#### Schritt 2: Routing-Grundgerüst (Tag 1–2)

```
2.1  router/index.js anlegen
     → 3 Routen für Phase 1 (lazy loaded)
     → / → V01Home
     → /person/:slug → V03Person
     → /dokument/:id → V04Document

2.2  App.vue: Layout-Struktur mit RouterView

2.3  EpochStore (Pinia) anlegen
     → current: '30er'
     → setEpoch(epoch)
     → epochClass computed
```

#### Schritt 3: Basis-Komponenten (Tag 2–3)

```
3.1  AppHeader.vue (Navigation, Such-Icon, Login-Platzhalter)
3.2  AppFooter.vue (Statistik-Widget, Links)
3.3  EpochBadge.vue (Epochen-Tag, z.B. "Die 30er")
3.4  EntityCard.vue (Person, Dokument, Stub-Varianten)
```

#### Schritt 4: V03 Personenprofil (Tag 3–5)

```
4.1  V03Person.vue: Routing + Composables einbinden
4.2  PersonProfile.vue (K04): Vollständiges Layout
     → Portrait
     → Metadaten
     → MembershipBlock (Aufnahme, Austritt)
     → AttendanceHeatmap
     → TimelineBlock
     → NetworkGraph–Mini (Statisch, Mock-Daten)
4.3  usePersons composable einbinden
4.4  Stub-Response Demo → in Phase 2 (Phase 1 nutzt nur öffentliche 30er-Personen)
```

#### Schritt 5: V04 Dokumentansicht (Tag 5–7)

```
5.1  V04Document.vue: Routing + Composables
5.2  DocumentDualView.vue (K05): Scan + Transkription
5.3  GapInline.vue: Unleserliche Stellen als klickbare Lücken
5.4  useDocuments composable
5.5  Dual-View Tabs für Mobile ( statt Side-by-Side )
```

#### Schritt 6: V01 Startseite (Tag 7–9)

```
6.1  V01Home.vue: Layout
6.2  HeroBlock.vue (K02): Tägliches Zitat, Quelle, Datum
6.3  Featured Persons: EntityCards der 2–3 prominentesten 30er
6.4  Epochen-Einstieg: Kacheln "Die 30er" / "Die 90er"
6.5  useFeatured composable
```

#### Schritt 7: Responsive Check + Accessibility (Tag 9–10)

```
7.1  Mobile-Layout testen (768px, 480px)
     → EntityCards: 1 Spalte
     → DocumentDualView: Tabs
     → Navigation: Hamburger oder Scroll

7.2  Keyboard-Navigation: Tab-Reihenfolge, Focus-States
     → WCAG 2.1 AA

7.3  Screenreader-Tests: aria-labels, alt-Texte

7.4  Epoch-Farben: Testen auf .epoch-30er / .epoch-90er
```

#### Schritt 8: Demo-Deployment auf NAS (Tag 10–11)

```
8.1  npm run build → dist/
8.2  rsync dist/ nas:/volume1/docker/rotary-archiv/frontend_b/dist/
8.3  docker compose restart nginx (oder nginx -s reload)
8.4  Smoke Test:
     → Startseite lädt
     → Personenprofil zeigt Mock-Daten
     → Dokument zeigt Scan + Transkription
     → Stub-Response bei 90er-Person
```

### Phase-1-Abnahme-Kriterien

| Kriterium | Test |
|---|---|
| Startseite zeigt Hero-Block + Featured Persons | Visuell |
| Personenprofil zeigt vollständige Timeline | Klick auf 30er-Person |
| Stub-Response bei 90er-Person | Klick auf 90er-Person → Erklärtext |
| Dokumentansicht: Scan + Transkription sichtbar | Klick auf Dokument |
| GapInline: Unleserliche Stellen klickbar | Blick auf Scan-Text |
| Responsive: Mobile Ansicht funktional | Browser-DevTools |
| Keine Console-Errors | DevTools Console |

---

## Phase 2 — Vollständiges Frontend (nach Club-Freigabe)

### Zielkriterien

- Alle 12 Views funktional
- Auth (JWT) für 90er-Inhalte
- Leaflet-Karte (V06)
- Netzwerk-Graph (V07)
- GapInline-Contribution (Feature A)
- AmtsStrahl (Feature D)
- Consent-Workflow (Feature C)
- Gegen echtes Backend B (REST-API)

### Reihenfolge (grob)

```
Phase 2.1  — Auth + Stores (1 Woche)
├─ Pinia auth.js: JWT-Handling, Refresh, Logout
├─ useAuth composable
├─ Login/Logout-UI in AppShell
├─ Route-Guards für geschützte Routen

Phase 2.2  — Erweiterte Views (2 Wochen)
├─ V02Epochs: Epoch-Übersicht + AmtsStrahl
├─ V05Search: Suchergebnisse + Filter
├─ V06Map: Leaflet-Karte mit Markern
├─ V07Network: D3.js Vollgraph

Phase 2.3  — Community-Features (1 Woche)
├─ V08StoryDetail: Story + StorySourcePanel
├─ V09StorySubmit: ContributionForm (Story)
├─ V10CorrectionSubmit: ContributionForm (Korrektur)
├─ V11Profile: Nutzerprofil + Consent-Management

Phase 2.4  — V12 + Fine Tuning (1 Woche)
├─ V12About: "Was der Club kontrolliert"
├─ ConsentProgress: Vollständig
├─ Finales Design-Review
├─ Performance-Optimierung

Phase 2.5  — Backend-Anbindung (1 Woche)
├─ useApi.js: Mock → Echt
├─ .env.production: VITE_USE_MOCK=false
├─ End-to-End Test gegen Backend B
```

### Auth-Requierte Views

| View | Auth-Status | Begründung |
|---|---|---|
| V02Epochs | Anonym + Auth | 30er öffentlich, 90er eingeloggt |
| V03Person | Anonym + Auth | 30er öffentlich, 90er Stub/Auth |
| V04Document | Anonym + Auth | 30er öffentlich, 90er Stub/Auth |
| V05Search | Anonym | Nur öffentliche Ergebnisse |
| V06Map | Anonym + Auth | 30er öffentlich, 90er eingeloggt |
| V07Network | Anonym | Nur öffentliche Verbindungen |
| V08StoryDetail | Anonym | Nur approved Stories |
| V09StorySubmit | Anonym | Niedrigschwellig, anon erlaubt |
| V10CorrectionSubmit | Anonym | Niedrigschwellig, anon erlaubt |
| V11Profile | **Auth Pflicht** | Nur für eingeloggte Nutzer |
| V12About | Anonym | Öffentliches Vertrauensdokument |

---

## Abhängigkeitsgraph

```
Phase 1:
┌─────────────┐     ┌─────────────┐
│ 1. Setup    │────▶│ 2. Router   │────▶┌─────────────┐
└─────────────┘     └─────────────┘     │ 3. Basis-K  │
                                         └─────────────┘
                                                │
                                                ▼
                                        ┌─────────────┐
                                        │ 4. V03      │────▶┌─────────────┐
                                        └─────────────┘     │ 5. V04      │
                                                             └─────────────┘
                                                                    │
                                                                    ▼
                                                            ┌─────────────┐
                                                            │ 6. V01      │────▶┌─────────────┐
                                                            └─────────────┘     │ 7. Responsive│
                                                                                └─────────────┘
                                                                                       │
                                                                                       ▼
                                                                               ┌─────────────┐
                                                                               │ 8. Deploy   │
                                                                               └─────────────┘
```

---

## Geschätzter Zeitrahmen

| Phase | Aufwand | Dauer (geschätzt) |
|---|---|---|
| Phase 1 | 10–11 Tage | 2–3 Wochen (parallel zu anderem Job) |
| Phase 2 | 5–6 Wochen | 2–3 Monate |

---

*Weiter zu: T6-offene-fragen.md*
