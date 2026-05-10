#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

if [ -f "${PROJECT_DIR}/.env.host" ]; then
    set -a
    source "${PROJECT_DIR}/.env.host"
    set +a
fi

TARGET="${1:-frontend}"
LOG_DIR="${PROJECT_DIR}/logs"

mkdir -p "${LOG_DIR}"

case "${TARGET}" in
    frontend)
        echo "$(date): Building frontend..." | tee -a "${LOG_DIR}/update.log"

        docker run --rm \
            -v "${PROJECT_DIR}/rotary-frontend":/app \
            -w /app \
            node:20-alpine \
            sh -c "npm ci && npm run build" 2>&1 | tee -a "${LOG_DIR}/update.log"

        echo "$(date): Frontend build complete." | tee -a "${LOG_DIR}/update.log"
        ;;
    *)
        echo "Unknown target: ${TARGET}" | tee -a "${LOG_DIR}/update.log"
        exit 1
        ;;
esac

docker compose -f "${PROJECT_DIR}/docker-compose.yml" restart frontend

# Smoke Test (kommentiert):
# - Startseite lädt
# - Personenprofil zeigt Mock-Daten
# - Dokumentansicht zeigt Scan + Transkription
# - Keine Console-Errors im Browser
