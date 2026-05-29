# Agent Config Schemas

## config/main.agents.js — AgentDefinition

```typescript
type AgentDefinition = {
  id: string;                           // REQUIRED: unique, lowercase-hyphenated
  name: string;                         // REQUIRED: TUI display name
  description: string;                  // REQUIRED
  promptPath: string | string[];        // REQUIRED (string = single file; array = merged)
  role?: 'controller';                  // exactly ONE per workflow; omit otherwise
  chainedPromptsPath?: ChainedPathEntry | ChainedPathEntry[];
  engine?: string;
  model?: string;
  modelReasoningEffort?: 'low' | 'medium' | 'high';
  tracks?: string[];
  conditions?: string[];
  conditionsAny?: string[];
  mcp?: MCPConfig;
}

type ChainedPathEntry = string | {
  path: string;
  conditions?: string[];
  conditionsAny?: string[];
  tracks?: string[];
}
```

### promptPath array — files merged into single prompt

```javascript
promptPath: [
  path.join(promptsDir, 'shared', 'coding-standards.md'),
  path.join(promptsDir, 'developer', 'persona.md'),
  path.join(promptsDir, 'developer', 'instructions.md'),
]
```

All files concatenated and shown to agent simultaneously.

### chainedPromptsPath — sequential with user interaction between

```javascript
chainedPromptsPath: [
  path.join(promptsDir, 'analyst', 'chained', 'step-01-features.md'),
  {
    path: path.join(promptsDir, 'analyst', 'chained', 'step-02-users.md'),
    tracks: ['full-app'],              // only for this track
  },
  {
    path: path.join(promptsDir, 'analyst', 'chained', 'step-03-criteria.md'),
    conditions: ['has_api'],           // only when has_api selected
    conditionsAny: ['has_ui', 'has_auth'],
  },
]
```

Each entry injected in sequence with a conversation turn between them.

## config/sub.agents.js — SubAgentDefinition

```typescript
type SubAgentDefinition = {
  id: string;           // REQUIRED
  name: string;         // REQUIRED
  description: string;  // REQUIRED
  mirrorPath?: string;  // static prompt; omit for orchestrator-generated prompts
}
```

Key difference: `mirrorPath` (not `promptPath`). Sub-agents are invoked via `codemachine run` inside orchestrator prompts, not as workflow steps.

## config/modules.js — ModuleDefinition

```typescript
type ModuleDefinition = AgentDefinition & {
  behavior: {
    type: 'loop';         // currently only supported type
    action: 'stepBack';   // currently only supported action
  };
}
```

Modules are regular agents that can trigger loop-back via `directive.json`. They appear in the workflow via `resolveModule()` which adds loop metadata to the step.

## config/placeholders.js — PlaceholderRegistry

```typescript
type PlaceholderRegistry = {
  userDir?: Record<string, string>;    // paths relative to user's project dir
  packageDir?: Record<string, string>; // paths relative to this workflow package
}
```

```javascript
import path from 'path';
export default {
  userDir: {
    requirements:   '.codemachine/artifacts/requirements.md',
    tech_spec:      '.codemachine/artifacts/technical_spec.md',
    openapi:        '.codemachine/artifacts/specs/03_openapi.yaml',
  },
  packageDir: {
    directive_guide: path.join('prompts', 'templates', 'shared', 'directive-output.md'),
    coding_standards: path.join('prompts', 'templates', 'shared', 'standards.md'),
  },
};
```

Use in prompts: `{{requirements}}` → full file contents at runtime.

**Built-in runtime placeholders (no registration needed):**

| Placeholder | Value |
|-------------|-------|
| `{{date}}` | Current date |
| `{{project_name}}` | Active project identifier |
| `{{selected_track}}` | User's selected track ID |
| `{{selected_conditions}}` | User's selected condition IDs |
| `{{specification}}` | Spec file contents (requires `specification: true` in workflow) |

## config/agent-characters.json — Visual Personas

```json
{
  "personas": {
    "swagger": {
      "baseFace": "(⌐■_■)",
      "expressions": {
        "thinking": "(╭ರ_•́)",
        "tool":     "<(•_•<)",
        "error":    "(╥﹏╥)",
        "idle":     "(⌐■_■)"
      }
    }
  },
  "agents": {
    "planner": "swagger",
    "developer": "friendly"
  },
  "defaultPersona": "friendly"
}
```

Built-in: `swagger`, `friendly`, `analytical`.

## Engine registry

| engine | default model | reasoning |
|--------|--------------|-----------|
| `claude` | opus | No |
| `ccr` | sonnet | No |
| `codex` | gpt-5.2-codex | Yes (medium default) |
| `opencode` | opencode/big-pickle | No |
| `cursor` | auto | No |
| `mistral` | devstral-2 | No |
| `auggie` | auto | No |

Resolution cascade: engine registry → `main.agents.js` → `workflow.js` step override → CLI flag.
Fallback: `opencode` → `claude` → `codex` → `cursor` → `ccr`

## .codemachine/ runtime state

```
.codemachine/
├── agents/             ← registered sub-agent configs
├── inputs/             ← user specification files (when specification: true)
├── memory/
│   └── directive.json  ← agent control signals (agents write here)
├── logs/
│   ├── registry.db     ← SQLite: name, timestamp, duration, status, tokens, errors
│   └── agent-*.log     ← full prompts and responses per run
└── template.json       ← primary workflow state record
```

### template.json state

```typescript
{
  activeTemplate: string,
  lastUpdated: string,              // ISO 8601

  completedSteps: {
    [stepIndex: number]: {
      sessionId: string,
      monitoringId: string,
      completedChains: number[],
      completedAt: string,
    }
  },
  notCompletedSteps: number[],
  resumeFromLastStep: boolean,      // default true

  selectedTrack: string,
  selectedConditions: string[],
  projectName: string,
  autonomousMode: 'true'|'false'|'never'|'always',

  controllerConfig?: {
    agentId: string,
    sessionId: string,
    monitoringId: string,
  },
  controllerView: boolean,
}
```

Manual step rerun: remove step index (and all subsequent) from `completedSteps`.
Full reset: delete `template.json`.
