#!/usr/bin/env bash
# Download deploy assets from scripts/deploy/assets.lock (Google Drive), verify sha256, place them.
#
# Idempotent: a file whose sha256 already matches is not downloaded again; a tar asset is not
# re-extracted while <dest>/.asset-<name>.sha256 matches. Any mismatch after download → exit 1.
#
# Usage:
#   scripts/deploy/fetch_assets.sh            # all assets
#   scripts/deploy/fetch_assets.sh --check    # only report what is missing / stale, no downloads
#
# Env: ASSETS_LOCK (default scripts/deploy/assets.lock), ASSETS_CACHE (default data/tmp/deploy).
# Needs: curl, sha256sum, tar, zstd  (Ubuntu: sudo apt-get install -y curl zstd).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

LOCK="${ASSETS_LOCK:-scripts/deploy/assets.lock}"
CACHE="${ASSETS_CACHE:-data/tmp/deploy}"
DRIVE_URL="https://drive.usercontent.google.com/download?export=download&confirm=t&id="
CHECK_ONLY=0

case "${1:-}" in
  --check) CHECK_ONLY=1 ;;
  "") ;;
  -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
  *) echo "unknown arg: $1" >&2; exit 2 ;;
esac

for tool in curl sha256sum tar zstd; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool (sudo apt-get install -y $tool)" >&2; exit 1; }
done

sha_of() { sha256sum "$1" | cut -d' ' -f1; }
sha_ok() { [[ -f "$1" ]] && [[ "$(sha_of "$1")" == "$2" ]]; }

# download <drive_id> <sha256> <out>
download() {
  local id="$1" sha="$2" out="$3"
  if sha_ok "$out" "$sha"; then
    echo "  ok      $out"
    return 0
  fi
  if (( CHECK_ONLY )); then
    echo "  MISSING $out"
    STALE=1
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  echo "  get     $out"
  curl -fL --retry 5 --retry-all-errors --retry-delay 5 --connect-timeout 30 \
    --progress-bar -o "$out.part" "${DRIVE_URL}${id}"
  local got
  got="$(sha_of "$out.part")"
  if [[ "$got" != "$sha" ]]; then
    echo "sha256 mismatch for $out: expected $sha, got $got (left as $out.part;" \
         "check Drive sharing / id in $LOCK)" >&2
    exit 1
  fi
  mv -f "$out.part" "$out"
}

STALE=0
echo "assets from $LOCK"
while read -r name id sha kind dest; do
  [[ -z "${name:-}" || "$name" == \#* ]] && continue
  case "$kind" in
    file)
      download "$id" "$sha" "$dest/$name"
      ;;
    archive)
      download "$id" "$sha" "$CACHE/$name"
      ;;
    tar)
      download "$id" "$sha" "$CACHE/$name"
      marker="$dest/.asset-$name.sha256"
      if [[ -f "$marker" && "$(cat "$marker")" == "$sha" ]]; then
        echo "  ok      $dest/ (extracted $name)"
      elif (( CHECK_ONLY )); then
        echo "  STALE   $dest/ (not extracted from $name)"
        STALE=1
      else
        mkdir -p "$dest"
        echo "  extract $name → $dest/"
        tar -I zstd -xf "$CACHE/$name" -C "$dest"
        echo "$sha" > "$marker"
      fi
      ;;
    *)
      echo "unknown kind '$kind' for $name in $LOCK" >&2
      exit 1
      ;;
  esac
done < "$LOCK"

if (( CHECK_ONLY && STALE )); then
  echo "some assets are missing or stale — run scripts/deploy/fetch_assets.sh"
  exit 1
fi
echo "assets ready"
