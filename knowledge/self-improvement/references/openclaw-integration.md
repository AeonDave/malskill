# OpenClaw Integration

This path is optional. Use it only if your environment already relies on OpenClaw workspace files and hooks.

## What OpenClaw adds

OpenClaw can surface the self-improvement reminder during bootstrap and can keep shared workspace files for cross-session behavior.

Typical workspace shape:

```text
~/.openclaw/
├── workspace/
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── TOOLS.md
│   └── .learnings/
│       ├── LEARNINGS.md
│       ├── ERRORS.md
│       └── FEATURE_REQUESTS.md
├── skills/
└── hooks/
```

## Suggested setup

1. install the skill into the OpenClaw skills directory
2. create or copy the `.learnings/` files under the workspace
3. copy the optional hook from `hooks/openclaw/`
4. enable the hook in your OpenClaw environment

## Promotion targets in OpenClaw

Use OpenClaw workspace files only for high-signal guidance:
- `AGENTS.md` for workflow and delegation rules
- `SOUL.md` for behavioral guidance
- `TOOLS.md` for tool gotchas and integration reminders

Keep raw incident detail in `.learnings/`.

## Recommended policy

- use `.learnings/` for capture
- use workspace files for distilled rules
- avoid turning bootstrap reminders into long essays
- do not inject sensitive data into workspace-level prompts

## Included hook resources

The skill ships optional OpenClaw files in `hooks/openclaw/`:
- `HOOK.md`
- `handler.ts`
- `handler.js`

They exist for environments that expect either TypeScript or JavaScript handlers.
