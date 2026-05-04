# Agentic Workflow

Use this reference when the concise `SKILL.md` routing is not enough and the agent needs a step-by-step solve loop for miscellaneous multi-domain challenge solving.

## Triage loop

1. **Artifact inventory** — list files, endpoints, binaries, captures, transcripts, source code, models, or notes.
2. **Dominant primitive** — identify whether the solve hinges on math, parsing, memory control, protocol state, public-source correlation, model behavior, or reporting.
3. **Technique handoff** — load the first matching methodology skill: `crypto-technique`, `reversing-technique`, `post-exploit-technique`, `wireless-technique`, `network-technique`.
4. **Tool selection** — choose from: `offensive-tools/cryptography/cyberchef`, `offensive-tools/network/netcat`, `offensive-tools/network/wireshark`, `offensive-tools/wireless/aircrack-ng`, `offensive-tools/wireless/kismet`, `coding/python-patterns`, `coding/systematic-debugging`.
5. **Proof construction** — build the smallest script, query, exploit, decode chain, or analysis trace that demonstrates progress.
6. **Validation** — prove the result by replay, decryption check, crash control, request/response evidence, extracted artifact, or independent correlation.
7. **Writeup capture** — log only the final path plus meaningful failed hypotheses.

## Useful generic patterns from writeup research

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific pivots

- Classify the primitive, not the category label: parser, sandbox, encoding, RF, protocol, game logic, or host privilege boundary.
- Use shortest deterministic transform chain first; avoid speculative brute force until representation is known.
- For jail and VM tasks, map constraints then build minimal escape or emulator.

## Tool handoff rules

- Load tool skills for syntax and flags after this workflow selects the tool family.
- Load coding skills when a custom solver, parser, harness, exploit script, or emulator is needed.
- Load verification/evidence skills before final reporting when the result must be reproducible.
- If two categories compete, run the cheaper validation first and document why the other path waits.

## Stop conditions

- Objective proof recovered and replayable.
- Current hypothesis falsified by exact evidence.
- Required artifact, credential, oracle, or authorization is missing.
- Further action would be destructive, noisy, or outside the lab/scope boundary.
