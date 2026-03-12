#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

set -a; source "$PROJECT_DIR/.env.prod"; set +a

COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Requesting certificate for: ${API_DOMAIN} ==="

docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" run --rm certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "$API_DOMAIN" \
    --email "$CERT_EMAIL" \
    --agree-tos \
    --non-interactive

echo "=== Restarting nginx ==="
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" restart nginx

echo "=== SSL initialisation complete ==="
