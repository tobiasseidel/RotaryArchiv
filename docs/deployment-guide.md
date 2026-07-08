# Deployment Guide: RotaryArchiv + litellm

## Überblick

Diese Anleitung beschreibt die Installation des RotaryArchiv mit MCP Server und litellm Gateway auf einer NAS (Synology/QNAP) mit Portainer.

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                        NAS (Docker)                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ frontend │  │ backend  │  │  worker  │  │   ollama │   │
│  │  (nginx) │  │ (FastAPI)│  │   (OCR)  │  │  (LLM)   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │         │
│       └──────────────┴──────────────┴──────────────┘         │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────────────┐  │
│  │                    Docker Network                     │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌──────────┐  ┌─────────┴────────┐                         │
│  │ litellm  │←→│    mcp-server    │                         │
│  │ (Gateway)│  │ (RotaryArchiv)   │                         │
│  └──────────┘  └──────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Voraussetzungen

- Docker + Docker Compose auf der NAS
- Portainer (optional, für Web-UI)
- Ollama läuft auf der NAS (Port 11434)
- Git zum Klonen des Repos

## Installation

### 1. Repository klonen

```bash
ssh nas-user@nas-ip
cd /Volume1
git clone <repo-url> RotaryArchiv
cd RotaryArchiv
```

### 2. Environment-Dateien erstellen

```bash
# .env.docker für Docker-Umgebungsvariablen
cat > .env.docker << 'EOF'
# Database
SQLITE_PATH=/app/data/rotary_archiv.db

# Pfade
DATA_DIR=/Volume1/RotaryArchiv
DOCUMENTS_PATH=/app/data/documents
TRIPLESTORE_PATH=/app/data/triplestore.ttl

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_VISION_MODEL=deepseek-ocr:latest
OLLAMA_GPT_MODEL=gpt-oss:20b
OLLAMA_TIMEOUT_SECONDS=7200

# Ports
BACKEND_PORT=8085
FRONTEND_PORT=8080
MCP_PORT=8001
LITELLM_PORT=4000

# Debug
DEBUG=True
EOF
```

### 3. Docker Compose starten

```bash
# Alles starten
docker compose up -d

# Logs beobachten
docker compose logs -f

# Nur MCP + litellm starten
docker compose up -d mcp-server litellm
```

### 4. Services prüfen

```bash
# Health Checks
curl http://localhost:8085/health        # Backend
curl http://localhost:8001/health        # MCP Server
curl http://localhost:4000/health        # litellm

# MCP Server Test
curl http://localhost:8001/              # Server Info

# litellm Models
curl http://localhost:4000/v1/models     # Alle Modelle
```

## MCP Server Testen

### SSE Endpoint testen

```bash
# Server Info
curl http://localhost:8001/

# Health
curl http://localhost:8001/health

# Tools auflisten (via POST)
curl -X POST http://localhost:8001/messages \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Mit litellm testen

```bash
# litellm Starten (lokal zum Testen)
pip install litellm
litellm --config litellm_config.yaml

# Modelle prüfen
curl http://localhost:4000/v1/models

# Tool aufrufen
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-local",
    "messages": [{"role": "user", "content": "Liste alle Dokumente"}],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}]
  }'
```

## Agenten nutzen

### Recherche-Agent

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-local",
    "messages": [
      {"role": "system", "content": "Du bist ein Archiv-Rechercheur. Durchsuche das Archiv und liefere Quellenangaben."},
      {"role": "user", "content": "Finde alle Clubvorstände der 1930er Jahre"}
    ],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}]
  }'
```

### OCR-Agent

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama-local",
    "messages": [
      {"role": "system", "content": "Du steuerst OCR-Workflows. Starte und überwache OCR für Dokumente."},
      {"role": "user", "content": "Zeige den Status aller OCR-Jobs"}
    ],
    "tools": [{"type": "mcp", "server_url": "litellm_proxy", "server_label": "archiv"}]
  }'
```

## Troubleshooting

### MCP Server startet nicht

```bash
# Logs prüfen
docker compose logs mcp-server

# Manuell testen
docker compose exec mcp-server python -c "from src.rotary_archiv.mcp.sse_server import app; print('OK')"

# Port prüfen
netstat -tlnp | grep 8001
```

### litellm kann MCP nicht erreichen

```bash
# Network prüfen
docker network ls
docker network inspect rotaryarchiv_default

# MCP Server erreichbar?
docker compose exec litellm curl http://mcp-server:8001/health

# litellm Logs
docker compose logs litellm
```

### Ollama nicht erreichbar

```bash
# Ollama Status
curl http://localhost:11434/api/tags

# Von Docker aus
docker compose exec litellm curl http://host.docker.internal:11434/api/tags
```

## Updates

```bash
# Code updaten
git pull

# Containers neu bauen
docker compose build --no-cache

# Neustart
docker compose up -d

# Logs
docker compose logs -f
```

## Port-Übersicht

| Service | Port | Zweck |
|---------|------|-------|
| Frontend | 8080 | Web-UI |
| Backend | 8085 | FastAPI API |
| MCP Server | 8001 | MCP SSE Endpoint |
| litellm | 4000 | LLM Gateway |
| Ollama | 11434 | LLM inference |

## Sicherheit

### Network-Isolation

Die Services laufen in einem isolierten Docker-Network. Für externen Zugriff:

```bash
# Nur für internes Netzwerk
# Externe Ports nur bei Bedarf öffnen

# litellm mit Master Key
environment:
  - LITELLM_MASTER_KEY=your-secret-key
```

### API Keys

```bash
# In .env.docker
LITELLM_MASTER_KEY=sk-your-secret-key
```

Dann litellm Config ergänzen:

```yaml
litellm_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```
