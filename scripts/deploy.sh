#!/usr/bin/env bash
# Zero-downtime deployment script
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Building new images ==="
docker compose -f "$COMPOSE_FILE" build backend

echo "=== Running database migrations ==="
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head

echo "=== Restarting backend + worker (zero-downtime) ==="
docker compose -f "$COMPOSE_FILE" up -d --no-deps --build backend worker

echo "=== Cleaning old images ==="
docker image prune -f

echo "=== Health check ==="
sleep 5
if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "Health check PASSED"
else
    echo "WARNING: Health check failed — check logs with: docker compose -f $COMPOSE_FILE logs backend"
fi

echo "=== Deploy complete ==="
