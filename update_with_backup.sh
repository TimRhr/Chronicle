#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$REPO_DIR/backups"
mkdir -p "$BACKUP_DIR"

log() { printf '[update] %s\n' "$*"; }

log "Stopping containers before backup…"
docker compose down

log "Ensuring data directory ownership (postgres=999, uploads=$USER)…"
sudo chown -R 999:999 data/postgres || true
sudo chown -R "$USER":"$USER" data/uploads || true

log "Starting database container for backup…"
docker compose up -d db
sleep 5

log "Creating database dump (chronicle-db → backups/db-${TIMESTAMP}.sql)…"
if docker compose ps db >/dev/null 2>&1; then
  docker compose exec -T db pg_dump -U chronicle -d chronicle > "$BACKUP_DIR/db-${TIMESTAMP}.sql"
else
  log "Warning: db container not running, skipping pg_dump"
fi

log "Archiving uploads → backups/uploads-${TIMESTAMP}.tar.gz…"
sudo tar -czf "$BACKUP_DIR/uploads-${TIMESTAMP}.tar.gz" -C data uploads

log "Archiving postgres data → backups/postgres-${TIMESTAMP}.tar.gz…"
sudo tar -czf "$BACKUP_DIR/postgres-${TIMESTAMP}.tar.gz" -C data postgres

STASH_NAME=""
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  STASH_NAME="auto-update-${TIMESTAMP}"
  log "Stashing local changes (${STASH_NAME})…"
  git stash push -u -m "${STASH_NAME}"
fi

log "Fetching & fast-forwarding to origin/main…"
git fetch --all --prune
git pull --ff-only

log "Rebuilding containers…"
docker compose up -d --build

log "Stopping containers to restore backup state…"
docker compose stop web >/dev/null 2>&1 || true
docker compose stop db >/dev/null 2>&1 || true

log "Restoring uploads from backup…"
sudo rm -rf data/uploads
sudo tar -xzf "$BACKUP_DIR/uploads-${TIMESTAMP}.tar.gz" -C data
sudo chown -R "$USER":"$USER" data/uploads

log "Restoring postgres data directory from backup…"
sudo rm -rf data/postgres
sudo tar -xzf "$BACKUP_DIR/postgres-${TIMESTAMP}.tar.gz" -C data
sudo chown -R 999:999 data/postgres

log "Starting database container…"
docker compose up -d db

log "Ensuring chronicle database is recreated from SQL dump…"
docker compose exec db dropdb -U chronicle chronicle >/dev/null 2>&1 || true
docker compose exec db createdb -U chronicle chronicle
docker compose exec -T db psql -U chronicle -d chronicle < "$BACKUP_DIR/db-${TIMESTAMP}.sql"

log "Starting remaining containers…"
docker compose up -d

if [ -n "$STASH_NAME" ]; then
  log "Restoring stashed changes (${STASH_NAME})…"
  git stash pop || log "Warning: stash pop had conflicts, stash kept"
fi

log "Update complete. Backups stored in $BACKUP_DIR."
