# Debugging and Testing

Load this file when something fails or when validating a new server end to end.

## Default workflow

1. **Inspector** — prove the server can start, initialize, and expose capabilities
2. **Local Python harness** — verify calls programmatically
3. **Target host** — confirm registration, approvals, and UX behavior

Do not start with the host if you cannot yet prove the server works standalone.

## Inspector-first checklist

- server starts
- `initialize` succeeds
- tools/resources/prompts are listed as expected
- a trivial call works
- invalid input fails clearly
- notifications/logs appear where expected

## Local harness checks

Use a `StdioServerParameters` + `stdio_client` + `ClientSession` harness to test:

- initialization
- capability discovery
- one or two representative calls
- env injection
- parser or output-shape expectations

## Stdio logging rule

For stdio servers, stdout is protocol traffic. Log to stderr only.

If the host suddenly cannot parse messages after you added “harmless” prints, the prints are probably not harmless.

## Common failure patterns

| Symptom | Likely cause |
|---|---|
| Server not visible in host | bad command/path, host not restarted, JSON config error |
| `-32602` or odd params errors | capability mismatch, wrong request shape, unsupported optional feature |
| Silent startup failure | missing env var, wrong working directory, import/runtime crash |
| Tool hangs | upstream I/O, missing timeout, blocked child process, waiting for unsupported callback |
| Host works differently than Inspector | host config/env differs from standalone run |

## Host-side debugging

- inspect desktop-host logs
- verify config paths and env
- if available, enable DevTools and inspect console/network behavior
- confirm the server appears in the host’s connected-servers UI

Windows Claude Desktop logs live under `%APPDATA%\Claude\logs`.

## Regression discipline

When you fix a failure:

- keep the smallest reproducer
- add or keep a harness/integration check for it
- remove temporary debug prints before finalizing

## Three-guess rule

If three plausible fixes fail, stop patching randomly. Re-open the initialize exchange, transport choice, env assumptions, and path handling.
