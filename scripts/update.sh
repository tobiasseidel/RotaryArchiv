#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
FRONTEND_DIR="${PROJECT_DIR}/rotary-frontend"
LOG_DIR="${PROJECT_DIR}/logs"

mkdir -p "${LOG_DIR}"

echo "$(date): Building frontend..." | tee -a "${LOG_DIR}/update.log"

cd "${FRONTEND_DIR}"
npm ci && npm run build 2>&1 | tee -a "${LOG_DIR}/update.log"

echo "$(date): Frontend build complete." | tee -a "${LOG_DIR}/update.log"
echo "Push to Git, then redeploy in Portainer."
