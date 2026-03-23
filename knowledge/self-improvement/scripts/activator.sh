#!/bin/sh
# Emit a short self-improvement reminder for hook-driven workflows.

cat <<'EOF'
<self-improvement-reminder>
After the task, check whether reusable knowledge emerged:
- non-obvious fix or workaround
- user correction or repo convention
- repeated error pattern
- missing capability worth tracking
If yes, log it in .learnings/ and promote only distilled rules.
</self-improvement-reminder>
EOF
