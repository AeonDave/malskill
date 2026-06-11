# Subagent Routing and Delegation

**Load when**: As a Supervisor, you are about to delegate a task to a specialized role or a subagent via the `runSubagent` tool.

## The Delegation Contract

Subagents lack your high-level context. If you simply ask "Hack this server", they will hallucinate or spam tools. You must enforce a strict contract.

When formulating the subagent prompt, include these exact blocks:

1. **Role Context**: Tell the subagent which role it assumes (e.g., "Act as the `offensive-web-role`").
2. **The Hard Boundary**: "Stop and report back immediately if you hit a WAF block or lose connection."
3. **Required Artifacts**: "I need the exact curl command you used, and the raw base64 response of the reverse shell execution."
4. **Tool Restrictions**: If stealth is required, explicitly forbid intrusive scanners like `sqlmap` or `nikto`.

If a subagent returns without the required artifacts, *reject the submission* and instruct it to re-run the steps, capturing the data.
