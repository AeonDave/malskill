#!/bin/sh
# Create a new skill scaffold from a learning theme without Python.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SKILL_NAME=""
OUTPUT_DIR="."
LEARNING_ID="LRN-YYYYMMDD-XXX"
DATE_HINT=$(date -u +"%Y-%m-%d" 2>/dev/null || date +"%Y-%m-%d")
SOURCE_FILE=""
ENTRY_ID=""
RESOURCES=""
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --learning-id) LEARNING_ID="$2"; shift 2 ;;
    --date-hint) DATE_HINT="$2"; shift 2 ;;
    --source-file) SOURCE_FILE="$2"; shift 2 ;;
    --entry-id) ENTRY_ID="$2"; shift 2 ;;
    --resources) RESOURCES="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h)
      echo "Usage: extract_skill.sh [skill-name] [--source-file FILE --entry-id ID] [--output-dir DIR] [--resources refs,scripts] [--dry-run]"
      exit 0
      ;;
    *)
      if [ -z "$SKILL_NAME" ]; then
        SKILL_NAME="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        exit 1
      fi
      ;;
  esac
done

# --- helpers ---------------------------------------------------------------

# Extract a ### section body from the entry block identified by ENTRY_ID.
extract_entry_section() {
  section_name="$1"
  awk -v id="$ENTRY_ID" -v section="$section_name" '
    BEGIN { in_block=0; in_section=0 }
    $0 ~ "^## \\[" id "\\]" { in_block=1; next }
    in_block && /^## \[/ { exit }
    in_block && $0 == "### " section { in_section=1; next }
    in_section && /^### / { exit }
    in_section { print }
  ' "$SOURCE_FILE" | sed '/^[[:space:]]*$/d'
}

# Return first non-empty line from the first matching section.
first_line_of() {
  for s in "$@"; do
    line=$(extract_entry_section "$s" | head -n 1)
    [ -n "$line" ] && { printf '%s' "$line"; return; }
  done
}

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/-\{2,\}/-/g; s/^-//; s/-$//'
}

title_case() {
  printf '%s' "$1" | awk -F- '{ for (i = 1; i <= NF; i++) { $i = toupper(substr($i,1,1)) tolower(substr($i,2)) } print }'
}

# Truncate to first sentence.
first_sentence() {
  printf '%s' "$1" | sed 's/\([.!?]\) .*/\1/'
}

# --- infer values from source entry ----------------------------------------

if [ -n "$SOURCE_FILE" ] && [ -n "$ENTRY_ID" ]; then
  summary=$(first_line_of "Summary" "Requested Capability")
  [ -n "$summary" ] || summary="Captured reusable workflow from learning $ENTRY_ID"
  background=$(first_line_of "Details" "Error" "User Context" "Context")
  [ -n "$background" ] || background="$summary"
  suggested_action=$(first_line_of "Suggested Action" "Suggested Fix" "Suggested Implementation")
  [ -n "$suggested_action" ] || suggested_action="Review the original learning and turn it into repeatable, validated steps."
  [ -n "$SKILL_NAME" ] || SKILL_NAME=$(slugify "$summary")
  LEARNING_ID="$ENTRY_ID"
else
  summary="Captured reusable workflow"
  background="$summary"
  suggested_action="Review the original learning and turn it into repeatable, validated steps."
fi

[ -n "$SKILL_NAME" ] || { echo "Skill name is required" >&2; exit 1; }
printf '%s' "$SKILL_NAME" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$' || {
  echo "Invalid skill name: $SKILL_NAME (must be lowercase, hyphens, digits)" >&2
  exit 1
}

TARGET_PATH="$OUTPUT_DIR/$SKILL_NAME"

# Build description: first sentence + standard suffix, capped at 200 chars.
desc_summary=$(first_sentence "$summary")
DESCRIPTION="$desc_summary. Use when the same non-obvious problem or workflow appears again."
TITLE=$(title_case "$SKILL_NAME")
action_sentence=$(printf '%s' "$suggested_action" | tr '\n' ' ' | sed 's/  */ /g')
[ -n "$action_sentence" ] || action_sentence="Apply the reusable fix, then verify the outcome."

CONTENT=$(cat <<EOF
---
name: $SKILL_NAME
description: "$DESCRIPTION"
---

# $TITLE

$summary

## When to use

- the same non-obvious problem appears again
- the original learning has been validated and should become reusable guidance
- future sessions would benefit from having the workflow pre-written

## Workflow

1. Review the original learning and remove incident-only detail.
2. Capture the reusable checks, commands, and decision points.
3. Apply this rule: $action_sentence
4. Validate the resulting workflow in a fresh task before packaging or broad reuse.

## Background

$background

## Resources

- add \`references/\`, \`assets/\`, or \`scripts/\` only when they clearly improve reuse

## Source

- Learning ID: $LEARNING_ID
- Extraction Date: $DATE_HINT
EOF
)

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Target: $TARGET_PATH"
  echo
  echo "$CONTENT"
  [ -n "$RESOURCES" ] && echo "Resource directories: $RESOURCES"
  exit 0
fi

[ ! -e "$TARGET_PATH" ] || { echo "Target already exists: $TARGET_PATH" >&2; exit 1; }
mkdir -p "$TARGET_PATH"
printf '%s\n' "$CONTENT" > "$TARGET_PATH/SKILL.md"

# Create requested resource directories.
if [ -n "$RESOURCES" ]; then
  IFS=','
  for dir in $RESOURCES; do
    dir=$(printf '%s' "$dir" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -n "$dir" ] && mkdir -p "$TARGET_PATH/$dir"
  done
  unset IFS
fi

echo "Created skill scaffold at $TARGET_PATH"

echo "Created skill scaffold at $TARGET_PATH"
