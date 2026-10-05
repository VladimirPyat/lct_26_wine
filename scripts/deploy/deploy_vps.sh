#!/usr/bin/env bash
# One-command VPS deploy from a cloned repo: assets → DB volume → build/up → health check.
# Prerequisites: Docker + compose plugin, .env (cp .env.vps.example .env and set the API key).
#
# Usage:
#   scripts/deploy/deploy_vps.sh            # first install or update (DB volume restored only if missing)
#   scripts/deploy/deploy_vps.sh --yes      # also allow replacing an existing DB volume (backup kept)
# Args are passed to restore_db_volume.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.vps.yml}"
export COMPOSE_FILE

[[ -f .env ]] || { echo "no .env — cp .env.vps.example .env and fill QWEN_API_KEY" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker not installed (see manuals/deploy_vps.md)" >&2; exit 1; }
docker compose version >/dev/null || { echo "docker compose plugin missing" >&2; exit 1; }

PORT="${VINE_PORT:-$(sed -n 's/^VINE_PORT=//p' .env | tail -n1)}"
PORT="${PORT:-80}"

echo "== 1/4 assets"
scripts/deploy/fetch_assets.sh

echo "== 2/4 database volume"
scripts/deploy/restore_db_volume.sh "$@"

echo "== 3/4 build + start"
docker compose -f "$COMPOSE_FILE" up -d --build

echo "== 4/4 health (http://127.0.0.1:$PORT/health)"
for _ in $(seq 1 90); do
  if BODY="$(curl -fsS "http://127.0.0.1:$PORT/health" 2>/dev/null)"; then
    echo "healthy: $BODY"
    docker compose -f "$COMPOSE_FILE" ps
    exit 0
  fi
  sleep 5
done
echo "app did not become healthy; last logs:" >&2
docker compose -f "$COMPOSE_FILE" logs --tail 80 app >&2
exit 1
