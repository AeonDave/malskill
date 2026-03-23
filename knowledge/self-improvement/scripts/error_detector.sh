#!/bin/sh
# Detect likely command failures from tool output and emit a short reminder.

set -eu

OUTPUT=${CLAUDE_TOOL_OUTPUT:-${COPILOT_TOOL_OUTPUT:-${TOOL_OUTPUT:-}}}

if [ -z "$OUTPUT" ] && [ ! -t 0 ]; then
  OUTPUT=$(cat)
fi

lowered=$(printf '%s' "$OUTPUT" | tr '[:upper:]' '[:lower:]')
case "$lowered" in
  *"error:"*|*"failed"*|*"command not found"*|*"no such file"*|*"permission denied"*|*"fatal:"*|*"exception"*|*"traceback"*|*"modulenotfounderror"*|*"syntaxerror"*|*"typeerror"*|*"exit code"*|*"non-zero"*)
    cat <<'EOF'
<error-detected>
A command failure likely occurred. Log it to .learnings/ERRORS.md if it was non-obvious,
required investigation, or could recur in a future session.
</error-detected>
EOF
    ;;
esac
