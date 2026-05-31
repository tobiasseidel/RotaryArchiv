# T3-docker-compose.md

> **Thread:** T3 Auth & Deployment  
> **Version:** 1.0 — 2026-05-02  
> **Abhängigkeiten:** T3-nginx-config.md, T2-migrations-plan.md  
> **Input für:** T6 Coding

---

## Überblick

Alle Dienste laufen in einem gemeinsamen Docker-Netz (`rotary_net`).
Nur Nginx ist nach außen exposed. Backend A, Backend B, PostgreSQL und
Fuseki sind ausschließlich intern erreichbar.

```
rotary_net (intern)
├── nginx          → :80, :443 (exposed)
├── backend_a      → :${BACKEND_A_PORT} (nur intern)
├── backend_b      → :${BACKEND_B_PORT} (nur intern)
├── postgres       → :5432 (nur intern)
└── fuseki         → :3030 (nur intern)
```

---

## Verzeichnisstruktur auf der NAS

```
/volume1/docker/rotary-archiv/
├── .env                          ← Alle Secrets und Ports (nie in Git!)
├── docker-compose.yml
├── docker-compose.override.yml   ← Lokale Entwicklungs-Overrides (in .gitignore)
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── rotary.conf
├── packages/
│   └── rotary_core/              ← Shared Package (aus T2 P0)
├── backend_a/                    ← Schicht A
├── backend_b/                    ← Schicht B
├── postgres/
│   └── init/
│       └── 01-init.sql           ← DB-Initialisierung (einmalig)
├── fuseki/
│   ├── config/
│   │   └── rotary.ttl            ← Fuseki-Dataset-Konfiguration
│   └── data/                     ← Persistente RDF-Daten (Volume)
└── frontend_b/
    └── dist/                     ← Build-Artefakte (von CI/lokalem Build)
```

---

## .env — Umgebungsvariablen

```bash
# .env  —  NICHT in Git committen

# ── Ports ──────────────────────────────────────────────────────────────────
BACKEND_A_PORT=8101
BACKEND_B_PORT=8085

# ── Domain ─────────────────────────────────────────────────────────────────
ROTARY_DOMAIN=archiv.rotary-dresden.de
ADMIN_EMAIL=admin@rotary-dresden.de

# ── Datenbank ───────────────────────────────────────────────────────────────
POSTGRES_DB=rotary_archiv
POSTGRES_USER=rotary
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
DATABASE_URL=postgresql://rotary:CHANGE_ME_STRONG_PASSWORD@postgres:5432/rotary_archiv

# ── Fuseki ───────────────────────────────────────────────────────────────────
FUSEKI_ADMIN_PASSWORD=CHANGE_ME_FUSEKI_PASSWORD
FUSEKI_DATASET=rotary
SPARQL_ENDPOINT=http://fuseki:3030/rotary

# ── Auth (Backend B) ─────────────────────────────────────────────────────────
JWT_SECRET_KEY=CHANGE_ME_RANDOM_256BIT_HEX
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ── E-Mail-Verschlüsselung ───────────────────────────────────────────────────
EMAIL_ENCRYPTION_KEY=CHANGE_ME_FERNET_KEY   # Fernet-Key, 32 Bytes base64

# ── Backend A spezifisch ────────────────────────────────────────────────────
OLLAMA_HOST=http://host.docker.internal:11434   # Ollama läuft nativ auf NAS
```

---

## docker-compose.yml

```yaml
version: "3.9"

networks:
  rotary_net:
    driver: bridge

volumes:
  postgres_data:
  fuseki_data:
  certbot_certs:
  certbot_webroot:

services:

  # ───────────────────────────────────────────────────────────────────────────
  # Nginx — einziger öffentlicher Eintrittspunkt
  # ───────────────────────────────────────────────────────────────────────────
  nginx:
    image: nginx:1.27-alpine
    container_name: rotary_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./frontend_b/dist:/var/www/rotary-frontend:ro
      - certbot_certs:/etc/nginx/certs:ro
      - certbot_webroot:/var/www/certbot:ro
    networks:
      - rotary_net
    depends_on:
      - backend_b
    environment:
      - ROTARY_DOMAIN=${ROTARY_DOMAIN}

  # ───────────────────────────────────────────────────────────────────────────
  # PostgreSQL
  # ───────────────────────────────────────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: rotary_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB:       ${POSTGRES_DB}
      POSTGRES_USER:     ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d:ro
    networks:
      - rotary_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ───────────────────────────────────────────────────────────────────────────
  # Apache Fuseki — Triplestore
  # ───────────────────────────────────────────────────────────────────────────
  fuseki:
    image: secoresearch/fuseki:latest    # oder stain/jena-fuseki
    container_name: rotary_fuseki
    restart: unless-stopped
    environment:
      ADMIN_PASSWORD: ${FUSEKI_ADMIN_PASSWORD}
      FUSEKI_DATASET: ${FUSEKI_DATASET}
    volumes:
      - fuseki_data:/fuseki/databases
      - ./fuseki/config:/fuseki/configuration:ro
    networks:
      - rotary_net
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:3030/$$/ping || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5

  # ───────────────────────────────────────────────────────────────────────────
  # Backend A — Schicht A (OCR, Admin, Erschließung)
  # ───────────────────────────────────────────────────────────────────────────
  backend_a:
    build:
      context: .
      dockerfile: backend_a/Dockerfile
    container_name: rotary_backend_a
    restart: unless-stopped
    environment:
      DATABASE_URL:    ${DATABASE_URL}
      SPARQL_ENDPOINT: ${SPARQL_ENDPOINT}
      OLLAMA_HOST:     ${OLLAMA_HOST}
      BACKEND_PORT:    ${BACKEND_A_PORT}
      JWT_SECRET_KEY:  ${JWT_SECRET_KEY}
      JWT_ALGORITHM:   ${JWT_ALGORITHM}
    volumes:
      - ./packages/rotary_core:/app/packages/rotary_core:ro
      # Scan-Dateien (read-write für OCR-Output)
      - /volume1/rotary-scans:/app/scans
    networks:
      - rotary_net
    depends_on:
      postgres:
        condition: service_healthy
      fuseki:
        condition: service_healthy
    # Kein Port-Mapping nach außen — nur intern erreichbar
    expose:
      - "${BACKEND_A_PORT}"
    extra_hosts:
      - "host.docker.internal:host-gateway"   # Für Ollama auf NAS-Host

  # ───────────────────────────────────────────────────────────────────────────
  # Backend B — Schicht B (Public API)
  # ───────────────────────────────────────────────────────────────────────────
  backend_b:
    build:
      context: .
      dockerfile: backend_b/Dockerfile
    container_name: rotary_backend_b
    restart: unless-stopped
    environment:
      DATABASE_URL:             ${DATABASE_URL}
      SPARQL_ENDPOINT:          ${SPARQL_ENDPOINT}
      BACKEND_PORT:             ${BACKEND_B_PORT}
      JWT_SECRET_KEY:           ${JWT_SECRET_KEY}
      JWT_ALGORITHM:            ${JWT_ALGORITHM}
      JWT_ACCESS_TOKEN_EXPIRE_MINUTES:  ${JWT_ACCESS_TOKEN_EXPIRE_MINUTES}
      JWT_REFRESH_TOKEN_EXPIRE_DAYS:    ${JWT_REFRESH_TOKEN_EXPIRE_DAYS}
      EMAIL_ENCRYPTION_KEY:     ${EMAIL_ENCRYPTION_KEY}
    volumes:
      - ./packages/rotary_core:/app/packages/rotary_core:ro
    networks:
      - rotary_net
    depends_on:
      postgres:
        condition: service_healthy
      fuseki:
        condition: service_healthy
    expose:
      - "${BACKEND_B_PORT}"

  # ───────────────────────────────────────────────────────────────────────────
  # Certbot — TLS-Erneuerung
  # ───────────────────────────────────────────────────────────────────────────
  certbot:
    image: certbot/certbot
    container_name: rotary_certbot
    restart: unless-stopped
    volumes:
      - certbot_certs:/etc/letsencrypt
      - certbot_webroot:/var/www/certbot
    networks:
      - rotary_net
    entrypoint: >
      sh -c "trap exit TERM;
             while :; do
               certbot renew --webroot -w /var/www/certbot --quiet;
               sleep 12h & wait $${!};
             done"
    environment:
      - ROTARY_DOMAIN=${ROTARY_DOMAIN}
      - ADMIN_EMAIL=${ADMIN_EMAIL}
```

---

## docker-compose.override.yml (lokale Entwicklung)

```yaml
# Nicht in Git — nur für lokale Entwicklung auf der NAS
version: "3.9"

services:
  backend_a:
    # Lokaler Source-Mount für Hot-Reload
    volumes:
      - ./backend_a/src:/app/src
    command: uvicorn rotary_archiv.main:app --host 0.0.0.0
             --port ${BACKEND_A_PORT} --reload
    ports:
      - "${BACKEND_A_PORT}:${BACKEND_A_PORT}"   # Nur lokal direkt erreichbar

  backend_b:
    volumes:
      - ./backend_b/src:/app/src
    command: uvicorn rotary_public.main:app --host 0.0.0.0
             --port ${BACKEND_B_PORT} --reload
    ports:
      - "${BACKEND_B_PORT}:${BACKEND_B_PORT}"

  postgres:
    ports:
      - "5432:5432"   # Direktzugriff für lokale DB-Tools (DBeaver etc.)
```

---

## Dockerfiles

### backend_a/Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System-Dependencies (für Pillow, psycopg2 etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Shared Package zuerst installieren
COPY packages/rotary_core /app/packages/rotary_core
COPY backend_a/pyproject.toml /app/

RUN pip install --no-cache-dir -e /app/packages/rotary_core
RUN pip install --no-cache-dir -e /app

COPY backend_a/src /app/src

CMD ["sh", "-c", "alembic upgrade head && uvicorn rotary_archiv.main:app \
     --host 0.0.0.0 --port ${BACKEND_PORT} --workers 2"]
```

### backend_b/Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/rotary_core /app/packages/rotary_core
COPY backend_b/pyproject.toml /app/

RUN pip install --no-cache-dir -e /app/packages/rotary_core
RUN pip install --no-cache-dir -e /app

COPY backend_b/src /app/src

CMD ["sh", "-c", "uvicorn rotary_public.main:app \
     --host 0.0.0.0 --port ${BACKEND_PORT} --workers 2"]
```

> **Hinweis:** `alembic upgrade head` läuft **nur** im Backend A Start-Command —
> Backend B hat keine Schema-Hoheit (konsistent mit T2-Architekturentscheidung).

---

## Fuseki-Dataset-Konfiguration

### fuseki/config/rotary.ttl

```turtle
@prefix fuseki:  <http://jena.apache.org/fuseki#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ja:      <http://jena.hpl.hp.com/2005/11/Assembler#> .
@prefix tdb2:    <http://jena.apache.org/2016/tdb#> .

<#rotary_dataset> rdf:type tdb2:DatasetTDB2 ;
    tdb2:location  "/fuseki/databases/rotary" .

<#rotary_service> rdf:type fuseki:Service ;
    rdfs:label                   "Rotary Archiv SPARQL" ;
    fuseki:name                  "rotary" ;
    fuseki:serviceQuery          "sparql" ;
    fuseki:serviceQuery          "query" ;
    fuseki:serviceUpdate         "update" ;
    fuseki:serviceUpload         "upload" ;
    fuseki:serviceReadGraphStore "get" ;
    fuseki:dataset               <#rotary_dataset> .
```

> **TDB2 statt In-Memory:** TDB2 persistiert auf Disk (`fuseki_data`-Volume)
> und überlebt Container-Neustarts. Das ist die Produktions-Einstellung.

---

*Nächste Datei: T3-update-prozess.md*
