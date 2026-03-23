#!/bin/sh
# Ensure the .learnings store exists using shipped templates.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ASSETS_DIR="$ROOT_DIR/assets"
STORE_DIR="${1:-.learnings}"

mkdir -p "$STORE_DIR"

copy_if_missing() {
  src="$1"
  dst="$2"
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
  fi
}

copy_if_missing "$ASSETS_DIR/LEARNINGS.md" "$STORE_DIR/LEARNINGS.md"
copy_if_missing "$ASSETS_DIR/ERRORS-template.md" "$STORE_DIR/ERRORS.md"
copy_if_missing "$ASSETS_DIR/FEATURE-REQUESTS-template.md" "$STORE_DIR/FEATURE_REQUESTS.md"

echo "Ensured learning store at $STORE_DIR"
