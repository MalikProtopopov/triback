#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
DOMAINS=(api.triho.ru admin.triho.ru)
CERT_EMAIL="${CERT_EMAIL:?Set CERT_EMAIL env var (e.g. admin@triho.ru)}"

echo "=== Requesting certificates for: ${DOMAINS[*]} ==="

DOMAIN_ARGS=""
for d in "${DOMAINS[@]}"; do
    DOMAIN_ARGS="$DOMAIN_ARGS -d $d"
done

docker compose -f "$COMPOSE_FILE" run --rm certbot certonly \
    --webroot \
    -w /var/www/certbot \
    $DOMAIN_ARGS \
    --email "$CERT_EMAIL" \
    --agree-tos \
    --non-interactive

echo "=== Restarting nginx ==="
docker compose -f "$COMPOSE_FILE" restart nginx

echo "=== SSL initialisation complete ==="
