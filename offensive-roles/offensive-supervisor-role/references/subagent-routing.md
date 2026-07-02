# Subagent Routing and Context Packaging

**Load when**: you are about to delegate a task to a specialized worker role or subagent and must write the dispatch prompt.

A worker starts **cold**. It never sees the conversation, the attack tree, or prior tool output — it inherits ONLY the dispatch prompt. Anything you omit is lost. Anything you over-share is leaked context the worker does not need (least-context). So every delegation carries a structured context block. Topology choice (hierarchical vs blackboard), MCP-C2, and loop protection live in `agentic-offensive-orchestration` — do not restate them here.

## Context block (fill every field, per dispatch)

```yaml
objective:        # ONE verifiable task + the exact success signal.
                  # e.g. "Confirm /admin is auth-bypassable. Success = HTTP 200 admin
                  #       dashboard body returned with no valid session cookie."
scope_roe:        # In-scope targets (host/URL/CIDR); hard boundaries (never touch X);
                  # noise + destructive limits (e.g. "no exploitation of prod DB rows").
position:         # Foothold/creds/host/privilege the worker NEEDS to start — and nothing
                  # it does not. e.g. "unauth, external. edge = nginx 1.24. cookie SESSION=...".
                  # Least-context: a web worker gets the URL + auth model, NOT the nmap sweep.
constraints:      # Tactic limits. e.g. "no brute force", "single benign payload per point",
                  # "stop on WAF 403", "manual curl/python replay, no sqlmap/nuclei".
required_artifacts: # EXACT proof to return. e.g. raw HTTP request+response, command+stdout,
                  # hash, screenshot path. No prose-only summaries.
stop_conditions:  # When to abort and report back. e.g. "WAF block", "lost connection",
                  # "3 failed attempts on same vector", "creds needed you were not given".
```

## Rules

- **Role first line**: name the assumed role in line 1 (e.g. "Act as `offensive-web-role`.") so the worker loads the right methodology.
- **Least-context**: pass the minimum foothold state the objective requires. A worker exploiting SQLi does not need the port scan; give the URL + vuln class only.
- **One objective per dispatch**: split multi-target or multi-phase work into separate delegations. A worker with two goals hallucinates a plan.
- **Artifacts are mandatory**: if `required_artifacts` is vague, the worker returns "it worked" and you cannot verify. Specify the exact bytes/output you will re-check.
- **Reject on missing proof**: if a worker returns without the required artifacts, reject the submission and re-dispatch with the capture step explicit. Do not backfill the proof yourself.
- **Log the routing choice**: record why THIS role got THIS leg — see `decision-and-error-journaling.md`.

## Worked dispatch

```yaml
# Act as offensive-web-role.
objective: "Confirm SSTI in the /greeting name param. Success = arithmetic payload
            {{7*7}} reflected as 49 in the rendered HTML response body."
scope_roe: "In-scope: https://<target>/greeting only. No other endpoint. Non-destructive."
position: "Unauth, external. Jinja2 suspected (Flask Werkzeug 500 page seen). No creds."
constraints: "Single benign math payload per test. No RCE payloads. Stop on WAF 403."
required_artifacts: "Raw request line + body, raw response body showing the reflected value."
stop_conditions: "WAF 403, 3 non-reflecting payloads, or any 5xx storm."
```
