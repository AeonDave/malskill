# SDK and Local Host Integration

Load when selecting or migrating an SDK, connecting a local server, diagnosing host startup, or packaging a working integration.

## Match the actual runtime

- Record the installed SDK package/version, runtime, entrypoint, host/version, transport, and required protocol features. Use the project's lockfile and that release's documentation; a current README may describe a different major version.
- Prefer the official SDK for new servers; distinguish it from similarly named third-party packages. Preserve an existing supported framework unless the task requires changing it.
- Check extension support independently of core protocol support. Do not infer Tasks, Apps, or client-input support from the SDK name or latest protocol date.
- Let the SDK serialize wire fields and manage transport lifecycle. Verify emitted messages through a compatible client; missing literal `server/discover` or `resultType` in application code is not evidence of a defect.
- For Python, consult the [official SDK](https://github.com/modelcontextprotocol/python-sdk) and [migration guide](https://py.sdk.modelcontextprotocol.io/migration/) for the installed major version. Check imports, runtime floor, handler signatures, error conversion, startup/shutdown, and client APIs together; do not mix examples across versions.
- Keep domain handlers independent of the host. Acquire shared clients/pools through the SDK's documented lifespan mechanism and close them on shutdown; bind caller identity to each request, not a process-global variable.

## Host launch contract

For stdio, configure a command plus argument array using the target host's documented schema. A `mcpServers` JSON object is host configuration, not an MCP protocol message; other hosts use different schemas.

1. Resolve the executable and entrypoint explicitly. Prefer absolute installed paths for local configuration; a GUI host may have a different `PATH` from the terminal.
2. Make data/config paths independent of the host's working directory. Use an explicit supported working-directory option or resolve paths in the application. Preserve spaces as part of one argument, not shell quoting embedded inside an argument.
3. Supply the required environment deliberately; do not assume shell activation, startup profiles, or `.env` loading. Use the host's secret mechanism where available and keep credentials out of examples, committed config, and logs.
4. Reserve stdout for MCP traffic; route application and dependency diagnostics to stderr. Check wrappers and child processes too.
5. Reproduce the exact launch command with the intended environment from an unrelated directory. Inspect stderr and the exit code before changing protocol code.
6. Connect using an independent MCP client or Inspector compatible with the chosen revision. Exercise discovery/listing and one representative call or read.
7. Register or reload the configuration using the host's supported procedure; test the same operation in that host. Registration does not grant unrestricted authorization, and a terminal check does not prove host compatibility.

Stdio limits network exposure but does not sandbox the executable. Restrict its OS permissions, filesystem scope, environment, and network access to the workflow's needs. For local HTTP, apply the Origin/Host, binding, and authentication controls in [security.md](security.md).

## Diagnose the failing boundary

| Observation | Next check |
|---|---|
| Process never starts or exits immediately | Executable/runtime, arguments, cwd-independent paths, missing env, import/startup error on stderr |
| Process stays alive but client cannot parse replies | Stdout contamination, selected transport, framing, client/server protocol compatibility |
| Inspector works but target host fails | Exact command, environment, host-supported revision and capabilities, configuration reload, host logs |
| Tools work but resources/prompts are absent | Server advertisement and listing versus the host's supported UI; do not assume automatic context loading |
| Call hangs | Trace the request into the handler and upstream operation; inspect deadlines, blocking I/O, and unsupported client input |

Use [systematic-debugging](../../../coding/systematic-debugging/SKILL.md) when the failure boundary remains unclear. Change one supported hypothesis at a time; do not repeatedly reinstall or migrate without evidence.

## Package only the requested deployment

- Keep source plus a launch command for internal use when sufficient; use a language package for runtime-managed installs or an [MCP bundle](https://github.com/modelcontextprotocol/mcpb) when the target host supports that format.
- Test the packaged entrypoint, declared dependencies/runtime, required configuration, and shutdown from a clean install location on each claimed platform. Development checkout success is insufficient.
- Keep installed launch paths deterministic, but bundle paths relocatable using the manifest's supported variables. Do not bake development-machine paths or credentials into a manifest.
- Document access requirements and defaults; packaging is not a sandbox. Validate the chosen format with its current tooling.
- Use [publication checks](testing.md#publication-readiness) for distribution or Registry publication; private host integration does not require a Registry entry.

Host-specific example and troubleshooting: [official local-server guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers). Verify the target host's current schema before editing its live configuration.
