#!/bin/sh
# Append a structured entry to the learning store without Python.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STORE_DIR=".learnings"
KIND=""
SUMMARY=""
CATEGORY="insight"
NAME=""
PRIORITY=""
AREA="workflow"
SOURCE="conversation"
DETAILS=""
SUGGESTED_ACTION=""
RELATED_FILES=""
TAGS=""
SEE_ALSO=""
PATTERN_KEY=""
RECURRENCE_COUNT=""
FIRST_SEEN=""
LAST_SEEN=""
ERROR_TEXT=""
CONTEXT_TEXT=""
SUGGESTED_FIX=""
REPRODUCIBLE="unknown"
REQUESTED_CAPABILITY=""
USER_CONTEXT=""
COMPLEXITY="medium"
SUGGESTED_IMPLEMENTATION=""
FREQUENCY="first_time"
RELATED_FEATURES=""

while [ $# -gt 0 ]; do
  case "$1" in
    --kind) KIND="$2"; shift 2 ;;
    --store-dir) STORE_DIR="$2"; shift 2 ;;
    --summary) SUMMARY="$2"; shift 2 ;;
    --category) CATEGORY="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --priority) PRIORITY="$2"; shift 2 ;;
    --area) AREA="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --details) DETAILS="$2"; shift 2 ;;
    --suggested-action) SUGGESTED_ACTION="$2"; shift 2 ;;
    --related-files) RELATED_FILES="$2"; shift 2 ;;
    --tags) TAGS="$2"; shift 2 ;;
    --see-also) SEE_ALSO="$2"; shift 2 ;;
    --pattern-key) PATTERN_KEY="$2"; shift 2 ;;
    --recurrence-count) RECURRENCE_COUNT="$2"; shift 2 ;;
    --first-seen) FIRST_SEEN="$2"; shift 2 ;;
    --last-seen) LAST_SEEN="$2"; shift 2 ;;
    --error-text) ERROR_TEXT="$2"; shift 2 ;;
    --context) CONTEXT_TEXT="$2"; shift 2 ;;
    --suggested-fix) SUGGESTED_FIX="$2"; shift 2 ;;
    --reproducible) REPRODUCIBLE="$2"; shift 2 ;;
    --requested-capability) REQUESTED_CAPABILITY="$2"; shift 2 ;;
    --user-context) USER_CONTEXT="$2"; shift 2 ;;
    --complexity) COMPLEXITY="$2"; shift 2 ;;
    --suggested-implementation) SUGGESTED_IMPLEMENTATION="$2"; shift 2 ;;
    --frequency) FREQUENCY="$2"; shift 2 ;;
    --related-features) RELATED_FEATURES="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$KIND" ]; then
  echo "--kind is required (learning|error|feature)" >&2
  exit 1
fi

# Enum validation — mirrors Python VALID_* sets.
validate_enum() {
  value="$1"; label="$2"; shift 2
  for valid in "$@"; do
    [ "$value" = "$valid" ] && return 0
  done
  echo "Invalid $label: $value (expected: $*)" >&2
  exit 1
}

validate_enum "$AREA" "area" workflow repo-config docs tooling programming testing knowledge research offensive-tools bof

"$SCRIPT_DIR/ensure_store.sh" "$STORE_DIR" >/dev/null

utc_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ"
}

day_stamp() {
  date -u +"%Y%m%d" 2>/dev/null || date +"%Y%m%d"
}

next_id() {
  prefix="$1"
  file="$2"
  today=$(day_stamp)
  if [ -f "$file" ]; then
    last=$(grep -o "${prefix}-${today}-[0-9][0-9][0-9]" "$file" | awk -F- 'END { if (NF) print $3 + 0; else print 0 }')
  else
    last=0
  fi
  seq=$((last + 1))
  printf '%s-%s-%03d' "$prefix" "$today" "$seq"
}

append_metadata_line() {
  label="$1"
  value="$2"
  if [ -n "$value" ]; then
    printf '%s\n' "- $label: $value"
  fi
}

case "$KIND" in
  learning)
    [ -n "$SUMMARY" ] || { echo "--summary is required" >&2; exit 1; }
    [ -n "$PRIORITY" ] || PRIORITY="medium"
    validate_enum "$PRIORITY" "priority" low medium high critical
    validate_enum "$CATEGORY" "category" correction insight knowledge_gap best_practice
    validate_enum "$SOURCE" "source" conversation user_feedback error review research simplify-and-harden
    FILE="$STORE_DIR/LEARNINGS.md"
    ENTRY_ID=$(next_id "LRN" "$FILE")
    {
      printf '## [%s] %s\n\n' "$ENTRY_ID" "$CATEGORY"
      printf '**Logged**: %s\n' "$(utc_now)"
      printf '**Priority**: %s\n' "$PRIORITY"
      printf '**Status**: pending\n'
      printf '**Area**: %s\n\n' "$AREA"
      printf '### Summary\n%s\n\n' "$SUMMARY"
      printf '### Details\n%s\n\n' "${DETAILS:-N/A}"
      printf '### Suggested Action\n%s\n\n' "${SUGGESTED_ACTION:-N/A}"
      printf '### Metadata\n'
      append_metadata_line "Source" "$SOURCE"
      append_metadata_line "Related Files" "$RELATED_FILES"
      append_metadata_line "Tags" "$TAGS"
      append_metadata_line "See Also" "$SEE_ALSO"
      append_metadata_line "Pattern-Key" "$PATTERN_KEY"
      append_metadata_line "Recurrence-Count" "$RECURRENCE_COUNT"
      append_metadata_line "First-Seen" "$FIRST_SEEN"
      append_metadata_line "Last-Seen" "$LAST_SEEN"
      printf '\n---\n'
    } >> "$FILE"
    ;;
  error)
    [ -n "$NAME" ] || { echo "--name is required" >&2; exit 1; }
    [ -n "$SUMMARY" ] || { echo "--summary is required" >&2; exit 1; }
    [ -n "$ERROR_TEXT" ] || { echo "--error-text is required" >&2; exit 1; }
    [ -n "$PRIORITY" ] || PRIORITY="high"
    validate_enum "$PRIORITY" "priority" low medium high critical
    FILE="$STORE_DIR/ERRORS.md"
    ENTRY_ID=$(next_id "ERR" "$FILE")
    {
      printf '## [%s] %s\n\n' "$ENTRY_ID" "$NAME"
      printf '**Logged**: %s\n' "$(utc_now)"
      printf '**Priority**: %s\n' "$PRIORITY"
      printf '**Status**: pending\n'
      printf '**Area**: %s\n\n' "$AREA"
      printf '### Summary\n%s\n\n' "$SUMMARY"
      printf '### Error\n```text\n%s\n```\n\n' "$ERROR_TEXT"
      printf '### Context\n%s\n\n' "${CONTEXT_TEXT:-N/A}"
      printf '### Suggested Fix\n%s\n\n' "${SUGGESTED_FIX:-N/A}"
      printf '### Metadata\n'
      append_metadata_line "Reproducible" "$REPRODUCIBLE"
      append_metadata_line "Related Files" "$RELATED_FILES"
      append_metadata_line "See Also" "$SEE_ALSO"
      append_metadata_line "Tags" "$TAGS"
      printf '\n---\n'
    } >> "$FILE"
    ;;
  feature)
    [ -n "$NAME" ] || { echo "--name is required" >&2; exit 1; }
    [ -n "$REQUESTED_CAPABILITY" ] || { echo "--requested-capability is required" >&2; exit 1; }
    [ -n "$PRIORITY" ] || PRIORITY="medium"
    validate_enum "$PRIORITY" "priority" low medium high critical
    FILE="$STORE_DIR/FEATURE_REQUESTS.md"
    ENTRY_ID=$(next_id "FEAT" "$FILE")
    {
      printf '## [%s] %s\n\n' "$ENTRY_ID" "$NAME"
      printf '**Logged**: %s\n' "$(utc_now)"
      printf '**Priority**: %s\n' "$PRIORITY"
      printf '**Status**: pending\n'
      printf '**Area**: %s\n\n' "$AREA"
      printf '### Requested Capability\n%s\n\n' "$REQUESTED_CAPABILITY"
      printf '### User Context\n%s\n\n' "${USER_CONTEXT:-N/A}"
      printf '### Complexity Estimate\n%s\n\n' "$COMPLEXITY"
      printf '### Suggested Implementation\n%s\n\n' "${SUGGESTED_IMPLEMENTATION:-N/A}"
      printf '### Metadata\n'
      append_metadata_line "Frequency" "$FREQUENCY"
      append_metadata_line "Related Features" "$RELATED_FEATURES"
      append_metadata_line "Tags" "$TAGS"
      printf '\n---\n'
    } >> "$FILE"
    ;;
  *)
    echo "Unsupported kind: $KIND" >&2
    exit 1
    ;;
esac

echo "Appended $KIND entry $ENTRY_ID to $FILE"
