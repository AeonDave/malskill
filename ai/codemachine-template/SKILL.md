---
name: codemachine-template
description: "Create, validate, and structure CodeMachine AI orchestrator workflow packages. Use when the user asks to build a CodeMachine workflow, write a .workflow.js file, define agents for CodeMachine, scaffold a codemachine package, or create multi-agent pipelines with CodeMachine CLI. Also triggers for: codemachine template, codemachine workflow design, main.agents.js, sub.agents.js, modules.js, resolveStep, resolveModule, directive.json, codemachine.json. Does NOT cover general Claude API usage or non-CodeMachine orchestration frameworks."
---

# codemachine-template

## Overview

CodeMachine is a CLI orchestrator that wraps AI coding engines (Claude Code, Codex, Cursor, etc.) into structured multi-agent workflows defined as JavaScript ES modules. This skill guides creation of correct, production-quality CodeMachine workflow packages from scratch.

## Package Structure

Every CodeMachine workflow is a package with this layout:

```
my-workflow-codemachine/        ← name ends with -codemachine for discoverability
├── codemachine.json            ← REQUIRED: manifest
├── config/
│   ├── main.agents.js          ← REQUIRED: core agent definitions
│   ├── sub.agents.js           ← optional: parallel sub-agents
│   ├── modules.js              ← optional: loop-capable validation agents
│   └── placeholders.js         ← optional: inter-agent variable injection
├── templates/workflows/
│   └── my-workflow.workflow.js ← REQUIRED: at least one workflow file
└── prompts/templates/
    └── workflow-name/
        ├── agent-name.md       ← agent prompt files
        └── shared/             ← shared prompt fragments
```

## Workflow Creation Process

### Step 1 — Define the manifest (`codemachine.json`)

```json
{
  "name": "my-workflow",
  "version": "1.0.0",
  "description": "What this workflow does"
}
```

Required: `name`, `version`. Optional: `description`, `paths` (custom layout).

### Step 2 — Define agents (`config/main.agents.js`)

Use `import.meta.dirname` for portable paths. Exactly one agent gets `role: 'controller'` only if it drives interactive conversation before automation.

```javascript
import path from 'path';
const promptsDir = path.join(import.meta.dirname, '..', 'prompts', 'templates', 'my-workflow');

export default [
  {
    id: 'planner',                    // REQUIRED: unique, lowercase-hyphenated
    name: 'Project Planner',          // REQUIRED: TUI display name
    description: 'Creates implementation plan',  // REQUIRED
    promptPath: path.join(promptsDir, 'planner.md'),  // REQUIRED

    // Optional:
    chainedPromptsPath: [             // sequential prompts with user interaction between
      path.join(promptsDir, 'chained', 'step-01.md'),
      { path: path.join(promptsDir, 'chained', 'step-02.md'), tracks: ['track-id'] },
    ],
    role: 'controller',               // only ONE agent per workflow; omit for regular agents
    engine: 'claude',                 // 'claude'|'codex'|'cursor'|'opencode'|'ccr'|'mistral'
    model: 'claude-opus-4-7',
    modelReasoningEffort: 'high',     // 'low'|'medium'|'high' — reasoning-capable engines (e.g. Codex)
    tracks: ['track-id'],             // agent runs only for these tracks
    conditions: ['cond-id'],          // AND logic: all must be selected
    conditionsAny: ['cond-a', 'cond-b'], // OR logic: any must be selected
    mcp: [{ server: 'workflow-signals', only: ['propose_step_completion'] }],
  },
];
```

### Step 3 — Define sub-agents if needed (`config/sub.agents.js`)

Sub-agents run in parallel via `codemachine run "agent-a & agent-b"` from an orchestrator prompt.

```javascript
import path from 'path';
const promptsDir = path.join(import.meta.dirname, '..', 'prompts', 'templates', 'my-workflow');

export default [
  {
    id: 'frontend-dev',
    name: 'Frontend Developer',
    description: 'Implements UI components',
    mirrorPath: path.join(promptsDir, 'sub-agents', 'frontend.md'),  // static prompt
    // Omit mirrorPath for orchestrator-generated dynamic prompts
  },
];
```

### Step 4 — Define modules if looping is needed (`config/modules.js`)

Modules are agents that can trigger loop-back behavior via `directive.json`.

```javascript
import path from 'path';
const promptsDir = path.join(import.meta.dirname, '..', 'prompts', 'templates', 'my-workflow');

export default [
  {
    id: 'quality-gate',
    name: 'Quality Gate',
    description: 'Validates output; loops back if issues found',
    promptPath: path.join(promptsDir, 'quality-gate.md'),
    behavior: { type: 'loop', action: 'stepBack' },  // REQUIRED for modules
  },
];
```

### Step 5 — Build the workflow file (`templates/workflows/my-workflow.workflow.js`)

Global helpers are injected at runtime: `resolveStep`, `resolveModule`, `resolveFolder`, `separator`, `controller`.

```javascript
export default {
  name: 'My Workflow',

  // Optional interactive controller agent (for pre-workflow conversation):
  controller: controller('controller-id', { engine: 'claude' }),

  // Autonomous mode: 'never'|'always'|true|false (true = default auto, user can toggle)
  autonomousMode: true,

  // Require a spec file before workflow starts:
  specification: false,

  // User selects a project type (radio):
  tracks: {
    question: 'What are we building?',
    options: {
      greenfield: { label: 'New Project', description: 'Build from scratch' },
      existing:   { label: 'Existing Codebase', description: 'Extend or refactor' },
    },
  },

  // User selects features (multi-select):
  conditionGroups: [
    {
      id: 'stack',
      question: 'What does the project include?',
      multiSelect: true,
      tracks: ['greenfield'],          // scope to a specific track
      conditions: {
        has_api:  { label: 'REST API', description: 'Backend endpoints' },
        has_ui:   { label: 'Frontend UI', description: 'React/Next.js UI' },
        has_auth: { label: 'Authentication', description: 'User login/JWT' },
      },
    },
  ],

  steps: [
    separator("Planning"),
    resolveStep('planner', { executeOnce: true }),

    separator("Implementation"),
    resolveStep('backend-dev', {
      tracks: ['greenfield'],
      conditions: ['has_api'],          // runs only if has_api selected
      interactive: false,
      engine: 'codex',
      modelReasoningEffort: 'medium',
    }),
    resolveStep('frontend-dev', {
      conditionsAny: ['has_ui', 'has_auth'],  // runs if either selected
    }),

    separator("Validation"),
    resolveModule('quality-gate', { loopSteps: 2, loopMaxIterations: 3 }),
  ],

  subAgentIds: ['frontend-dev', 'backend-dev', 'test-runner'],
};
```

### Step 6 — Write prompt files

Every agent prompt `.md` must have YAML frontmatter and write `directive.json` to signal completion:

```markdown
---
name: "Planner"
description: "Creates implementation plan from requirements"
---

## STEP GOAL
[What this agent must accomplish]

## MANDATORY EXECUTION RULES
[Constraints and invariants]

## Sequence of Instructions
1. Read `.codemachine/artifacts/requirements.md`
2. Produce implementation plan
3. Write `.codemachine/artifacts/plan.md`
4. Write directive:

\`\`\`json
{ "action": "complete", "reason": "Plan written" }
\`\`\`

## SUCCESS METRICS
[How to know the step succeeded]
```

**Directive actions:**

| `action` | Effect |
|----------|--------|
| `complete` / `continue` | Advance to next step |
| `loop` | Return N steps back (requires module with `loopSteps`) |
| `checkpoint` | Pause and await user confirmation |
| `trigger` | Invoke a specific agent (trigger module type) |
| `error` | Halt workflow with failure |
| `stop` | Terminate workflow successfully |

Directive must be written to `.codemachine/memory/directive.json` as a file — chat messages are not detected.

### Step 7 — Wire inter-agent data with placeholders (`config/placeholders.js`)

```javascript
import path from 'path';
export default {
  userDir: {
    // Resolved relative to user's project directory at runtime
    requirements: '.codemachine/artifacts/requirements.md',
    plan_output:  '.codemachine/artifacts/plan.md',
  },
  packageDir: {
    // Resolved relative to this workflow package
    coding_standards: path.join('prompts', 'templates', 'my-workflow', 'shared', 'standards.md'),
  },
};
```

Use in prompts as `{{placeholder_name}}` — expands to full file contents at runtime.

**Built-in runtime placeholders** (no registration needed, always available):

| Placeholder | Value |
|-------------|-------|
| `{{date}}` | Current date |
| `{{project_name}}` | Active project name |
| `{{selected_track}}` | User's selected track ID |
| `{{selected_conditions}}` | User's selected condition IDs |
| `{{specification}}` | Contents of spec file (if `specification: true`) |

## Validation Constraints

Before declaring a template complete, verify:
- `name` and `version` in `codemachine.json` — non-empty
- Each agent: `id`, `name`, `description` all non-empty
- `promptPath` — non-empty string or non-empty array
- `modelReasoningEffort` — **only `'low'|'medium'|'high'`** if present. CodeMachine's
  validator hard-rejects any other value (e.g. `'xhigh'`) and the template then
  **silently disappears from the picker** — no error shown to the user.
- `executeOnce`, `interactive` — boolean if present
- Exactly zero or one agent with `role: 'controller'`
- Modules have `behavior: { type: 'loop', action: 'stepBack' }`
- Module agents defined in `modules.js` must NOT be duplicated in `main.agents.js`
- Sub-agents use `mirrorPath`, not `promptPath`
- Every step agent writes `directive.json` (chat alone won't advance workflow)
- `resolveModule` loopSteps ≤ total preceding steps (can't loop past step 0)
- Every `resolveStep('id')` / `resolveModule('id')` id MUST exist in the package's
  `config/main.agents.js` / `config/modules.js`. The resolver **throws at module
  evaluation** on an unknown id (`Unknown main agent: …`) → template fails to load.

## Validating a workflow (catch picker-silent failures)

The CodeMachine picker drops any workflow whose module evaluation throws OR whose
template fails `validateWorkflowTemplate` — **without printing why**. To diagnose,
run the bundled validator (a faithful port of the CLI's `validator.ts` + the
`resolveStep`/`resolveModule` throw-on-unknown-id behaviour):

```bash
node <skill>/assets/validate-workflow.mjs <path/to/x.workflow.js> [--config <pkg>/config]
```

It loads the package config exactly like `registerImportedAgents`, evaluates the
workflow with the real global helpers, then validates. It surfaces:
- module-evaluation throws (unknown agent/module id) — the #1 silent-vanish cause
- invalid `modelReasoningEffort` (e.g. `'xhigh'`)
- bad step `type`, `promptPath`, module `behavior`
- loop bounds that rewind past step 0

`--config` auto-detects `../../config` relative to the workflow when omitted.
Run it on every workflow before declaring done; a missing template in the picker
almost always means it threw or failed validation here.

## MCP Integration

Built-in MCP servers for agent coordination:

```javascript
// Controller agent — approve/reject step transitions
mcp: [{ server: 'workflow-signals', only: ['approve_step_transition', 'get_pending_proposal'] }]

// Step agents in autonomous mode — propose completion
mcp: [{ server: 'workflow-signals', only: ['propose_step_completion'] }]

// Orchestrator agent — run sub-agents
mcp: [{
  server: 'agent-coordination',
  only: ['run_agents', 'get_agent_status'],
  targets: ['frontend-dev', 'backend-dev'],  // which sub-agents are invokable
}]
```

## Parallel Sub-Agent Execution

From an orchestrator prompt, run sub-agents:

```bash
# Sequential (&&)
codemachine run "data-dev && api-dev && ui-dev"

# Parallel (&)
codemachine run "api-dev[tail:50] & ui-dev[tail:50]"

# Mixed
codemachine run "data-dev[tail:30] && api-dev[tail:50] & ui-dev[tail:50] && test-dev"

# With input files
codemachine run "backend-dev[input:.codemachine/artifacts/plan.md,tail:100]"
```

## Common Mistakes

- Using `promptPath` instead of `mirrorPath` for sub-agents → sub-agents won't load
- Forgetting to write `directive.json` in prompt → workflow hangs indefinitely
- `loopSteps: 3` when only 2 steps precede the module → loops past start, crashes
- Multiple agents with `role: 'controller'` → only first is recognized
- `chainedPromptsPath` with a bare string path (not a `ChainedPathEntry` object or array) for multiple sequential prompts → only first step runs; use an array for multiple chained steps
- `resolveFolder` without spread operator (`...resolveFolder(...)`) → type error
- `resolveFolder` files without numeric prefix (`01-`, `02-`) → not loaded in correct order
- Defining a module agent in `main.agents.js` AND `modules.js` → ID conflict; keep in `modules.js` only

## Resources

### references/
- `references/workflow-schema.md` — complete TypeScript WorkflowTemplate interface + all option types; load when writing complex workflows or debugging validation errors
- `references/agent-config-schema.md` — full AgentDefinition, ModuleDefinition, SubAgentDefinition schemas; load when agent config has unusual requirements (conditional chains, MCP, nested conditions)
- `references/prompt-patterns.md` — prompt structure patterns, XML-style controller prompts, directive variants, artifact hierarchy conventions; load when writing or reviewing prompt files
- `references/orchestration-patterns.md` — interactive/autonomous/continuous/hybrid patterns, controller pattern, engine registry, CLI reference; load when designing the overall workflow execution model

### assets/
- `assets/codemachine.json` — manifest template
- `assets/main.agents.js` — annotated agent config template
- `assets/sub.agents.js` — sub-agent config template
- `assets/modules.js` — module config template
- `assets/placeholders.js` — placeholder registry template
- `assets/workflow.workflow.js` — full workflow template with all optional fields
- `assets/prompt-template.md` — prompt file template with frontmatter and directive
- `assets/validate-workflow.mjs` — workflow validator (port of CLI validator.ts + resolvers); run before declaring any workflow done to catch picker-silent load/validation failures
