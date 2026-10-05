#!/usr/bin/env bash
# Create the VPS Postgres volume from data/tmp/deploy/pgdata.tar.zst (raw PG data dir) and start db.
#
# - no volume yet               → create + extract (first install)
# - volume restored from this same archive (marker sha256 matches) → nothing to do
# - volume with other data      → needs --yes: copies it to <volume>_bak_<timestamp> first,
#                                 then replaces the contents (rollback = point VINE_PG_VOLUME at the backup)
# Extraction uses the db image pinned in docker-compose.vps.yml (same PG/pgvector build as the archive).
# After start: prints the wine count and checks every DB slug has static/wines/<slug>.webp.
#
# Usage:
#   scripts/deploy/restore_db_volume.sh [--yes] [--force]
#     --force  re-extract even if the marker says this archive is already restored (implies a replace)
#
# Env: VINE_PG_VOLUME (default from .env or vine_vps_pgdata), COMPOSE_FILE (default docker-compose.vps.yml),
#      PGDATA_ARCHIVE (default data/tmp/deploy/pgdata.tar.zst).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

YES=0
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) YES=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

env_value() { [[ -f .env ]] && sed -n "s/^$1=//p" .env | tail -n1 | tr -d "\"'" || true; }

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.vps.yml}"
VOLUME="${VINE_PG_VOLUME:-$(env_value VINE_PG_VOLUME)}"
VOLUME="${VOLUME:-vine_vps_pgdata}"
ARCHIVE="${PGDATA_ARCHIVE:-data/tmp/deploy/pgdata.tar.zst}"
MARKER="data/tmp/deploy/state/${VOLUME}.restored"

dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

for tool in docker zstd sha256sum; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 1; }
done
[[ -f "$ARCHIVE" ]] || { echo "no $ARCHIVE — run scripts/deploy/fetch_assets.sh first" >&2; exit 1; }

DB_IMAGE="$(dc config --images | grep -m1 'pgvector/')"
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | cut -d' ' -f1)"
echo "volume=$VOLUME image=$DB_IMAGE archive=$ARCHIVE"

if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  if [[ -f "$MARKER" && "$(cat "$MARKER")" == "$ARCHIVE_SHA" && "$FORCE" == 0 ]]; then
    echo "volume already restored from this archive — skip"
    dc up -d db
    exit 0
  fi
  if (( ! YES )); then
    echo "volume $VOLUME exists with other data; rerun with --yes to back it up and replace it" >&2
    exit 3
  fi
  dc stop app db >/dev/null 2>&1 || true
  BACKUP="${VOLUME}_bak_$(date +%Y%m%d_%H%M%S)"
  echo "backup $VOLUME → $BACKUP"
  docker volume create "$BACKUP" >/dev/null
  docker run --rm -v "$VOLUME":/from:ro -v "$BACKUP":/to --entrypoint sh "$DB_IMAGE" \
    -c 'cp -a /from/. /to/'
  docker run --rm -v "$VOLUME":/data --entrypoint sh "$DB_IMAGE" \
    -c 'find /data -mindepth 1 -delete'
else
  echo "create volume $VOLUME"
  docker volume create "$VOLUME" >/dev/null
fi

echo "extract archive into $VOLUME"
zstd -dc "$ARCHIVE" | docker run --rm -i -v "$VOLUME":/data --entrypoint tar "$DB_IMAGE" \
  --numeric-owner -C /data -xf -

dc up -d db
for _ in $(seq 1 60); do
  dc exec -T db pg_isready -U vine -d vine -q 2>/dev/null && break
  sleep 2
done
dc exec -T db pg_isready -U vine -d vine -q || { echo "db did not become ready" >&2; exit 1; }

ROWS="$(dc exec -T db psql -U vine -d vine -Atc 'select count(*) from wines')"
echo "wines in DB: $ROWS"
if compgen -G "static/wines/*.webp" >/dev/null; then
  MISSING="$(comm -23 \
    <(dc exec -T db psql -U vine -d vine -Atc 'select slug from wines' | sort) \
    <(find static/wines -maxdepth 1 -name '*.webp' -printf '%f\n' | sed 's/\.webp$//' | sort) | wc -l)"
  echo "DB slugs without static/wines/<slug>.webp: $MISSING"
else
  echo "static/wines is empty — run scripts/deploy/fetch_assets.sh (images.tar.zst)"
fi

mkdir -p "$(dirname "$MARKER")"
echo "$ARCHIVE_SHA" > "$MARKER"
echo "db volume ready (start the app: docker compose -f $COMPOSE_FILE up -d)"
