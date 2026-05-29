# WorkflowTemplate Schema

Source: `src/workflows/templates/types.ts` (CodeMachine-CLI)

## WorkflowTemplate

```typescript
interface WorkflowTemplate {
  name?: string;                        // display name in TUI
  steps: WorkflowStep[];                // REQUIRED
  subAgentIds?: string[];               // IDs from sub.agents.js
  tracks?: TracksConfig;
  conditionGroups?: ConditionGroup[];
  controller?: ControllerDefinition;
  specification?: boolean;              // require spec file before start
  autonomousMode?: boolean | 'never' | 'always';  // true/false are booleans; 'never'/'always' are strings
}
```

## WorkflowStep union

```typescript
type WorkflowStep = ModuleStep | Separator;

interface Separator {
  type: 'separator';
  text: string;                         // REQUIRED non-empty
}

interface ModuleStep {
  type: 'module';
  agentId: string;                      // REQUIRED non-empty
  agentName: string;                    // REQUIRED non-empty
  promptPath: string | string[];        // REQUIRED non-empty
  model?: string;
  modelReasoningEffort?: 'low' | 'medium' | 'high';
  engine?: string;
  module?: ModuleMetadata;
  executeOnce?: boolean;
  interactive?: boolean;
  tracks?: string[];
  conditions?: string[];
  conditionsAny?: string[];
  mcp?: MCPConfig;
}
```

## ModuleMetadata behaviors

```typescript
// Loop back N steps
{ type: 'loop'; action: 'stepBack'; steps: number; trigger?: string; maxIterations?: number; skip?: string[]; }

// Trigger another agent
{ type: 'trigger'; action: 'mainAgentCall'; triggerAgentId: string; }

// Checkpoint evaluate
{ type: 'checkpoint'; action: 'evaluate'; }
```

## TracksConfig

```typescript
interface TracksConfig {
  question: string;
  options: Record<string, { label: string; description?: string }>;
}
```

## ConditionGroup

```typescript
interface ConditionGroup {
  id: string;
  question: string;
  multiSelect?: boolean;                // default false (radio)
  tracks?: string[];                    // scope to specific tracks
  conditions: Record<string, { label: string; description?: string }>;
  children?: Record<string, {           // nested follow-up per condition
    question: string;
    multiSelect?: boolean;
    conditions: Record<string, { label: string; description?: string }>;
  }>;
}
```

## ControllerDefinition

```typescript
interface ControllerDefinition {
  type: 'controller';
  agentId: string;
  options?: { engine?: string; model?: string; };
}
// Created via: controller('agent-id', { engine: 'claude' })
```

## MCPConfig

```typescript
type MCPConfig = Array<string | MCPServerFilterConfig>;

interface MCPServerFilterConfig {
  server: string;
  only?: string[];      // tool allowlist
  exclude?: string[];   // tool blocklist
  targets?: string[];   // sub-agent name allowlist (agent-coordination only)
}
```

## resolveStep overrides

```typescript
interface StepOverrides {
  agentName?: string;
  promptPath?: string | string[];
  model?: string;
  modelReasoningEffort?: 'low' | 'medium' | 'high';
  engine?: string;
  executeOnce?: boolean;
  interactive?: boolean;
  tracks?: string[];
  conditions?: string[];
  conditionsAny?: string[];
  mcp?: MCPConfig;
}
```

## resolveModule additional overrides

```typescript
interface ModuleOverrides extends StepOverrides {
  loopSteps?: number;
  loopMaxIterations?: number;
  loopSkip?: string[];
}
```

## Validation rules (from validator.ts)

- `steps` must be an array
- Each step `type`: `'module'` or `'separator'` only
- Separator `text`: non-empty string
- ModuleStep `agentId`, `agentName`: non-empty string
- ModuleStep `promptPath`: non-empty string or non-empty array of strings
- `model`: string if present
- `modelReasoningEffort`: exactly `'low'|'medium'|'high'` if present
- `executeOnce`, `interactive`: boolean if present
- `tracks` elements: strings
- Template loaded via dynamic `import()` with timestamp cache-bust

## autonomousMode behavior table

`true`/`false` are JavaScript booleans in the workflow file; `template.json` serializes them as strings `'true'`/`'false'`.

| Value | User can toggle | Default mode |
|-------|----------------|--------------|
| `'never'` | No | Manual locked |
| `'always'` | No | Autonomous locked |
| `true` | Yes (Shift+Tab) | Autonomous |
| `false` | Yes (Shift+Tab) | Manual |

## resolveFolder

```javascript
// Loads all numerically-prefixed .md files from a named folder in config
// Returns WorkflowStep[] — must be spread with ...
...resolveFolder('spec-kit', { engine: 'codex', modelReasoningEffort: 'medium' })
```

Folder files must be named `01-step.md`, `02-step.md`, etc. (numeric prefix).
