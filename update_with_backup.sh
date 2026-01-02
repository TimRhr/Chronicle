#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$(cd "$REPO_DIR/.." && pwd)/backups"
mkdir -p "$BACKUP_DIR"

log() { printf '[update] %s\n' "$*"; }

cleanup_backups() {
  local prefix="$1"
  local extension="$2"
  local files=("$BACKUP_DIR"/${prefix}-*.${extension})

  if (( ${#files[@]} <= 2 )); then
    return
  fi

  IFS=$'\n' files=($(printf '%s\n' "${files[@]}" | sort -r))
  for file in "${files[@]:2}"; do
    rm -f "$file"
  done
}

log "Stopping containers before backup…"
docker compose down

log "Ensuring data directories exist…"
mkdir -p data/postgres data/uploads

log "Detecting postgres UID/GID from db image…"
PG_UID="$(docker compose run --rm db sh -lc 'id -u postgres')"
PG_GID="$(docker compose run --rm db sh -lc 'id -g postgres')"
log "Detected postgres UID/GID: ${PG_UID}:${PG_GID}"

log "Ensuring data directory ownership (postgres=${PG_UID}:${PG_GID}, uploads=$USER)…"
sudo chown -R "${PG_UID}:${PG_GID}" data/postgres || true
sudo chown -R "$USER":"$USER" data/uploads || true

log "Archiving uploads → backups/uploads-${TIMESTAMP}.tar.gz…"
sudo tar -czf "$BACKUP_DIR/uploads-${TIMESTAMP}.tar.gz" -C data uploads
cleanup_backups "uploads" "tar.gz"

log "Archiving postgres data → backups/postgres-${TIMESTAMP}.tar.gz…"
sudo tar -czf "$BACKUP_DIR/postgres-${TIMESTAMP}.tar.gz" -C data postgres
cleanup_backups "postgres" "tar.gz"

log "Starting database container for SQL dump (optional)…"
docker compose up -d db

log "Waiting for database to become ready…"
DB_READY="false"
for _ in {1..30}; do
  if docker compose exec -T db pg_isready -U chronicle -d chronicle >/dev/null 2>&1; then
    DB_READY="true"
    break
  fi
  sleep 1
done

if [ "$DB_READY" = "true" ]; then
  log "Creating database dump → backups/db-${TIMESTAMP}.sql…"
  docker compose exec -T db pg_dump -U chronicle -d chronicle > "$BACKUP_DIR/db-${TIMESTAMP}.sql"
  cleanup_backups "db" "sql"
else
  log "Warning: database is not ready (container may be restarting). Skipping pg_dump; filesystem backup still available."
fi

STASH_NAME=""
if ! git diff --quiet || ! git diff --cached --quiet; then
  STASH_NAME="auto-update-${TIMESTAMP}"
  log "Stashing local changes (${STASH_NAME})…"
  git stash push -m "${STASH_NAME}"
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
sudo chown -R "${PG_UID}:${PG_GID}" data/postgres

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
  git -c status.showUntrackedFiles=no stash pop --quiet || log "Warning: stash pop had conflicts, stash kept"
fi

log "Update complete. Backups stored in $BACKUP_DIR."
