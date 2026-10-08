# OpenCode guard template

Targets OpenCode and `@opencode-ai/plugin` **1.18.35**. The server module rejects selected sensitive filenames in the `read` tool and exposes a bounded `example_echo` tool. Set `enabled: false` to register no hooks/tools.

Rename the package and module ID when copying this template. Set agent/config permissions for broader access policy.

```bash
bun install
bun run typecheck
bun test
npm pack --dry-run
```

For an isolated project, add the copied package directory to its `opencode.json` `plugin` array. Restart the matching OpenCode host, confirm the `example.guard` initialization log, then exercise a permitted read, a protected read, and the echo tool. A passing unit test is separate from this host check.

After publication, use a pinned npm specifier such as `@example/opencode-guard@0.1.0`. Keep one installation route active. Refer to the [official plugin guide](https://opencode.ai/docs/plugins/) for config placement.
