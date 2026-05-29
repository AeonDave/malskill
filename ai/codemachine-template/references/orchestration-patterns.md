# Orchestration Patterns & CLI Reference

## Patterns

### 1. Interactive (user drives every step)

```javascript
export default {
  steps: [
    resolveStep('planner',   { interactive: true }),
    resolveStep('developer', { interactive: true }),
    resolveStep('tester',    { interactive: true }),
  ],
};
```

User confirms or provides input before each step advances.

### 2. Autonomous (controller drives pipeline)

```javascript
export default {
  controller: controller('po-agent', { engine: 'claude' }),
  autonomousMode: 'always',
  steps: [
    resolveStep('po-agent',    {}),
    resolveStep('architect',   { interactive: false }),
    resolveStep('developer',   { interactive: false }),
  ],
};
```

Controller agent (PO) approves each step transition via MCP `workflow-signals`.

Required agent MCP config:
- Controller: `mcp: [{ server: 'workflow-signals', only: ['approve_step_transition', 'get_pending_proposal'] }]`
- Step agents: `mcp: [{ server: 'workflow-signals', only: ['propose_step_completion'] }]`

### 3. Continuous (zero-touch batch)

```javascript
export default {
  specification: true,          // reads spec file from .codemachine/inputs/
  autonomousMode: 'always',
  steps: [
    resolveStep('analyst',    { interactive: false, executeOnce: true }),
    resolveStep('developer',  { interactive: false }),
    resolveStep('tester',     { interactive: false }),
    resolveModule('gate',     { loopSteps: 1, loopMaxIterations: 3 }),
  ],
};
```

No user interaction. Spec file provides all context upfront.

### 4. Hybrid (key decisions manual, routine auto)

```javascript
export default {
  steps: [
    resolveStep('po',        { interactive: true }),      // user conversation
    resolveStep('architect', { interactive: true }),      // user review checkpoint
    resolveStep('developer', { interactive: false }),     // auto
    resolveStep('tester',    { interactive: false }),     // auto
    resolveModule('gate',    { loopSteps: 2, loopMaxIterations: 3 }),
  ],
};
```

### 5. Parallel Sub-Agents (via orchestrator step)

```javascript
// workflow.js
export default {
  steps: [
    resolveStep('impl-orchestrator', {}),  // this agent runs sub-agents in parallel
  ],
  subAgentIds: ['data-dev', 'api-dev', 'ui-dev', 'test-dev'],
};

// impl-orchestrator agent config in main.agents.js
{
  id: 'impl-orchestrator',
  mcp: [{
    server: 'agent-coordination',
    only: ['run_agents', 'get_agent_status'],
    targets: ['data-dev', 'api-dev', 'ui-dev', 'test-dev'],
  }],
}
```

Inside the orchestrator prompt:
```bash
codemachine run "data-dev[tail:30] && api-dev[tail:50] & ui-dev[tail:50] && test-dev[tail:50]"
```

### 6. Loop + Fix Pattern

```javascript
export default {
  steps: [
    resolveStep('developer', {}),
    resolveStep('tester',    { interactive: false }),
    resolveModule('gate',    {
      loopSteps: 2,              // loops back 2 steps to developer
      loopMaxIterations: 3,
      loopSkip: ['setup'],       // skip any already-done setup steps
    }),
  ],
};
```

Loop flow: tester writes `{ "action": "loop" }` → gate module triggers → workflow rewinds 2 steps → developer reruns with `fix_instructions.md` context.

## CLI Reference

```bash
# Core
codemachine                          # TUI (must not be in $HOME)
codemachine version
codemachine -d <dir>                 # set working directory

# Workflow
codemachine templates                # interactive selector
codemachine templates list

# Script mode (direct sub-agent invocation)
codemachine run "agent-id 'message'"
codemachine run "agent-a & agent-b"            # parallel
codemachine run "agent-a && agent-b"           # sequential
codemachine run "agent-a[tail:50] & agent-b[input:file.md,tail:100]"

# Single step
codemachine step <agentId>
codemachine step <agentId> "message" --engine claude --model opus --reasoning high

# Auth
codemachine auth login
codemachine auth logout
codemachine auth status

# Package management
codemachine import ./local-path
codemachine import user/repo
codemachine import https://github.com/user/repo
codemachine export

# Debug
codemachine agents
codemachine agents logs <id>
codemachine agents export
codemachine doctor
codemachine mcp
```

### run script modifiers

```
[tail:N]              take last N lines of agent output
[input:file.md]       inject file content as additional context
[input:f1.md;f2.md]   inject multiple files
```

## TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Shift+Tab` | Toggle autonomous / manual mode |
| `Tab` | Switch timeline panel |
| `P` | Pause execution |
| `Ctrl+S` | Skip remaining steps |
| `Ctrl+C` | Quit with state save |
| `H` | Open history |
| `R` | Return to controller |
| `Enter` | Expand agent / advance |
| `↑↓` | Navigate timeline |
| `Y/N` | Quick confirm/reject |
| `Escape` | Close dialog |
| `Ctrl+T` | Toggle dark/light theme |

Status symbols: `·` disabled, `❯` ready, `‖` active/paused, `✗` failed, `◉` awaiting input

## Runner Modes

| interactive | autoMode | chainedPrompts | Behavior |
|-------------|----------|----------------|----------|
| true | true | yes | Controller drives with prompts |
| true | true | no | Controller drives single step |
| true | false | yes | User drives with prompts |
| true | false | no | User drives each step |
| false | true | yes | Fully autonomous |
| false | true | no | Auto-advance to next step |
| false | false | yes | Forced → user drives + warning |
| false | false | no | Forced → user drives + warning |

## Install sources

```bash
codemachine import ./my-workflow
codemachine import ~/projects/my-workflow
codemachine import /absolute/path
codemachine import username/repo-name           # GitHub short form
codemachine import https://github.com/user/repo
codemachine import git@github.com:user/repo.git
codemachine import package-name                 # GitHub search by name
```

Installed to: `~/.codemachine/imports/{name}-codemachine/`

## codemachine.json paths override

If the package uses a non-standard layout:

```json
{
  "name": "my-workflow",
  "version": "1.0.0",
  "paths": {
    "config": "cfg/",
    "workflows": "flows/",
    "prompts": "content/",
    "characters": "cfg/personas.json"
  }
}
```
