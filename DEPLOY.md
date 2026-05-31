# Deployment auf NAS mit Docker/Portainer

## Voraussetzungen

- Docker auf dem NAS
- Portainer (oder Docker CLI)
- Ollama auf dem NAS-Host (nicht als Container)

## Verzeichnisstruktur auf dem NAS

```
/Volume1/docker/rotary-archiv-repo/   <- Git-Repository klonen
├── docker-compose.yml
├── Dockerfile
├── .env.docker          <- kopieren als .env
├── requirements.txt
├── src/
└── alembic/

/Volume1/RotaryArchiv/data/           <- Daten (existierender Ordner)
├── documents/
├── triplestore.ttl
└── rotary_archiv.db
```

## Schritte

### 1. Repository klonen

```bash
cd /Volume1/docker
git clone <repo-url> rotary-archiv-repo
cd rotary-archiv-repo
```

### 2. Daten

Die Daten liegen bereits auf `/Volume1/RotaryArchiv/data/` - die docker-compose.yml verweist direkt dorthin.

### 3. Environment-Datei vorbereiten

```bash
cp .env.docker .env
```

Falls Ollama auf dem NAS-Host nicht über `host.docker.internal` erreichbar ist:
```bash
# .env anpassen:
OLLAMA_BASE_URL=http://<NAS-IP>:11434
```

### 4. Ollama konfigurieren (falls nötig)

Ollama muss auf dem NAS-Host auf `0.0.0.0:11434` lauschen (nicht nur `localhost`).

Prüfen/ändern in `/etc/systemd/system/ollama.service`:
```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

### 5. Portainer Stack erstellen

1. Portainer öffnen → Stacks → Add stack
2. Repository wählen: Git-URL zum RotaryArchiv-Repo
3. Compose file: `docker-compose.yml`
4. Environment variables: Aus `.env` kopieren oder Datei mitgeben
5. Deploy

## Ports

- Backend: `http://<NAS-IP>:8085`
- API-Docs: `http://<NAS-IP>:8085/docs`

## Logs

```bash
# Container-Logs anzeigen
docker logs rotary_backend
docker logs rotary_worker

# Follow mode
docker logs -f rotary_backend
docker logs -f rotary_worker
```

## Updates

1. Git pull im Repository
2. Images neu bauen:
   ```bash
   docker-compose build
   docker-compose up -d
   ```
3. Oder in Portainer: Stack aktualisieren