#!/bin/sh
# Promote a learning entry into project guidance or a new skill without Python.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_FILE=""
ENTRY_ID=""
TARGET=""
TARGET_FILE=""
TARGET_LABEL=""
SECTION="Self-Improvement Promotions"
RULE=""
RULE_FILE=""
SKILL_NAME=""
SKILLS_ROOT="knowledge"
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --source-file) SOURCE_FILE="$2"; shift 2 ;;
    --entry-id) ENTRY_ID="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --target-file) TARGET_FILE="$2"; shift 2 ;;
    --target-label) TARGET_LABEL="$2"; shift 2 ;;
    --section) SECTION="$2"; shift 2 ;;
    --rule) RULE="$2"; shift 2 ;;
    --rule-file) RULE_FILE="$2"; shift 2 ;;
    --skill-name) SKILL_NAME="$2"; shift 2 ;;
    --skills-root) SKILLS_ROOT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[ -n "$SOURCE_FILE" ] || { echo "--source-file is required" >&2; exit 1; }
[ -n "$ENTRY_ID" ] || { echo "--entry-id is required" >&2; exit 1; }
[ -n "$TARGET" ] || { echo "--target is required (file|skill)" >&2; exit 1; }
case "$TARGET" in file|skill) ;; *) echo "Unsupported target: $TARGET (expected file or skill)" >&2; exit 1 ;; esac

# --- helpers ---------------------------------------------------------------

extract_section() {
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

# First non-empty line from a section, with fallback sections.
first_line_of() {
  for s in "$@"; do
    line=$(extract_section "$s" | head -n 1)
    [ -n "$line" ] && { printf '%s' "$line"; return; }
  done
}

# Truncate to first sentence (period/exclamation/question followed by space or end).
first_sentence() {
  printf '%s' "$1" | sed 's/\([.!?]\) .*/\1/'
}

update_entry() {
  new_status="$1"
  extra_label="$2"
  extra_value="$3"
  tmp_file=$(mktemp)
  awk -v id="$ENTRY_ID" -v status="$new_status" -v label="$extra_label" -v value="$extra_value" '
    BEGIN { in_block=0; extra_done=0; status_prefix="**Status**:"; label_prefix="**" label "**:" }
    $0 ~ "^## \\[" id "\\]" { in_block=1 }
    in_block && /^## \[/ && $0 !~ "^## \\[" id "\\]" { in_block=0 }
    in_block && index($0, status_prefix) == 1 {
      print "**Status**: " status
      if (label != "") {
        print "**" label "**: " value
        extra_done=1
      }
      next
    }
    in_block && label != "" && index($0, label_prefix) == 1 {
      if (!extra_done) {
        print "**" label "**: " value
        extra_done=1
      }
      next
    }
    { print }
  ' "$SOURCE_FILE" > "$tmp_file"
  mv "$tmp_file" "$SOURCE_FILE"
}

# Insert content under a ## heading, before the next ## heading (like Python
# append_under_heading). Falls back to appending a new section at EOF.
append_under_heading() {
  _file="$1"
  _heading="$2"
  _content="$3"
  if [ ! -f "$_file" ]; then
    printf '## %s\n\n%s\n' "$_heading" "$_content" > "$_file"
    return
  fi
  if grep -Fxq "## $_heading" "$_file"; then
    # Section exists — insert _content before the next ## heading.
    tmp_file=$(mktemp)
    awk -v heading="## $_heading" -v content="$_content" '
      BEGIN { found=0; inserted=0 }
      found && !inserted && /^## / {
        print content
        print ""
        inserted=1
      }
      $0 == heading { found=1 }
      { print }
      END { if (found && !inserted) print "\n" content }
    ' "$_file" > "$tmp_file"
    mv "$tmp_file" "$_file"
  else
    # Section does not exist — append new section at end.
    printf '\n## %s\n\n%s\n' "$_heading" "$_content" >> "$_file"
  fi
}

# --- distill rule ----------------------------------------------------------

summary=$(first_line_of "Summary" "Requested Capability")
suggested=$(first_line_of "Suggested Action" "Suggested Fix" "Suggested Implementation")

if [ -z "$RULE" ] && [ -n "$RULE_FILE" ]; then
  RULE=$(cat "$RULE_FILE")
fi
if [ -z "$RULE" ]; then
  s=$(first_sentence "${summary:-Promoted learning}")
  if [ -n "$suggested" ]; then
    a=$(first_sentence "$suggested")
    RULE="- $s $a"
  else
    RULE="- $s"
  fi
fi

# --- apply target ----------------------------------------------------------

case "$TARGET" in
  file)
    [ -n "$TARGET_FILE" ] || { echo "--target-file is required for file promotion" >&2; exit 1; }
    [ -n "$TARGET_LABEL" ] || TARGET_LABEL=$(basename "$TARGET_FILE")
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "Would append to $TARGET_FILE under section '$SECTION':"
      echo "$RULE"
      echo "Would mark $ENTRY_ID as promoted to $TARGET_LABEL"
      exit 0
    fi
    append_under_heading "$TARGET_FILE" "$SECTION" "$RULE"
    update_entry "promoted" "Promoted" "$TARGET_LABEL"
    echo "Promoted $ENTRY_ID to $TARGET_FILE"
    ;;
  skill)
    if [ "$DRY_RUN" -eq 1 ]; then
      "$SCRIPT_DIR/extract_skill.sh" ${SKILL_NAME:+"$SKILL_NAME"} --source-file "$SOURCE_FILE" --entry-id "$ENTRY_ID" --output-dir "$SKILLS_ROOT" --dry-run
      echo "Would mark $ENTRY_ID as promoted_to_skill"
      exit 0
    fi
    if [ -n "$SKILL_NAME" ]; then
      "$SCRIPT_DIR/extract_skill.sh" "$SKILL_NAME" --source-file "$SOURCE_FILE" --entry-id "$ENTRY_ID" --output-dir "$SKILLS_ROOT"
      skill_path="$SKILLS_ROOT/$SKILL_NAME"
    else
      skill_output=$("$SCRIPT_DIR/extract_skill.sh" --source-file "$SOURCE_FILE" --entry-id "$ENTRY_ID" --output-dir "$SKILLS_ROOT")
      echo "$skill_output"
      skill_path=$(printf '%s\n' "$skill_output" | awk '/Created skill scaffold at / {print $NF}' | tail -n 1)
    fi
    update_entry "promoted_to_skill" "Skill-Path" "$skill_path"
    echo "Promoted $ENTRY_ID into $skill_path"
    ;;
  *)
    echo "Unsupported target: $TARGET" >&2
    exit 1
    ;;
esac
