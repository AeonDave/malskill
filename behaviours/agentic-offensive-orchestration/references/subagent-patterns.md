# Subagent Patterns

Use subagents for bounded offensive research, artifact analysis, implementation, or review tasks where fresh context improves quality and the work can be verified independently.

## Minimal prompt packet

Include:

- objective: one sentence with success signal
- mode: pentest/red-team, CTF/lab, artifact triage, exploit research, tool/skill curation, or code/tool development
- topology: single operator, supervisor-light, or swarm-lite; include why this branch is independent
- role and loaded skills: role/skill names the worker must load, not source paths
- model tier: cheap, standard, diverse standard, premium, or rescue; include why the cost is justified
- inputs: paths, URLs, artifacts, command outputs, assumptions already verified
- boundaries: authorized target/lab scope, destructive/noisy limits, files that may be changed, time budget
- allowed MCP/tools: exact lanes such as Tavily, fetch, GitHub search, debugger, scanner, or read-only file tools
- prohibited actions: live target contact, external submission, credential validation, payload execution, shared-file edits, or data exposure
- output format: bullets, table, patch summary, source ledger, evidence packet, or handoff package
- stop rule: when to ask, hand off, or return `blocked` instead of guessing

For public research tasks, include a public-safe query boundary. Do not let workers send hostnames, IPs, internal emails, secrets, proprietary snippets, private crash data, customer names, or unpublished vulnerability details to Tavily, search engines, sandboxes, public APIs, or LLMs unless explicitly approved.

## Role routing hints

- Sparse CVE/exploit/writeup/source clue -> `offensive-researcher-role`.
- Disk/memory/PCAP/log/media/evidence bundle -> `offensive-forensic-role`.
- Unknown local challenge or flag-style artifact -> inspect the artifact briefly, then load the closest category `*-ctf`.
- Web/API/browser/auth -> `offensive-web-role`.
- Cloud/SaaS/IAM/storage/workload -> `offensive-cloud-role`.
- Windows host/AD/Kerberos/AD CS/SMB/shares/accounts -> `offensive-windows-role`.
- Linux host/session/container/SSH/services/network paths -> `offensive-linux-role`.
- Binary/malware/firmware/protocol -> `offensive-reverse-role` or `offensive-exploit-role` depending on whether the question is understanding or exploitability.
- Crypto/hash/token/oracle -> `offensive-crypto-role`.
- Public identity/domain/supplier/reputation -> `offensive-osint-role`.

## Parallelism rules

## Spawn decision

- **0 workers**: small source, one endpoint/artifact cluster, clear oracle, one likely primitive.
- **1 worker**: independent source review, traffic map, artifact map, lab replica, or research lane can run while the operator probes or reviews.
- **2 workers**: source/runtime, auth/surface, forensic/research, or build/review branches have independent inputs and merge cleanly.
- **3+ workers**: only when every branch has distinct context, oracle, or decision boundary; define merge format before launch.
- **Evidence reviewer**: after decisive claim only, not by default.
- **Research fan-out**: allowed only with distinct model/source scope/context packets and explicit merge criteria.

## Dispatch and lifecycle

- Use sync by default.
- Use async only when the branch is independent, output format is predefined, and the main operator can make real progress elsewhere.
- If async would lead to waiting or polling, run sync instead.
- Re-topologize after two failed pivots, source/runtime contradiction, branch merge, or stale worker detection.
- Split, fuse, suspend, or kill workers as evidence changes. Retire stale or duplicate workers immediately after merge point.
- Do not split two workers onto the same primitive unless one builds and one reviews.
- Merge when a primitive is confirmed, disproved, or needs another branch output.

## Model ladder

- **Cheap**: triage, route maps, source skim, negative filtering, file inventory.
- **Standard**: default solver, researcher, worker, and reviewer.
- **Diverse standard**: second opinion when disagreement is useful and context/method differs.
- **Premium**: bounded synthesis after concrete dead end and sharp question.
- **Rescue**: one stuck branch at a time, with exact evidence, failed pivots, and local oracle.

Do not escalate for uncertainty alone. Before premium/rescue, exhaust cheap validation: routes, trust boundaries, parser/proxy behavior, auth/session handling, env drift, build-vs-runtime mismatch, and target-version evidence.

## Local replica / lab-builder branches

Create a local replica when target behavior depends on exact versions, framework defaults, parser quirks, race timing, serialization, middleware order, sandbox rules, or build/runtime drift.

Requirements:

- match known target evidence: version, config, route, parser, dependency, container, or runtime clue;
- answer one narrow question with a defined oracle;
- prefer Docker when it makes version replication cheaper or cleaner;
- record setup, result, and divergence notes;
- discard the lab result when it diverges from target behavior.

WEB examples: Express query parser coercion, Flask/Jinja versions, Spring binding behavior, Apache `.htaccess` handlers, proxy rewrite order, SSRF redirect handling, browser bot referrer/cookie behavior.

Parallelize only when:

- tasks do not mutate the same target or files
- outputs can be validated independently
- rate limits/noise are understood
- failure of one task does not invalidate another mid-run
- external research queries are public-safe and source limits are explicit

Keep serial when:

- exploit steps depend on previous primitives
- one task may change target state
- root cause is unknown and broad parallel fixes would hide evidence
- two workers would race on the same branch or artifact
- two workers would submit the same private data to external services
- CTF/lab route is still unknown; classify first, then split

## Blackboard

Maintain this shared state across workers and main operator:

| Field | Contents |
|---|---|
| Facts | confirmed observations only |
| Hypotheses | theory, confidence, disproof test |
| Artifacts | source refs, requests/responses, logs, tokens, scripts, hashes |
| Attempts | test -> output -> interpretation -> next |
| Dead paths | failed branches worth remembering |
| Queue | next cheapest discriminating tests |

## Output synthesis

Collect outputs into:

| Field | Required content |
|---|---|
| Fact | Evidence-backed observation |
| Evidence | Artifact, command, location, or citation |
| Confidence | confirmed, high, moderate, speculative, unknown |
| Risk | scope, noise, destructiveness, false-positive risk |
| Next action | smallest safe verification or implementation step |

Add `Negative finding` and `Conflict` rows when a worker disproves a path or sources disagree. These prevent repeated dead-end research and make pivots faster.

## Review checklist

- Did any worker exceed scope or assume authorization?
- Are claims backed by fresh evidence rather than reputation or tool output alone?
- Did MCP/Tavily/search queries stay within the approved public-safe boundary?
- Do workers contradict each other? If yes, preserve the conflict and resolve with targeted checks.
- Did any worker keep retrying after two failed evidence-based pivots?
- Did the main operator keep making progress while async workers ran?
- Should any worker be retired, fused, split, or escalated after merge evidence changed?
- Is the selected model tier justified by task complexity and current evidence?
- Is final synthesis shorter and clearer than the raw worker outputs?
