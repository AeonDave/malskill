import type { HookHandler } from 'openclaw/hooks';

const REMINDER = `## Self Improvement Reminder

Before or after significant work, check whether relevant knowledge should be reviewed, logged, or promoted:
- user correction or repo fact
- non-obvious error and its fix
- repeated workaround or repeated reminder
- missing capability worth tracking
`;

const handler: HookHandler = async (event) => {
  if (!event || typeof event !== 'object') {
    return;
  }

  if (event.type !== 'agent' || event.action !== 'bootstrap') {
    return;
  }

  if (!event.context || typeof event.context !== 'object') {
    return;
  }

  const sessionKey = event.sessionKey || '';
  if (sessionKey.includes(':subagent:')) {
    return;
  }

  if (Array.isArray(event.context.bootstrapFiles)) {
    event.context.bootstrapFiles.push({
      path: 'SELF_IMPROVEMENT_REMINDER.md',
      content: REMINDER,
      virtual: true,
    });
  }
};

export default handler;
