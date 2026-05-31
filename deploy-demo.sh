#!/usr/bin/env bash
# RotaryArchiv – Demonstrator-Deployment
# Baut das Frontend und überträgt es per rsync auf die NAS.
# Konfiguration via .env.deploy (nicht in Git!)

set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-rotary}"
DEPLOY_HOST="${DEPLOY_HOST:-nas}"
DEPLOY_PATH="${DEPLOY_PATH:-/volume1/docker/rotary-archive/frontend-b/dist}"

echo "▶ Build..."
npm run build

echo "▶ Deploy zu ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}..."
rsync -avz --delete dist/ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

echo "▶ Nginx reload..."
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "docker exec rotary-nginx nginx -s reload"

echo "✅ Deployment abgeschlossen."
