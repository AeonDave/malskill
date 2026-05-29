import path from 'path';

export default {
  // userDir: paths resolved relative to the USER's project directory at runtime
  userDir: {
    requirements:  '.codemachine/artifacts/requirements.md',
    tech_spec:     '.codemachine/artifacts/technical_spec.md',
    plan_output:   '.codemachine/artifacts/plan.md',
    fix_notes:     '.codemachine/memory/fix_instructions.md',
  },

  // packageDir: paths resolved relative to THIS workflow package directory
  packageDir: {
    directive_guide:   path.join('prompts', 'templates', 'shared', 'directive-output.md'),
    coding_standards:  path.join('prompts', 'templates', 'shared', 'standards.md'),
  },
};

// Usage in prompt .md files: {{requirements}}, {{tech_spec}}, etc.
// Each placeholder expands to the full file contents at runtime.
// Convention: limit to one file-content placeholder per prompt (not a hard system constraint).
