#!/usr/bin/env bash
# Database backup — pg_dump, gzip, 30-day rotation
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="db_backup_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "=== Creating backup: ${FILENAME} ==="
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-triho_user}" "${POSTGRES_DB:-triho_db}" \
    | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "Backup saved: ${BACKUP_DIR}/${FILENAME}"

echo "=== Removing backups older than 30 days ==="
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "=== Backup complete ==="
