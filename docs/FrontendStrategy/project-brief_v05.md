# RotaryArchiv — Project Brief

> **Version:** 0.5 — 2026-05-03
> **Status:** Aktiv — wird von allen Threads als Kontext-Einleitung verwendet
> **Zweck:** Zentrales Orientierungsdokument für alle Experten-Threads im Perplexity Space
> **Änderungen v0.5:** T1 Iteration — neuer Archetyp „Der Vorstand" (Klaus-Peter);
>   Projektstrategie um Zwei-Phasen-Modell ergänzt (Demonstrator → Öffentliches Archiv);
>   Zielgruppen-Tabelle aktualisiert; Emotionaler Kern um Vertrauensdimension erweitert;
>   V12 als Vertrauensdokument für Vorstand markiert; Glossar erweitert.

---

## Projektziel

Der Rotary Club Dresden wird 100 Jahre alt. Das Projekt **RotaryArchiv** erschließt und
präsentiert die Geschichte des Clubs auf Basis gescannter Protokolle und weiterer Dokumente.

Das Projekt besteht aus **zwei sich gegenseitig bedingenden Schichten**:

- **Schicht A — Erschließungswerkzeug (intern):** OCR, Qualitätsprüfung, Triplestore-Befüllung, Admin-Interface
- **Schicht B — Präsentationsfrontend (teilöffentlich):** Öffentlich zugängliches Web-Frontend für verschiedene Besuchergruppen

### Zwei Phasen des Projekts (entschieden T1 v1.2)

Das Projekt ist zunächst ein **Argument gegenüber dem Club**, kein fertiger Auftrag.

| Phase | Bezeichnung | Primäre Zielgruppe | Ziel des Frontends |
|---|---|---|---|
| **Phase 1** | Demonstrator | Vorstand (Klaus-Peter) | Vertrauen aufbauen, Kontrolle demonstrieren |
| **Phase 2** | Öffentliches Archiv | Alle fünf Archetypen | Entdeckung, Forschung, Community |

> **Konsequenz für Entwicklung:** In Phase 1 ist ein überzeugender Prototyp mit wenigen, tief
> erschlossenen Personen wichtiger als ein vollständiges System. V12 ist in Phase 1 die
> strategisch wichtigste Seite des gesamten Frontends.

---

## Technischer Stack

### Backend — Zwei getrennte Prozesse (entschieden in T2)

> **Architekturentscheidung:** Schicht A und Schicht B erhalten **getrennte FastAPI-Backends**.
> Sie teilen sich PostgreSQL-Datenbank und Apache Fuseki Triplestore, aber keinen Code-Prozess.
> Gemeinsamer Code lebt im lokalen Package `rotary_core`.

```
         PostgreSQL  ◄─────────────────────────────────►
         Apache Fuseki ◄───────────────────────────────►
                  │                              │
        Backend A (bestehend)          Backend B (neu zu bauen)
        FastAPI · OCR · Admin          FastAPI · Public API
        Port ${BACKEND_A_PORT} (intern)        Port ${BACKEND_B_PORT} (intern)
                  │                              │
        Frontend A (Admin, lokal)      Frontend B (öffentlich, Nginx)
        static/index.html              neu zu bauen (T5/T6)
```

> **Ports:** Konfigurierbar via `.env` (`BACKEND_A_PORT`, `BACKEND_B_PORT`).
> Beispielwerte: 8101 (A) / 8085 (B). Kein Hardcode im Code.

**Shared Package `rotary_core`** (neu, aus T2):
- Enthält: `models.py`, `triplestore.py`, `database.py`, `config.py`, `crypto.py` (neu T3)
- Beide Backends importieren daraus — eine einzige Quelle, kein Drift-Risiko
- Alembic-Migrationen laufen ausschließlich in Backend A
- Schema-Hoheit liegt dauerhaft bei Schicht A

| Komponente | Framework / Technologie |
|---|---|
| Backend A + B | FastAPI (Python) |
| ORM | SQLAlchemy mit Alembic-Migrationen |
| Datenbank | SQLite (Entwicklung) / PostgreSQL (Produktion) |
| Triplestore | rdflib + Apache Fuseki TDB2 (aktiv, persistent via Docker-Volume) |
| OCR-Engine | Ollama Vision (lokal), optional Tesseract |
| Wikidata | Personen und Orte verknüpft, Claims synchronisiert |
| Auth | JWT — Access Token (60 Min) + Refresh Token (30 Tage, rotierend) |
| E-Mail-Verschlüsselung | Fernet (AES-128-CBC + HMAC) via `rotary_core/crypto.py` |

### Frontend Schicht A (Admin, bestehend)
- Vanilla JavaScript, Single HTML File (`static/index.html`, ~12.000 Zeilen)
- Tab-basierte Navigation, Leaflet für Karten
- **Status:** Funktional, aber technisch verschuldet — kein Umbau geplant

### Frontend Schicht B (Präsentation, neu zu bauen)
- **Framework:** Offen — Entscheidung in T5 Frontend/Design-Thread
- **Deployment:** Lokal auf NAS, über Nginx öffentlich exposed
- **Auth:** JWT — Access Token optional, Admin-Endpoints pflicht-gesichert
- **Sprache:** Deutsch (keine Mehrsprachigkeit geplant)

### Infrastruktur (entschieden in T3)

- **Deployment-Umgebung:** NAS (lokal), Docker + Portainer
- **Öffentlicher Zugang:** Nur Nginx exposed (:80/:443) — Backend, DB, Fuseki intern
- **Reverse Proxy:** Nginx (TLS-Terminierung, SPA-Fallback, API-Proxy auf `/api/`)
- **TLS:** Let's Encrypt via Certbot (automatische Erneuerung im Docker-Container)
- **Triplestore-Persistenz:** Apache Fuseki TDB2, Daten in Docker-Volume `fuseki_data`
- **Domain:** Konfigurierbar via `ROTARY_DOMAIN` in `.env` — aktuell geplant als
  Subdomain einer bestehenden eigenen Domain; Club-Domain oder Neukauf als spätere Option
- **Docker-Netz:** `rotary_net` (bridge) — alle Services intern erreichbar, nur Nginx exposed
- **Deployment-Details:** → `T3-docker-compose.md`, `T3-nginx-config.md`
- **Update/Backup:** Shell-Skripte (`update.sh`, `rollback.sh`, `backup-db.sh`) → `T3-update-prozess.md`

---

## Datenmodell (Übersicht)

### Bestehende Kern-Entitäten (Schicht A, unverändert)

| Modell | Beschreibung |
|---|---|
| `Document` | Hauptdokument mit Metadaten und OCR-Workflow-Status |
| `DocumentPage` | Einzelne Seiten |
| `OCRJob` | Asynchrone Verarbeitungsaufträge |
| `OCRResult` | OCR-Ergebnisse verschiedener Quellen |
| `BBox` | Bounding Boxes mit Review-Status |
| `DocumentUnit` | Inhaltseinheiten aus mehreren Seiten |
| `ErschliessungsBox` | Triplestore-Brücke: entity-Boxen + beleg-Boxen (S/P/O) |

### Neue Entitäten (aus T2, noch zu implementieren in T6)

| Modell | Beschreibung | Phase |
|---|---|---|
| `Person` | Person als first-class DB-Objekt mit Slug, `is_public`, Epoche | P1 |
| `Place` | Ort mit Koordinaten, `is_public` | P2 |
| `HistoricalEvent` | Historisches Ereignis mit Datum, `is_public` | P2 |
| `Story` | Community-Beitrag mit `ContributionStatus`-Enum | P3 |
| `Correction` | Korrekturhinweis mit `ContributionStatus`-Enum | P3 |

### Neue Auth-Entitäten (aus T3, in rotary_core ergänzen)

| Modell | Beschreibung | Phase |
|---|---|---|
| `User` | Nutzer mit email, password_hash (bcrypt), role (user/admin) | vor P3 |
| `RefreshToken` | Refresh-Token-Store mit token_hash (SHA-256), TTL, revoked-Flag | vor P3 |

**Neues Enum:** `ContributionStatus: draft | submitted | approved | rejected`

### Triplestore (rdflib + Fuseki TDB2, aktiv, produktiv)

Personen, Orte und Ereignisse als RDF-Ressourcen mit URIs (`rotary:Person_X` etc.).
Wikidata-Claims via `wdt:P569` etc. synchronisiert.

**Ausstehende Erweiterung (T6, Phase P2):**
`rotary:date` auf Mention-Knoten — ermöglicht reine SPARQL-Zeitstrahl-Abfragen.

### Zugriffsmodell: `is_public`-Flag pro Objekt (entschieden T1/T3)

- **Kein Rollen-System.** Sichtbarkeit durch `is_public`-Boolean auf jedem Objekt.
- **Die 30er (1927–1937):** Objekte standardmäßig öffentlich.
- **Die 90er (1990–2008):** Objekte standardmäßig nicht-öffentlich; einzeln freischaltbar.
- **Nicht-öffentliche Objekte:** Anonymen Besuchern als erklärender Platzhalter angezeigt
  (HTTP 200 Stub-Response `{"stub": true, ...}`, kein 403/404).
- **Auth-Stufen:** anonym → nur `is_public=True`; eingeloggt (user) → alle freigeschalteten
  Inhalte; admin → zusätzlich Moderation-Queue und Approve/Reject-Endpoints.

### Anforderungen aus T1 — Bewertungsstatus

| Anforderung | Betroffene Objekte | Status |
|---|---|---|
| `is_public`-Flag | Person, Dokument, Story, Ort, Ereignis | ⚠️ Bewertet — neue Tabellen nötig (T6/P1–P2) |
| Beitragsstatus-Enum | Story, Korrektur | ❌ Bewertet — neue Tabellen nötig (T6/P3) |
| Stabile Slugs | Person | ❌ Bewertet — Person-Tabelle nötig (T6/P1) |
| Netzwerk-Abfrage | Triplestore | ⚠️ Bewertet — möglich, Erweiterung nötig (T6/P2) |
| Export-Endpoint BibTeX | Dokument | ❌ Bewertet — neuer Endpoint in Backend B (T6/P4) |
| Kontakt-E-Mail verschlüsselt | Story, Korrektur | ✅ Geklärt in T3 — Fernet, `rotary_core/crypto.py` |

---

## Quellmaterial

- **Primärquellen:** Gescannte Protokolle des Rotary Club Dresden
- **Epochen:** „Die 30er" (1927–1937) und „Die 90er" (1990–2008)
- **Umfang:** Etwa 1.200 Dokumente, z.T. mit mehreren Seiten
- **Format:** PDF-Dateien, seitenweise OCR-erschlossen
- **Besonderheiten:** Größtenteils Maschinenschrift, kleinere handschriftliche Anteile,
  zum Teil schlechte Scan-Qualität. Sprache ist Deutsch.

---

## Zielgruppen (entschieden in T1, aktualisiert v1.2)

→ Vollständige Archetypen und Jobs to be Done: `T1-ux-archetypen.md`

| Archetyp | Beschreibung | Typischer Zugang | Phase |
|---|---|---|---|
| **Klaus-Peter** (Vorstand) | Entscheidet über Freigabe — braucht Kontrolle und Vertrauen | Demo / intern | Phase 1 |
| **Karoline** (Familiendetektivin) | Sucht Vorfahren, kommt mit einem Namen | Öffentlich, ggf. eingeloggt | Phase 2 |
| **Wolfgang** (Insider) | Aktives/ehemaliges Mitglied, kennt die 90er | Eingeloggt | Phase 2 |
| **Dr. Miriam** (Forscherin) | Historikerin, braucht Quellenarbeit und Export | Eingeloggt, erweitert | Phase 2 |
| **Jannik** (Neugieriger) | Entdeckt das Archiv zufällig, will stöbern | Öffentlich | Phase 2 |

> Klaus-Peter ist kein dauerhafter Nutzer, sondern der Gatekeeper.
> Erst nach seiner Freigabe werden die anderen vier Archetypen zur primären Zielgruppe.

### Beitragsmodell
- **Anonyme Beiträge sind erlaubt** (Stories, Korrekturen) — ohne Account-Pflicht.
- Beiträge ohne Login → **Moderationswarteschlange** (Admin-Freigabe nötig).
- Beiträge von eingeloggten Nutzern → direkt sichtbar.

---

## Interaktionsprinzip (entschieden in T1)

- **Rabbit Hole:** Jede Entität hat eine stabile, sprechende URL und mindestens 3 Querverweise.
- **Entity-First-Navigation:** Primäre Navigation durch Klick auf verknüpfte Entitäten.
- **Progressive Disclosure:** Nicht-öffentliche Inhalte werden erklärt, nicht versteckt.

---

## Emotionaler Kern (entschieden in T1, erweitert v1.2)

> **„RotaryArchiv ist der Ort, an dem vergessene Namen wieder zu Menschen werden."**

→ Vollständige Tonalität, UI-Textbeispiele, Zwei-Phasen-Modell: `T1-emotionaler-kern.md`

**Phasenabhängige Gewichtung:**
- **Phase 1:** Kernbotschaft für den Vorstand — *„Der Club entscheidet, was sichtbar ist."*
- **Phase 2:** Kernbotschaft für alle — *„Vergessene Namen werden wieder zu Menschen."*

---

## Informationsarchitektur (entschieden in T1)

→ Vollständige View-Beschreibungen, URL-Schema: `T1-informationsarchitektur.md`

**12 Views:**
`V01 Startseite` · `V02 Epochen-Übersicht` · `V03 Personenprofil` · `V04 Dokumentansicht`
· `V05 Suche` · `V06 Karte` · `V07 Netzwerk-Graph` · `V08 Story-Detail`
· `V09 Story einreichen` · `V10 Korrektur einreichen` · `V11 Nutzerprofil` · `V12 Über das Projekt`

> **V12 — Über das Projekt** ist in Phase 1 das wichtigste Vertrauensdokument des Frontends.
> Pflichtabschnitte: „Was der Club kontrolliert" + „Was wir nicht zeigen ohne Freigabe".
> → Details in `T1-informationsarchitektur.md`

---

## Experten-Threads — Übersicht

```
T1 Konzept & UX          ──┐
T2 Datenmodell-Audit     ──┤──▶ T5 Frontend/Design ──▶ T6 Coding (OpenCode)
T3 Auth & Deployment     ──┘

T4 Refactoring Schicht A            (parallel, unabhängig)
T7 OCR/NLP-Pipeline                 (parallel, unabhängig)
```

| Thread | Fokus | Status | Wartet auf |
|---|---|---|---|
| T1 Konzept & UX | User-Archetypen, IA, emotionaler Kern, Zwei-Phasen-Modell | ✅ Abgeschlossen (v1.2) | — |
| T2 Datenmodell-Audit | Triplestore-Capabilities, neue T1-Anforderungen, Backend-Architektur | ✅ Abgeschlossen | — |
| T3 Auth & Deployment | NAS-Deployment, Auth-Mechanismus, E-Mail-Verschlüsselung, Fuseki-Konfiguration | ✅ Abgeschlossen | — |
| T4 Refactoring A | job_processor.py, Schicht-A-Architektur | 🔲 Offen | — |
| T5 Frontend/Design | Visuelle Sprache, Komponenten, Prototyp | 🔲 Offen | T1 ✅, T2 ✅, T3 ✅ |
| T6 Coding | Implementierung Schicht B (Backend B + Frontend B) | 🔲 Offen | T5, T3 ✅ |
| T7 OCR/NLP | Prompt-Optimierung, Entity Extraction | 🔲 Offen | — |

---

## Bekannte technische Schulden (Schicht A)

- `job_processor.py` hat 3.069 Zeilen — Aufteilung nötig (T4)
- Admin-Frontend: 12.050 Zeilen in einer HTML-Datei (T4)
- ~~Authentication noch nicht implementiert~~ → T3 abgeschlossen, Implementierung in T6
- Fehlende Service-Schicht zwischen API und Datenzugriff (T4)
- Legacy-Felder im Document-Modell (`ocr_text`, `ocr_text_tesseract` etc.) — nach Migration entfernen
- NOTE-Kommentar in `triplestore.py:4` ist veraltet — Triplestore ist aktiv in Verwendung

---

## Offene Entscheidungen

| Entscheidung | Zuständig | Status |
|---|---|---|
| Frontend-Framework für Schicht B (React / Vue / andere) | T5 | 🔲 Offen |
| `DocumentStatus.PUBLISHED` ablösen oder parallel zu `is_public` führen? | T6 | 🔲 Offen |
| Altes Triplestore-Modell (`rotary:erwaehnt`) deprecaten? | T6 | 🔲 Offen |
| Kookkurrenz-Tabelle als Denormalisierung oder Live-SPARQL? | T6 | 🔲 Offen |
| Konkrete Domain (Subdomain welcher Domain?) | Projektinhaber | 🔲 Offen |
| ~~Auth-Mechanismus für Backend B~~ | ~~T3~~ | ✅ JWT (Access 60 Min + Refresh 30 Tage) |
| ~~Verschlüsselungsverfahren für `author_email_enc`~~ | ~~T3~~ | ✅ Fernet (`rotary_core/crypto.py`) |
| ~~Fuseki bereits produktiv oder noch einzurichten?~~ | ~~T3~~ | ✅ TDB2, Docker-Volume, produktiv |
| ~~Reverse Proxy Konfiguration (Nginx, Ports)~~ | ~~T3~~ | ✅ Dokumentiert in T3-nginx-config.md |
| ~~Öffentliche Domain / URL~~ | ~~T3~~ | ✅ Konfigurierbar via `ROTARY_DOMAIN` in `.env` |
| ~~Triplestore-Vollständigkeit & API-Capabilities~~ | ~~T2~~ | ✅ Bewertet in T2 |

---

## Glossar

| Begriff | Bedeutung |
|---|---|
| Schicht A | Internes Erschließungswerkzeug (OCR, Admin) |
| Schicht B | Öffentliches Präsentationsfrontend |
| Backend A | FastAPI-Prozess für Schicht A (bestehend) |
| Backend B | FastAPI-Prozess für Schicht B (neu zu bauen) |
| rotary_core | Lokales Python-Package mit geteilten Modellen + Crypto (neu ab T2/T3) |
| Triplestore | RDF-Wissensdatenbank, rdflib + Apache Fuseki TDB2 |
| ErschliessungsBox | DB-Modell für die Triplestore-Integration |
| Protokoll | Gescanntes Sitzungsprotokoll des Rotary Club Dresden |
| Erschließung | Strukturierte Extraktion von Entitäten aus OCR-Text |
| BBox | Bounding Box — Positionsangabe einer Textstelle auf einer Seite |
| NAS | Network Attached Storage — lokaler Heimserver des Projektinhabers |
| is_public | Boolean-Flag auf Objekt-Ebene — steuert Sichtbarkeit im Frontend |
| Stub-Response | HTTP 200 mit `{"stub": true, ...}` für nicht-öffentliche Objekte (statt 403/404) |
| Rabbit Hole | Interaktionsprinzip: jeder Klick öffnet neue verknüpfte Entitäten |
| Die 30er | Epoche 1927–1937 — standardmäßig öffentlich |
| Die 90er | Epoche 1990–2008 — standardmäßig nicht-öffentlich |
| ContributionStatus | Enum: draft / submitted / approved / rejected (neu ab T2) |
| JWT | JSON Web Token — Auth-Mechanismus für Backend B (entschieden T3) |
| Access Token | JWT, 60 Min Laufzeit, enthält user_id + role |
| Refresh Token | Opaque Token, 30 Tage, rotierend, hash-gespeichert in DB |
| Fernet | Symmetrisches Verschlüsselungsformat (AES-128-CBC + HMAC-SHA256) |
| rotary_net | Docker-Bridge-Netz — alle Services intern, nur Nginx nach außen |
| ROTARY_DOMAIN | .env-Variable für die öffentliche Domain — einzige Stelle im gesamten Projekt |
| Klaus-Peter | Vorstand-Archetyp — primäre Zielgruppe in Phase 1, Gatekeeper für Freigabe |
| Phase 1 | Demonstrator-Phase: Überzeugungsarbeit beim Vorstand vor öffentlicher Freigabe |
| Phase 2 | Vollbetrieb: öffentliches Archiv nach Club-Freigabe, alle Archetypen aktiv |
| Vertrauensdokument | Bezeichnung für V12 in Phase 1 — erklärt Kontrollversprechen an den Vorstand |

---

*Dieses Dokument wird von allen Threads als Kontext-Einleitung verwendet.
Bei jeder größeren Entscheidung im Projekt bitte hier aktualisieren.*
