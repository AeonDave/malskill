import path from 'path';
const promptsDir = path.join(import.meta.dirname, '..', 'prompts', 'templates', 'my-workflow', 'sub-agents');

export default [
  {
    id: 'frontend-dev',                     // REQUIRED: unique, matches subAgentIds entry
    name: 'Frontend Developer',             // REQUIRED
    description: 'Implements UI components and pages',  // REQUIRED
    mirrorPath: path.join(promptsDir, 'frontend.md'),   // static prompt (use mirrorPath not promptPath)
    // Omit mirrorPath entirely for orchestrator-generated dynamic prompts
  },

  {
    id: 'backend-dev',
    name: 'Backend Developer',
    description: 'Implements API endpoints and business logic',
    mirrorPath: path.join(promptsDir, 'backend.md'),
  },

  {
    id: 'test-runner',
    name: 'Test Runner',
    description: 'Writes and runs tests for implemented features',
    mirrorPath: path.join(promptsDir, 'tests.md'),
  },
];
