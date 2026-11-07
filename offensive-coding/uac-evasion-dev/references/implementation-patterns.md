# UAC Evasion Implementation Patterns

Load when writing the bypass itself. Field-reported patterns include project-relative source labels, but no revision-bound qualification record is linked here. Public catalog references establish attribution, not runtime compatibility.

## UnifiedConsent side-load (UACME #83, valid since 19041)

Public catalog entry: [UACME #83](https://github.com/hfiref0x/UACME) — auto-elevated scheduled task `\UnifiedConsent\UnifiedConsentSyncTask` runs `taskhostw.exe` high-integrity, which side-loads `unifiedconsent.dll` from a redirected user path.

Implementation shape (field-reported, project evidence: AshuraLoader `uac_unifiedconsent.rs` / `elevation.md`):

1. Set `HKCU\Volatile Environment\SystemRoot` = `%TEMP%` — per-user `SystemRoot` override redirects the task's DLL resolution.
2. Create `%TEMP%\System32\` and plant the payload there as `unifiedconsent.dll`.
3. Create junction `%TEMP%\Registration` → the real `Registration` directory (keeps the task's COM registration resolution intact).
4. Signal the **WNF state** that wakes the sync task (literal state name split `a−b` per build seed in the project — field-reported detail; the public UACMe source shows the equivalent trigger).
5. Wait on a seed-derived event (~300 s floor), with 50–400 ms jitter on the setup steps.
6. Cleanup: restore `SystemRoot`, remove junction, delete `%TEMP%\System32\unifiedconsent.dll`.

Build floor ≥ 19041; qualified on Win11 26300 (project evidence). The planted DLL must export the entry the task expects or the load fails silently — verify the export forwarders against the real `unifiedconsent.dll`.

## Chain orchestration (UAC → admin → SYSTEM)

Field-reported (project evidence: AshuraLoader `chain.rs`, `remote.rs`):

```
medium bootstrap (this EXE)
  ├─ UAC bypass → high-integrity child (admin injector), separate process
  │    └─ SYSTEM delivery: pick a SYSTEM, non-PPL, non-critical host with a
  │       thread-pool (WmiPrvSE → spoolsv → BITS svchost), patch a worker
  │       start-routine trampoline (12-byte), bump WorkerFactoryThreadMinimum,
  │       self-disarming stub restores routine + minimum after delivery
  └─ ownership arbiter: first process to NtSetEvent-observe state 0 owns the
     outcome; ambiguous state ⇒ abort (never double-fallback)
```

Design rules:
- The SYSTEM delivery stub must be **self-disarming**: it restores the original start routine and worker minimum itself, so the elevated/injected context heals without a babysitter.
- Keep the bootstrap alive only as failure reporter; kill it as soon as the arbiter resolves.
- Deliver into SYSTEM hosts that are non-critical: killing the wrong svchost is availability damage and an immediate IR.

## SYSTEM vectors in the chain (field-reported)

- **RushPotato** (project-invented — not public): service COM class activation (`McpManagementService`), IStorage in-memory wrap, OBJREF moniker with attacker-controlled display name, `CoGetInstanceFromIStorage`, per-callback impersonation gated on `S-1-5-18` + `SecurityImpersonation`. Qualified runtime on Win11 26300 (C and Rust).
- **OXID dispatch-hook** (mechanics project-verified, runtime **not** qualified on 26300 — RPCSS no longer connects; same failure observed in public tools): hook dispatch entry 0 of `RPC_SERVER_INTERFACE` in `combase.dll`, serve OBJREF over `\\.\pipe\<seed>\pipe\epmapper`, `FSCTL_PIPE_IMPERSONATE`, `CreateProcessWithTokenW`. Re-qualify per build before shipping.

Full public potato-family catalog (GodPotato, SweetPotato, RoguePotato, …): `post-exploit-technique/references/windows-privesc.md` §1.

## Cleanup ledger pattern

Every bypass writes state; enumerate it as a table processed in reverse order:

| Artifact | Cleanup trigger | Verification |
|---|---|---|
| Registry value (`SystemRoot`, progid class) | After elevated payload start signal | Re-read key, expect original |
| Planted file (dll/dummy) | After DLL load confirmed (or process exit of the elevated host) | `GetFileAttributes` = not found |
| Junction/redirect | Same as file | Re-parse path |
| WNF/event state | Never manually — state is transient | n/a |
| Child process tree | Arbiter resolution | `NtTerminateProcess` on own children |

Cleanup must run in the **medium-integrity bootstrap** where possible (it owns the writes); the elevated child only cleans what only it can (e.g. keys written by the elevated side).

## BOF integration skeleton

```c
// bypass as BOF: the agent stays the C2 owner
void go(char* args, int len) {
    // 1. enumerate policy; bail if ConsentPromptBehaviorAdmin == 0
    // 2. stage payload where the chosen family delivers it
    // 3. trigger the auto-elevate path (task/COM/binary)
    // 4. wait on completion event (bounded!)
    // 5. BeaconPrintf status; cleanup per ledger
}
```

Keep the elevated payload's C2 channel identical to the agent's (pipe/socket callback into the same listener). A second session = doubled telemetry and a broken process tree in the operator view.

## Anti-patterns

- Shipping the stock fodhelper/eventvwr payloads unmodified — the most signature-checked family on 2026 rulesets.
- Leaving the planted DLL/key behind after success (cleanup is the bypass's second half).
- Retrying the trigger in a loop on failure — each iteration is an independent alert.
- Running UAC bypass and SYSTEM vector in the same process — a potato-family crash kills the bootstrap and the cleanup ledger with it.
- Assuming method validity from the UACME catalog age: methods die with Windows updates; live-test per build.
