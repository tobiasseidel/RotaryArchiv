# T3-update-prozess.md

> **Thread:** T3 Auth & Deployment  
> **Version:** 1.0 — 2026-05-02  
> **Abhängigkeiten:** T3-docker-compose.md  
> **Input für:** T6 Coding, laufender Betrieb
>
> **⚠️ Aktualisiert durch T9-dev-strategie.md:** Die Update/Rollback-Skripte
> setzen `backend_a` und `backend_b` als separate Container voraus.
> Laut T9 wird in Phase 1 nur **ein Backend-Container** deployed.
> Diese Skripte werden erst beim Split in Produktion benötigt.
> Siehe [T9-dev-strategie.md](T9-dev-strategie.md).

---

## Überblick

Da das Projekt auf einer privaten NAS ohne CI/CD-Pipeline läuft, ist der
Update-Prozess bewusst einfach gehalten: Shell-Skripte, die manuell oder
per Cron ausgeführt werden. Kein Kubernetes, kein GitHub Actions — aber
trotzdem reproduzierbar und mit Rollback-Option.

---

## Strategie: Blue-Green mit Docker Compose

Weil nur ein Backend B öffentlich exponiert ist und der NAS-Speicher
begrenzt ist, wird ein vereinfachtes **Rolling-Update** gefahren:

1. Neues Image bauen (im Hintergrund)
2. Container kurz stoppen, neuen starten
3. Bei Fehler: altes Image wiederherstellen

Downtime: ca. **10–30 Sekunden** (akzeptabel für ein Archiv-Projekt).

---

## Update-Skript: `scripts/update.sh`

```bash
#!/usr/bin/env bash
# scripts/update.sh — Produktions-Update für RotaryArchiv
# Aufruf: ./scripts/update.sh [backend_a|backend_b|all|frontend]

set -euo pipefail

PROJECT_DIR="/volume1/docker/rotary-archiv"
COMPOSE="docker compose -f ${PROJECT_DIR}/docker-compose.yml"
LOG="${PROJECT_DIR}/logs/update_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "${PROJECT_DIR}/logs"
exec > >(tee -a "$LOG") 2>&1

echo "═══════════════════════════════════════════════"
echo " RotaryArchiv Update — $(date)"
echo "═══════════════════════════════════════════════"

TARGET="${1:-all}"

# ─────────────────────────────────────────────────
# Schritt 1: Git Pull (wenn Repo auf NAS liegt)
# ─────────────────────────────────────────────────
echo "[1/5] Git Pull..."
cd "$PROJECT_DIR"
git pull --rebase origin main

# ─────────────────────────────────────────────────
# Schritt 2: Altes Image als Fallback taggen
# ─────────────────────────────────────────────────
echo "[2/5] Sichere alte Images..."
if [[ "$TARGET" == "backend_a" || "$TARGET" == "all" ]]; then
  docker tag rotary-archiv-backend_a:latest rotary-archiv-backend_a:rollback || true
fi
if [[ "$TARGET" == "backend_b" || "$TARGET" == "all" ]]; then
  docker tag rotary-archiv-backend_b:latest rotary-archiv-backend_b:rollback || true
fi

# ─────────────────────────────────────────────────
# Schritt 3: Neue Images bauen
# ─────────────────────────────────────────────────
echo "[3/5] Baue neue Images..."
if [[ "$TARGET" == "backend_a" || "$TARGET" == "all" ]]; then
  $COMPOSE build --no-cache backend_a
fi
if [[ "$TARGET" == "backend_b" || "$TARGET" == "all" ]]; then
  $COMPOSE build --no-cache backend_b
fi
if [[ "$TARGET" == "frontend" ]]; then
  echo "  → Frontend-Build (npm)..."
  cd "${PROJECT_DIR}/frontend_b"
  npm ci && npm run build
  cd "$PROJECT_DIR"
fi

# ─────────────────────────────────────────────────
# Schritt 4: Migrationen (nur wenn Backend A betroffen)
# ─────────────────────────────────────────────────
if [[ "$TARGET" == "backend_a" || "$TARGET" == "all" ]]; then
  echo "[4/5] Alembic-Migrationen..."
  # Starte temporären Backend-A-Container nur für Migrationen
  $COMPOSE run --rm backend_a alembic upgrade head
fi

# ─────────────────────────────────────────────────
# Schritt 5: Container neu starten (rolling)
# ─────────────────────────────────────────────────
echo "[5/5] Container-Restart..."
if [[ "$TARGET" == "all" ]]; then
  $COMPOSE up -d --no-deps backend_a backend_b nginx
elif [[ "$TARGET" == "frontend" ]]; then
  $COMPOSE exec nginx nginx -s reload
else
  $COMPOSE up -d --no-deps "$TARGET"
fi

echo ""
echo "✅ Update abgeschlossen: $(date)"
echo "   Log: $LOG"
```

---

## Rollback-Skript: `scripts/rollback.sh`

```bash
#!/usr/bin/env bash
# scripts/rollback.sh — Zurück zum letzten stabilen Image
set -euo pipefail

PROJECT_DIR="/volume1/docker/rotary-archiv"
COMPOSE="docker compose -f ${PROJECT_DIR}/docker-compose.yml"

echo "⚠️  Rollback wird ausgeführt..."

TARGET="${1:-all}"

if [[ "$TARGET" == "backend_a" || "$TARGET" == "all" ]]; then
  docker tag rotary-archiv-backend_a:rollback rotary-archiv-backend_a:latest
  $COMPOSE up -d --no-deps backend_a
fi

if [[ "$TARGET" == "backend_b" || "$TARGET" == "all" ]]; then
  docker tag rotary-archiv-backend_b:rollback rotary-archiv-backend_b:latest
  $COMPOSE up -d --no-deps backend_b
fi

echo "✅ Rollback abgeschlossen."
```

---

## Datenbank-Backup: `scripts/backup-db.sh`

```bash
#!/usr/bin/env bash
# scripts/backup-db.sh — Tägliches PostgreSQL-Backup
# Empfehlung: per Cron um 03:00 Uhr ausführen
set -euo pipefail

PROJECT_DIR="/volume1/docker/rotary-archiv"
BACKUP_DIR="/volume1/backups/rotary-archiv"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Backup direkt aus laufendem Container
docker exec rotary_postgres pg_dump \
  -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "$FILENAME"

echo "✅ Backup: $FILENAME ($(du -sh "$FILENAME" | cut -f1))"

# Alte Backups löschen (älter als 30 Tage)
find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +30 -delete
echo "🧹 Alte Backups bereinigt."
```

### Crontab-Einträge (NAS-Cron)

```cron
# Täglich 03:00 — Datenbankbackup
0 3 * * * /volume1/docker/rotary-archiv/scripts/backup-db.sh >> /volume1/logs/rotary-backup.log 2>&1

# TLS-Zertifikat wird durch Certbot-Container automatisch erneuert (kein Cron nötig)
```

---

## Fuseki-Datensicherung

Fuseki-Daten liegen im Docker-Volume `fuseki_data`. Backup:

```bash
# Fuseki TDB2-Daten sichern (bei gestopptem Fuseki-Container für Konsistenz)
docker stop rotary_fuseki
docker run --rm \
  -v rotary-archiv_fuseki_data:/source:ro \
  -v /volume1/backups/fuseki:/backup \
  alpine tar czf /backup/fuseki_$(date +%Y%m%d).tar.gz -C /source .
docker start rotary_fuseki
```

---

## Healthcheck nach Update

```bash
#!/usr/bin/env bash
# scripts/healthcheck.sh — Schnelltest nach jedem Update
set -euo pipefail

source /volume1/docker/rotary-archiv/.env

BASE="https://${ROTARY_DOMAIN}"

check() {
  local url="$1"
  local expected="$2"
  local result
  result=$(curl -sf --max-time 5 "$url" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$expected','MISSING'))" 2>/dev/null || echo "FAIL")
  if [[ "$result" == "FAIL" || "$result" == "MISSING" ]]; then
    echo "❌ $url — erwartet: $expected"
    return 1
  fi
  echo "✅ $url — $expected: $result"
}

echo "── Health Checks nach Update ──────────────────"
check "${BASE}/api/v1/stats"    "persons_public"
check "${BASE}/health"          "ok" || true   # plain-text, kein JSON
echo "───────────────────────────────────────────────"
```

---

## Portainer-Integration

Da Portainer bereits im Einsatz ist, können Updates alternativ über
die Portainer-Web-UI ausgeführt werden:

1. **Stacks → rotary-archiv → Editor** — docker-compose.yml bearbeiten
2. **Update the stack** — Portainer führt `docker compose up -d` aus
3. Container-Logs live in **Containers → [Name] → Logs** einsehbar

Empfehlung: Shell-Skripte für Routine-Updates, Portainer für Debugging
und manuelle Eingriffe.

---

*Nächste Datei: T3-auth-konzept.md (Phase 2)*
