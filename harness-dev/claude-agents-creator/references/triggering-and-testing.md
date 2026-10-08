# Validate Discovery and Behavior

Use the [official subagent docs](https://code.claude.com/docs/en/sub-agents#write-subagent-files) and installed `claude --version`; the checks below target 2.1.293.

## Load and parse

Claude watches existing project/user agent directories and picks up file changes within seconds. Restart after creating a scope's first `agents` directory, changing definitions under `--add-dir`, or starting with `--disable-slash-commands`. `/agents` prints editing guidance; it is not a registration list or creation wizard.

```bash
claude plugin validate .claude/agents
```

Component-directory lint requires 2.1.233+ and a directory named `agents`; an arbitrary example directory is treated as a plugin and needs a manifest. In 2.1.293, a malformed `tools: [` frontmatter line still passed this lint with a warning about the missing description. Parse frontmatter separately with a strict YAML parser, then check `name`, `description`, and supported field spelling. Unknown host fields are ignored. Use `--debug` for skipped definitions, unresolved tools, and trust failures; `/tasks` shows a running worker's actual model and effort.

For isolated definitions, use inline `--agents` JSON or a JSON file in non-interactive mode on 2.1.281+. The object uses `prompt` for the system-prompt body. Do not confuse this with a portable `SKILL.md` validator.

## Routing

Try representative requests without naming the worker, plus a nearby request it should not handle. Observe which worker is actually delegated to. Use explicit naming or `@agent-<name>` to test behavior independently of routing.

- Missed automatic delegation: make the concrete trigger clearer; do not inflate the description with unrelated tasks.
- Incorrect delegation: narrow the responsibility or overlapping descriptions.
- Explicit-only delegation: acceptable when on-demand behavior was intended.

## Behavior and effective capabilities

Run a representative task in the intended scope and check:

- It gets the supplied inputs through the available tools and obeys applicable repository rules.
- Its actual tool calls match the capability boundary, including any shell, MCP, memory, or nested-worker access.
- The model and effort match the intended effective configuration.
- The result satisfies the evidence/output contract; a turn-capped or interrupted result is identified as partial.
- Background results are observed before completion is claimed; a resumed worker retains the expected history.

For a no-write reviewer, try a request that also asks for a correction. Confirm it reports the proposed correction without writes. If memory auto-enables write tools or a shell allows modification, repair the capability configuration; stronger prose alone does not fix that gap.

For worktree isolation, inspect the revision and required change set before testing. For hooks/MCP, test the trust and plugin-scope behavior instead of assuming the fields execute everywhere.

## Iterate

Correct the demonstrated gap, then rerun its focused scenario. Use `skill-creator`'s behavior-comparison guidance when changing substantial instructions. Report strict parsing, component lint, discovery, and runtime behavior as separate evidence; do not claim runtime success from structural validation.
