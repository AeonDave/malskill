import path from 'path';
const promptsDir = path.join(import.meta.dirname, '..', 'prompts', 'templates', 'my-workflow');

export default [
  {
    id: 'quality-gate',
    name: 'Quality Gate',
    description: 'Validates all checks and loops back if issues found',
    promptPath: path.join(promptsDir, 'quality-gate.md'),
    behavior: {
      type: 'loop',       // REQUIRED: must be 'loop'
      action: 'stepBack', // REQUIRED: must be 'stepBack'
    },
  },
];
