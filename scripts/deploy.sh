#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

set -a; source .env.prod; set +a

COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Building new images ==="
docker compose -f "$COMPOSE_FILE" build backend

echo "=== Running database migrations ==="
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head

echo "=== Restarting backend + worker ==="
docker compose -f "$COMPOSE_FILE" up -d --no-deps --build backend worker

echo "=== Restarting nginx (refresh proxy to backend) ==="
docker compose -f "$COMPOSE_FILE" restart nginx

echo "=== Cleaning old images ==="
docker image prune -f

echo "=== Health check ==="
sleep 5
if curl -sf "https://${API_DOMAIN}/api/v1/health" > /dev/null 2>&1; then
    echo "Health check PASSED"
else
    echo "WARNING: Health check failed — check logs with: docker compose -f $COMPOSE_FILE logs backend"
fi

echo "=== Deploy complete ==="
