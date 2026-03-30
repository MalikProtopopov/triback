#!/usr/bin/env bash
# Быстрый перезапуск API и воркера на prod без pull/build/migrate.
# Запускать на сервере из корня репозитория: ./scripts/restart-backend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

set -a
# shellcheck source=/dev/null
source .env.prod
set +a

COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Restarting backend + worker ==="
docker compose -f "$COMPOSE_FILE" restart backend worker

echo "=== Restarting nginx (обновить upstream к backend) ==="
docker compose -f "$COMPOSE_FILE" restart nginx

echo "=== Health check ==="
sleep 3
if curl -sf "https://${API_DOMAIN}/api/v1/health" > /dev/null 2>&1; then
  echo "Health check PASSED"
else
  echo "WARNING: Health check failed — см. логи: docker compose -f $COMPOSE_FILE logs --tail=100 backend"
fi

echo "=== Restart complete ==="
