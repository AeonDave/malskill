# Decision and Error Journaling

**Load when**: you route a non-trivial delegation, or a worker leg fails and you must report the failure upward without flattening it.

Two halves of one auditable delegation trail. The decision journal records *why you routed*; the error chain records *why a leg died*. Together they make the attack tree replayable and let the next operator act on root cause, not on "job failed".

## Contents
- Decision journal (per routing/delegation decision)
- Good vs bad reasoning diagnostic
- Error-chain preservation (multi-level failure wrapping)
- Rules

## Decision journal

Log each non-trivial routing/delegation decision. One entry:

```yaml
question:            # The decision. e.g. "Which role validates the /admin bypass lead?"
options_considered:  # Real alternatives weighed.
                     # e.g. ["web-role manual replay", "researcher-role CVE lookup first"]
chosen:              # The pick. e.g. "web-role manual replay"
reasoning:           # The DECISIVE why. e.g. "Bypass looked like logic flaw in the app,
                     #  not a known CVE; manual replay is faster and lower-noise than
                     #  chasing an advisory that may not exist."
confidence:          # 0.0-1.0. Your calibrated belief the choice is correct. e.g. 0.7
```

Keep entries in the attack tree, not the final report (unless a decision is itself a finding).

## Good vs bad reasoning diagnostic

When a delegated leg fails, read the entry that routed it:

- **Wrong decision + GOOD reasoning** → the logic was sound; the INPUT was bad. Bad/stale target data, wrong creds, changed surface. Fix the data, re-dispatch — do not change how you route.
- **Wrong decision + BAD reasoning** → the routing LOGIC is broken. You sent the wrong role, or split the task wrong. Fix the routing rule, then re-dispatch.

This split tells you whether to re-feed or re-think. Low `confidence` on a failed leg is an early signal the reasoning was the weak link.

## Error-chain preservation

Never flatten a worker failure to "job failed". Each level WRAPS the level below: it preserves the original failure verbatim and adds its own `recovery_attempted`. The **root cause must survive to the supervisor's report and to the operator's next decision.**

```yaml
# Worker level (offensive-web-role)
worker_failure:
  action: "sqlmap on id param, then manual UNION replay"
  observed: "sqlmap returned WAF 403 on payload ' OR 1=1-- ; edge dropped the request"
  recovery_attempted: "retried with tamper=space2comment, then manual inline comment
                       /**/ variant; both still 403"
  root_cause: "WAF signature-blocks the injection at the edge"

# Supervisor level (wraps the worker)
supervisor_failure:
  leg: "web-role SQLi validation on /product?id="
  wrapped: *worker_failure          # original preserved, not summarized away
  recovery_attempted: "re-dispatched with encoded payload set; same 403 class"
  root_cause: "WAF at edge blocks SQLi payloads; this vector is dead until WAF-evasion
               tradecraft or a different injection point is found"
  next: "route offensive-researcher-role for WAF-bypass technique, OR pivot to another param"
```

## Rules

- **Preserve, do not paraphrase**: the worker's exact `observed` string (tool output, status code, error) rides up untouched. Paraphrase loses the detail the next operator needs.
- **Add, do not replace**: each level appends its own `recovery_attempted` + `root_cause`; it never overwrites the level below.
- **Root cause is mandatory upward**: a wrapped failure with no `root_cause` is incomplete — the supervisor cannot decide the next move from "it failed".
- **Failure feeds a decision**: end every wrapped failure with `next` (pivot, re-dispatch, or mark path dead). Tie it to a fresh decision-journal entry.
- **Dead path once, not thrice**: if the same vector fails after bounded retries, mark it dead in the tree (see loop protection in `agentic-offensive-orchestration`); do not re-route the identical leg.
