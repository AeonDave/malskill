# Runtime implementation

Use sections for components selected in the application contract. Command names here describe possible interfaces; document and test the names actually implemented.

## Helpers and output contracts

- Accept explicit input/output locations. Resolve bundled resources relative to the skill, not the caller's directory. Handle spaces, Unicode, and apostrophes without constructing shell command strings.
- Provide `--help`, validate before expensive work, and document dependencies, units, defaults, timeouts, and exit codes. Keep machine output parseable; send diagnostics separately.
- Version persisted contracts with downstream readers. Define required fields, types, allowed states, null handling, and relevant ordering. Reject unsupported versions with a recovery action; migrate only when needed.
- Check shape and meaning: ranges, evidence references, readability, and domain consistency. Valid JSON alone does not establish a correct result.
- Render reports from the validated result. Preserve unknown values and missing-evidence reasons. Compare repeat runs after normalizing declared volatile metadata; do not expect identical probabilistic conclusions.

For JSON, [`properties` does not require presence](https://json-schema.org/understanding-json-schema/reference/object): specify `required` separately and permit `null` explicitly where unknown is valid. Pin the schema dialect and use a compatible validator. Keep domain checks outside the generic schema when they require evidence or calculations.

## Sessions and recovery

Use sessions only for intermediate state or provenance.

- Allocate a stable unique run directory. Group inputs by one task or scene, not blindly by file. Record exact inputs; retain originals or immutable references and hashes where provenance matters.
- Store one authoritative run record: ID, contract version, input identities, timestamps, stage, limits, completed steps, result, checks, and artifact paths as needed. Use run-relative paths.
- Separate lifecycle from verification. Terminal runs can be complete, partial, unresolved, failed, or cancelled. “Complete” means the requested deliverable exists, not that every assertion is certain; store verification and reasons separately.
- Checkpoint meaningful progress. Resume steps only while inputs, configuration, and artifacts match; invalidate downstream results after changes. Detect dead workers before replacing them.
- Make retries idempotent: no duplicate report sections, evidence records, or external side effects. Retain previous results and provenance for corrections when auditability matters.
- Serialize writers or detect revision conflicts. Give locks owner identity and recovery rules; a PID alone can be reused. A stale `running` label is not proof of a live worker.

For Python single-file state, write a temporary file on the destination filesystem, close it, then use [`os.replace`](https://docs.python.org/3/library/os.html#os.replace). Handle replacement failure and retain previous valid state. This is not a multi-file transaction or a durability guarantee after power loss. For coordinated artifacts, publish a final manifest or commit marker only after referenced files validate; readers ignore unfinished generations.

Prefer stable directory names. If finalization renames a run, finish workers and release handles first, update paths, then verify readers and exports from the final location. On a Windows lock failure, stop only the owning app component and retry; preserve evidence.

## Evidence and finalization

- Link substantive claims to the exact input, source, operation, and artifact. Retain parameters, time, units, and source coverage when interpretation depends on them. Search/model rankings remain leads until the relevant claim is checked.
- Distinguish executed, passed, failed, skipped, and unavailable checks. Test whether an artifact supports the answer, not merely whether a suitably named file exists.
- Gate verified success on domain checks. For a user stop or waiver, retain the reason and emit a partial/unverified outcome; waived checks never become passed checks.
- Make finalization repeat-safe: validate current evidence, write the canonical result, render deliverables, reopen required files, then record delivery success. Failed rendering remains recoverable without repeating costly analysis.
- Keep artifacts within the declared output root. Check resolved paths, including symlink escapes, before serving or reading arbitrary files; scope cleanup to app-owned runs and caches.

## Doctor

Include a doctor when prerequisites can block or degrade the task.

Default checks are bounded and local: runtime, required executables/imports, bundled data/schemas, version compatibility, configuration validity, output writability, and relevant caches. A temporary writability probe cleans up only its own file. Diagnosis does not implicitly install packages, repair state, download models, or alter the system.

Offer machine-readable diagnostics when automation needs them. Each row identifies the check, affected capability, required/optional status, result (`pass`, `warn`, `fail`, `skipped`), observed detail, and remedy. Required failures produce a nonzero exit; missing optional capabilities warn unless explicitly required for this run. Explain skipped checks instead of treating them as success.

Network checks are explicit and bounded. Use a small known-answer probe when semantics matter; HTTP 200 establishes reachability only. Separate DNS/transport, authentication, permissions/quota, response shape, and usable content. Redact credentials and private inputs. Configured credentials do not prove authentication.

Keep expensive model/GPU checks and repairs separate from ordinary diagnosis. Print expected download/disk cost and the proposed command; execute within user authorization. Run doctor when needed on first use, after environment changes, or after a relevant failure; do not repeat healthy checks at every step.

## Services, cost, and optional UI

- Distinguish genuine empty results from absent coverage, service failure, malformed responses, and quota/auth errors. Bound retries/backoff; switch routes after unchanged failures. Cache with request identity, source, and freshness rules.
- Scope authorization to the task. Declare uploads, external writes, sensitive storage, and paid operations; a skill cannot grant authorization to itself. Keep credentials outside artifacts and command-line arguments.
- Start lightweight; estimate heavy work using actual size and measured rate. Checkpoint long jobs, expose progress/cancellation, and honor user limits without losing completed work.
- Add a viewer only when useful. Render persisted state; distinguish estimates, verified results, and unknowns. Display annotations must not silently overwrite the result.
- Local services bind loopback by default, isolate runs, serve intended files only, and stop only processes they own. Escape untrusted content; do not execute artifact-provided HTML or commands.
- Verify semantic state through the status interface and inspect displayed output. A healthy HTTP response is insufficient. Export offline artifacts when required; disclose network-dependent pieces.
- Define shutdown order for the actual lifecycle. Preserve final exports and release workers/handles; browser closure must not erase results or change verification.
