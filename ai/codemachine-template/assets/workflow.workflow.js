// Full workflow template — remove unused optional sections before use
export default {
  name: 'My Workflow',

  // OPTIONAL: pre-workflow controller agent for interactive conversation
  // controller: controller('controller-id', { engine: 'claude' }),

  // OPTIONAL: autonomous mode
  // 'never'|'always'|true (default auto)|false (default manual)
  autonomousMode: true,

  // OPTIONAL: require a spec file in .codemachine/inputs/ before starting
  specification: false,

  // OPTIONAL: track selection (radio)
  // tracks: {
  //   question: 'What are we building?',
  //   options: {
  //     greenfield: { label: 'New Project', description: 'Start from scratch' },
  //     existing:   { label: 'Existing App', description: 'Extend or refactor' },
  //   },
  // },

  // OPTIONAL: condition groups (multi-select features)
  // conditionGroups: [
  //   {
  //     id: 'stack',
  //     question: 'What does the project include?',
  //     multiSelect: true,
  //     tracks: ['greenfield'],
  //     conditions: {
  //       has_api: { label: 'REST API', description: 'Backend endpoints' },
  //       has_ui:  { label: 'Frontend UI', description: 'React UI' },
  //     },
  //   },
  // ],

  steps: [
    separator("Planning"),
    resolveStep('planner', {
      // interactive: true,       // pause for user input
      // executeOnce: true,       // skip on workflow resume
      // engine: 'codex',
      // model: 'gpt-5.2-codex',
      // modelReasoningEffort: 'high',
      // tracks: ['greenfield'],
      // conditions: ['has_api'],
      // conditionsAny: ['has_ui', 'has_auth'],
    }),

    separator("Implementation"),
    resolveStep('developer', { interactive: false }),

    separator("Validation"),
    resolveModule('quality-gate', {
      loopSteps: 1,             // loop back 1 step (to developer)
      loopMaxIterations: 3,
      // loopSkip: ['setup'],   // skip these agent IDs during loop
    }),

    // OPTIONAL: spread a folder of numerically-prefixed step files
    // ...resolveFolder('spec-kit', { engine: 'claude' }),
  ],

  // OPTIONAL: sub-agents for parallel execution from orchestrator prompts
  // subAgentIds: ['frontend-dev', 'backend-dev', 'test-runner'],
};
