#!/usr/bin/env bash
# Daily database backup: run from cron, e.g. "30 2 * * * /opt/nexora/scripts/backup_db.sh /var/backups/nexora"
set -euo pipefail
DEST="${1:?usage: backup_db.sh <dest-dir>}"
mkdir -p "$DEST"
STAMP="$(date +%Y%m%d-%H%M%S)"
pg_dump -h "${PGHOST:-localhost}" -U "${PGUSER:-nexora}" "${PGDATABASE:-nexora}" | gzip > "$DEST/nexora-$STAMP.sql.gz"
find "$DEST" -name 'nexora-*.sql.gz' -mtime +30 -delete
