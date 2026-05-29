import path from 'path';
const promptsDir = path.join(import.meta.dirname, '..', 'prompts', 'templates', 'my-workflow');

export default [
  // CONTROLLER AGENT (optional — only if pre-workflow conversation needed)
  // {
  //   id: 'controller',
  //   role: 'controller',          // exactly ONE per workflow
  //   name: 'Product Owner',
  //   description: 'Drives pre-workflow conversation and autonomous approvals',
  //   promptPath: path.join(promptsDir, 'controller.md'),
  //   mcp: [{
  //     server: 'workflow-signals',
  //     only: ['approve_step_transition', 'get_pending_proposal'],
  //   }],
  // },

  {
    id: 'planner',                          // REQUIRED: unique, lowercase-hyphenated
    name: 'Project Planner',                // REQUIRED: TUI display name
    description: 'Creates implementation plan from requirements',  // REQUIRED
    promptPath: path.join(promptsDir, 'planner.md'),               // REQUIRED

    // OPTIONAL fields:
    // chainedPromptsPath: [                // sequential prompts with interaction between
    //   path.join(promptsDir, 'chained', 'step-01.md'),
    //   { path: path.join(promptsDir, 'chained', 'step-02.md'), tracks: ['greenfield'] },
    // ],
    // engine: 'claude',                    // 'claude'|'codex'|'cursor'|'opencode'|'ccr'
    // model: 'claude-opus-4-7',
    // modelReasoningEffort: 'medium',      // 'low'|'medium'|'high' — reasoning-capable engines (e.g. Codex)
    // tracks: ['greenfield'],
    // conditions: ['has_api'],
    // conditionsAny: ['has_ui', 'has_auth'],
    // mcp: [{ server: 'workflow-signals', only: ['propose_step_completion'] }],
  },

  {
    id: 'developer',
    name: 'Developer',
    description: 'Implements features based on the plan',
    promptPath: path.join(promptsDir, 'developer.md'),
    // For parallel sub-agent orchestration, add:
    // mcp: [{
    //   server: 'agent-coordination',
    //   only: ['run_agents', 'get_agent_status'],
    //   targets: ['frontend-dev', 'backend-dev'],
    // }],
  },

  // NOTE: do NOT define module agents here.
  // Agents used via resolveModule() belong exclusively in modules.js.
  // Example: quality-gate → modules.js with behavior: { type: 'loop', action: 'stepBack' }
];
