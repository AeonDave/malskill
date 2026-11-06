# Assessment coverage and scanner findings

Load when starting from an asset inventory, planning checks across services or applications, or investigating scanner output.

## Turn inventory into questions

- Reuse the recon inventory. Confirm the identity needed for the next check: service/product, endpoint or virtual host, relevant build/configuration, and authentication state. Record uncertain fingerprints; a banner may describe an intermediary or omit a vendor backport.
- Keep a compact coverage record: **asset/surface → role and conditions → security question → check → evidence/outcome → next action**. Separate anonymous and authenticated coverage, and distinguish tested surfaces from merely discovered ones.
- For published version/configuration claims, load [cve-search](../../cve-search/SKILL.md). For custom behavior, choose hypotheses from trust boundaries, input processing, object ownership, and state transitions. Do not wait for an empty scanner report before examining application logic.
- Select automated checks by the behavior they exercise, supported technology, and required prerequisites. Add another tool only when it covers a concrete gap; scanner count, template count, and severity filters do not establish coverage. Use each selected tool's skill for syntax.
- Prioritize consequential reachable surfaces and checks that reduce uncertainty. Use targeted fuzzing or source/binary analysis when the question requires them; keep those workflows in their existing skills.

## Verify the reported signal

Retain the scanner/script/template identity and revision, target, parameters, required session state, and raw observations. Determine what actually matched: a version, status, response fragment, timing observation, or application effect. Treat that match as a lead until the research workflow supports its claimed meaning.

Replay the discriminating request or operation with its prerequisites and meaningful controls. When the result is ambiguous, test the relevant alternative explanation:

- **Wrong responder:** redirects, virtual-host routing, a gateway or WAF produced the response rather than the intended application path.
- **Generic response:** a soft error, common page, reflected marker, or cached result also satisfies the match on the control.
- **Wrong state:** an expired session, different role/tenant, stale object, or prior attempt changed what the request actually exercised.
- **Timing/noise:** load, retries, transport failure, or rate limiting explains a delay or missing response.

Keep the full sequence when state matters. Verify the returned content or resulting state, rather than accepting a path's existence, HTTP status, or scanner severity as impact. If the control also matches, revise the test; if the intended path cannot be reached, record the blocked validation rather than declaring the asset unaffected.

## Close with coverage and evidence

Consolidate reports by supported cause and affected conditions, retaining every affected surface. Multiple tools reporting the same symptom are not independent confirmation; the same vulnerability label on one endpoint may still describe distinct causes.

For each priority surface, distinguish **not tested**, **attempted but incomplete**, and **tested under stated conditions**. Attach candidate, reproduced, rejected, or unresolved findings separately. A completed scan with no findings closes only the checks and conditions it actually exercised.

Deliver the reproducible findings with their controls, coverage gaps, and next useful checks. Keep the tested actor/role, configuration, timestamps, and evidence paths with the result so another researcher can reproduce the decision without rerunning discovery.
