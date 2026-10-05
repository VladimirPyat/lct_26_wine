#!/usr/bin/env bash
# One-command VPS deploy from a cloned repo: assets → DB volume → build/up → health check.
# Prerequisites: Docker + compose plugin, .env (cp .env.vps.example .env and set the API key).
#
# Usage:
#   scripts/deploy/deploy_vps.sh            # first install or update (DB volume restored only if missing)
#   scripts/deploy/deploy_vps.sh --yes      # also allow replacing an existing DB volume (backup kept)
# Args are passed to restore_db_volume.sh.
#
# Health: app directly on 127.0.0.1:VINE_APP_PORT, then through Caddy — HTTPS for VINE_DOMAIN
# (certificate must be valid; first issuance can take up to a couple of minutes) or plain HTTP.
# Exit code != 0 when any check fails (the GitHub workflow then rolls back to the previous commit).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.vps.yml}"
export COMPOSE_FILE

[[ -f .env ]] || { echo "no .env — cp .env.vps.example .env and fill QWEN_API_KEY" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker not installed (see manuals/deploy_vps.md)" >&2; exit 1; }
docker compose version >/dev/null || { echo "docker compose plugin missing" >&2; exit 1; }

env_value() { sed -n "s/^$1=//p" .env | tail -n1 | tr -d "\"'"; }
APP_PORT="${VINE_APP_PORT:-$(env_value VINE_APP_PORT)}"; APP_PORT="${APP_PORT:-8080}"
HTTP_PORT="${VINE_HTTP_PORT:-$(env_value VINE_HTTP_PORT)}"; HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${VINE_HTTPS_PORT:-$(env_value VINE_HTTPS_PORT)}"; HTTPS_PORT="${HTTPS_PORT:-443}"
DOMAIN="${VINE_DOMAIN:-$(env_value VINE_DOMAIN)}"

dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

# wait_ok <attempts> <description> <curl args...>
wait_ok() {
  local attempts="$1" what="$2"; shift 2
  local body
  for _ in $(seq 1 "$attempts"); do
    if body="$(curl -fsS --max-time 10 "$@" 2>/dev/null)"; then
      echo "  ok $what: $body"
      return 0
    fi
    sleep 5
  done
  echo "  FAILED $what" >&2
  return 1
}

echo "== 1/4 assets"
scripts/deploy/fetch_assets.sh

echo "== 2/4 database volume"
scripts/deploy/restore_db_volume.sh "$@"

echo "== 3/4 build + start"
dc up -d --build --remove-orphans

echo "== 4/4 health"
if ! wait_ok 90 "app (127.0.0.1:$APP_PORT)" "http://127.0.0.1:$APP_PORT/health"; then
  dc logs --tail 80 app >&2
  exit 1
fi
if [[ -n "$DOMAIN" ]]; then
  proxy_ok() { wait_ok 36 "https://$DOMAIN (caddy)" --resolve "$DOMAIN:$HTTPS_PORT:127.0.0.1" \
    "https://$DOMAIN:$HTTPS_PORT/health"; }
else
  proxy_ok() { wait_ok 12 "http :$HTTP_PORT (caddy)" "http://127.0.0.1:$HTTP_PORT/health"; }
fi
if ! proxy_ok; then
  dc logs --tail 80 caddy >&2
  exit 1
fi
dc ps
