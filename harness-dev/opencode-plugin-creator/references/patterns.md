# Lifecycle, state, and verification

Use these rules when a plugin initializes state, starts resources, or performs asynchronous work.

## Initialization

The host awaits the plugin function. Await setup required by its hooks, or retain a readiness promise and make dependent hooks await it. Optional background work needs an observed rejection and a cancellation/teardown path. Do not detach required setup merely to shorten startup.

Keep entrypoints thin. Put reusable logic in sibling modules, and test both that logic and the actual returned hook closures with a typed fixture context.

## Logging and errors

Use the [SDK logging route](https://opencode.ai/docs/plugins/#logging), `client.app.log({ body: { service, level, message } })`. Invoke it on the client object; preserve receiver binding when wrapping SDK methods. Handle a rejected log request explicitly instead of creating an unhandled promise.

Keep logs bounded and avoid logging credentials or complete tool arguments. A startup log proves initialization reached that line; it does not prove the intended hook executed.

## Resource ownership

Return `dispose` for watchers, timers, servers, and child processes. Stop pending work before releasing resources. The [released host](https://github.com/anomalyco/opencode/blob/53d1eabb61e21162157817bf677da0a4ad3332e3/packages/opencode/src/plugin/index.ts) calls teardown hooks as the instance closes.

Multiple host instances can initialize the plugin separately. Bind a fixed port only when the task needs it; verify ownership before reusing an already-running service. Keep per-session state keyed by session ID and bound in size.

Use `input.project.id` for host project identity. Resolve paths with `node:path`; use SDK/context directories rather than the plugin process's cwd. For managed child sessions, follow [agent delegation guidance](../../opencode-agent-creator/references/agent-config-reference.md) and preserve user-visible history unless deletion is requested.

## Focused tests

Exercise relevant behavior:

- Initialization rejects invalid configuration before registering hooks.
- A hook changes the provided output object, and rejects the denied case.
- A custom tool returns the advertised result and honors cancellation/permission failure.
- Required initialization failure reaches dependent hooks.
- Teardown releases each resource the plugin actually owns.

Do not add a server, watcher, or lifecycle callback solely to demonstrate a pattern.

## Host verification

1. Typecheck against the target plugin/SDK package versions.
2. Run focused unit tests; import the real entrypoint, not only sibling helpers.
3. Install into an isolated OpenCode project, start the matching host, and confirm initialization.
4. Trigger the intended operation and inspect its observable result/error.
5. For owned resources, close/reload the instance and verify cleanup.

If host execution is unavailable, report the package versions, typecheck/tests, and the missing host check. Test success does not establish that a config path or export is discovered.
