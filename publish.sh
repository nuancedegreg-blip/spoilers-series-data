#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "[info] lancement generation automatique"
python3 generate_spoilers.py "$@"

TARGET_JSON="${SPOILERS_JSON_PATH:-}"
if [[ -z "$TARGET_JSON" ]]; then
  if [[ -f "$ROOT_DIR/spoilers.json" ]]; then
    TARGET_JSON="$ROOT_DIR/spoilers.json"
  else
    TARGET_JSON="$ROOT_DIR/Spoilers Séries FR/Spoilers Séries FR/spoilers.json"
  fi
fi

LOG_JSON="$ROOT_DIR/.internal_sources.json"

if git diff --quiet -- "$TARGET_JSON" "$LOG_JSON"; then
  echo "[info] aucun changement a publier"
  exit 0
fi

git config user.name "${GIT_AUTHOR_NAME:-spoilers-bot}"
git config user.email "${GIT_AUTHOR_EMAIL:-spoilers-bot@users.noreply.github.com}"

git add "$TARGET_JSON" "$LOG_JSON"
git commit -m "Update spoilers data $(date -u +%F-%H%M)"
git push

echo "[info] publication terminee"
