# Hypothesis Patterns

Domain templates for forming falsifiable hypotheses. Starting points, not a checklist to exhaust.

## Template

```text
H<n>: <cause> produces <symptom> via <mechanism>.
  Predicts:  doing <X> yields <Y>.
  Falsifier: doing <X> yields <Z> instead.
  Test:      <smallest experiment>.
```

Name a **cause**, a **mechanism**, and a **specific observable**. If any is missing, sharpen before testing.

---

## Observation matrix

Use this compact table when several runs differ by input, environment, or state. It prevents narrative drift.

| Run | Changed variable | Expected if H true | Actual | Verdict |
| --- | --- | --- | --- | --- |
| baseline | none | symptom present | pending | pending |
| control | safe/no-effect input | symptom absent | pending | pending |
| H1 test | one variable only | specific observable | pending | pending |

If two columns change in the same row, split the experiment.

---

## Debugging

| Class | Example hypothesis | Cheap falsifier |
| --- | --- | --- |
| Wrong state propagated | "Value V is corrupted before frame F because callee C mutates it." | Log V at entry/exit of C; expect unchanged. |
| Race / ordering | "Failure only occurs when thread A reaches X before thread B reaches Y." | Force ordering with a barrier or sleep; failure should disappear. |
| Boundary / off-by-one | "Loop overruns by 1 on inputs of size N=2^k." | Test sizes N-1, N, N+1; only N fails. |
| Environment / config | "Failure depends on env var E or config C." | Reproduce with E unset / C default; failure goes away. |
| Build / ABI mismatch | "Mixed compiler flags caused layout mismatch between caller and callee." | Rebuild both with identical flags; symptom changes. |
| Resource exhaustion | "FD/handle/mem leak triggers failure after N iterations." | Monitor resource; failure correlates with threshold. |
| Broken invariant | "Invariant I first becomes false between stages A and B." | Add assertion at A and B; A passes, B fails. |
| Wrong dependency origin | "Output O depends on stale value S, not current value C." | Trace reads/writes or slice O backward; S appears in the dependency path. |

Sharp predictions beat broad ones. Prefer "the value at offset 0x18 should be 0x41" over "things should look different."

### Reduction and minimization

When the reproducer is noisy, first hypothesize about the failure-inducing difference:

| Pattern | Example hypothesis | Cheap falsifier |
| --- | --- | --- |
| Input reduction | "Only token T is required to trigger the parser failure." | Remove all other tokens; failure remains. |
| Delta between pass/fail | "The failing config differs only by flag F." | Apply F to the passing config; failure appears. |
| Artifact minimization | "Only stream S in the PCAP matters." | Replay/extract S alone; symptom remains. |
| Code-path minimization | "Only function F is needed to reproduce." | Build a harness around F; full application not required. |

Reduction is useful only if the failure condition is precise. If minimization changes the exception, output, or oracle, mark the attempt inconclusive.

### Instrumentation and dependency tracing

- Give each probe a hypothesis ID: `H2 input_len=...`, `H3 branch=...`, `H4 invariant=...`.
- Log both the value and the context that makes it meaningful: input, version, thread/request ID, timestamp/order, environment.
- Prefer probes that answer "where did this value come from?" and "why did this branch execute?" over broad dumps.
- Remove temporary probes after the investigation, or convert durable ones into tests/assertions.

---

## CTF, exploit research, vuln triage

| Class | Example hypothesis | Cheap falsifier |
| --- | --- | --- |
| Attack surface category | "The bug is in input parsing, not in auth." | Send malformed input; observe whether failure occurs pre-auth. |
| Vulnerability class | "Parameter P is reflected unescaped (XSS) vs evaluated (SSTI/RCE)." | Send `{{7*7}}` and `<x>`; only one renders. |
| Oracle existence | "Server leaks timing on incorrect padding." | Compare timings for valid vs invalid pad on N samples; gap must be reproducible. |
| Memory primitive | "Overflow gives N-byte write at attacker-controlled offset." | Craft inputs of increasing length; observe controlled crash address. |
| Protection in effect | "ASLR is on for libc only, not for the binary." | Inspect `/proc/<pid>/maps` between runs; binary base stable, libc varies. |
| Side-channel | "Cache timing distinguishes secret bit k." | Run prime-probe N times; expect bimodal distribution. |
| Logic flaw | "Race between auth check and resource use allows TOCTOU." | Hammer the endpoint concurrently; success rate spikes above baseline. |

Bias toward experiments that **eliminate a whole branch**: knowing "it's not auth" is worth ten partial confirmations.

---

## Reverse engineering

| Class | Example hypothesis | Cheap falsifier |
| --- | --- | --- |
| Function purpose | "sub_401000 decrypts the config blob." | Feed known input/output via Frida or harness; outputs differ. |
| Algorithm identity | "The unknown routine is XTEA with key K." | Re-implement and compare on one block; mismatch. |
| Anti-debug technique | "Process exits early due to IsDebuggerPresent." | Patch the check; behavior changes only when patched. |
| Packing / encoding | "First stage decrypts a PE in section .data." | Dump memory after first jump; PE magic appears. |
| Network protocol field | "Bytes 4-7 are a length prefix in big-endian." | Send payload with mismatched length; server rejects predictably. |

Confirm guessed semantics with a **controlled input** before generalizing to the whole sample.

---

## Incident response and production failures

| Class | Example hypothesis | Cheap falsifier |
| --- | --- | --- |
| Recent change | "Deploy at T introduced the regression." | Compare error rate before/after T; rollback should restore baseline. |
| Dependency outage | "Upstream service S is the cause." | Check S's SLO/health at T; correlate latency. |
| Saturation | "Symptom is CPU/IO/memory saturation, not a code bug." | Plot utilization vs error rate; both spike together. |
| Config drift | "A non-deploy change (flag, secret rotation, DNS) coincides with onset." | Diff config snapshots around T. |
| Traffic shape | "Bug is triggered only by a specific request pattern." | Replay top N request shapes against staging. |
| Partial failure | "Only zone/shard/customer X is affected." | Slice metrics by zone/shard/tenant; isolate scope. |

Always include "blast radius" as an early hypothesis dimension: scope shapes both diagnosis and mitigation.

### Incident RCA distinctions

| Field | Question to answer | Failure mode |
| --- | --- | --- |
| Trigger | What activated the incident now? | Calling the trigger the root cause. |
| Root cause | What latent defect or system weakness made the trigger harmful? | Stopping at "traffic spike" or "human error." |
| Contributing factor | What amplified impact or slowed recovery? | Treating every contributor as equally causal. |
| Mitigation | What stopped user impact? | Confusing mitigation with prevention. |
| Action item | What measurable change prevents, detects, or limits recurrence? | Vague tasks with no owner or success condition. |

---

## Research and data-backed investigations

| Class | Example hypothesis | Cheap falsifier |
| --- | --- | --- |
| Population effect | "Variable V correlates with outcome O above noise." | Pre-register threshold; compute on held-out sample. |
| Source quality | "The discrepancy comes from dataset D's measurement bias." | Re-run analysis on independent dataset D'; effect changes. |
| Tool artifact | "The result is an artifact of parser P." | Re-parse with alternate tool; result diverges. |
| Causal vs correlational | "A causes B, not a shared confound." | Find a case where A varies while the suspected confound is held; B still tracks A. |

Write the prediction **before** running the query. Otherwise the analysis silently fits the data.
