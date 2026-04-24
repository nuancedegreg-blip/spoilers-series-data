#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

TARGET_JSON="${SPOILERS_JSON_PATH:-}"
if [[ -z "$TARGET_JSON" ]]; then
  if [[ -f "$ROOT_DIR/spoilers.json" ]]; then
    TARGET_JSON="$ROOT_DIR/spoilers.json"
  else
    TARGET_JSON="$ROOT_DIR/Spoilers Séries FR/Spoilers Séries FR/spoilers.json"
  fi
fi

LOG_JSON="$ROOT_DIR/internal_sources.json"
DISCOVERED_JSON="$ROOT_DIR/discovered_sources.json"

echo "[info] root: $ROOT_DIR"
echo "[info] target spoilers: $TARGET_JSON"

if [[ "${SKIP_PIPELINE_STEPS:-0}" != "1" ]]; then
  python3 discover_sources.py
  python3 generate_spoilers.py "$@"
fi

if git diff --quiet -- "$TARGET_JSON"; then
  echo "[info] spoilers.json inchangé, aucun commit ni push"
  exit 0
fi

git config user.name "${GIT_AUTHOR_NAME:-spoilers-bot}"
git config user.email "${GIT_AUTHOR_EMAIL:-spoilers-bot@users.noreply.github.com}"

git add "$TARGET_JSON"
if [[ -f "$LOG_JSON" ]]; then
  git add "$LOG_JSON"
fi
if [[ -f "$DISCOVERED_JSON" ]]; then
  git add "$DISCOVERED_JSON"
fi

git commit -m "Update spoilers data $(date -u +%F-%H%M)"
git push

echo "[info] publication terminée"
