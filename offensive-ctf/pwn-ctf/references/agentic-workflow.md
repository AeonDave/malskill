# Agentic Workflow

Use this reference when the concise `SKILL.md` routing is not enough and the agent needs a step-by-step solve loop for binary-exploitation challenge solving.

## Triage loop

1. **Artifact inventory** — list files, endpoints, binaries, captures, transcripts, source code, models, or notes.
2. **Dominant primitive** — identify whether the solve hinges on math, parsing, memory control, protocol state, public-source correlation, model behavior, or reporting.
3. **Technique handoff** — load the first matching methodology skill: `reversing-technique`, `vuln-exploit-technique`, `fuzzing-technique`.
4. **Tool selection** — choose from: `offensive-tools/network/pwntools`, `offensive-tools/rev/gdb`, `offensive-tools/rev/radare2`, `offensive-tools/rev/ghidra`, `coding/asm-patterns`, `coding/asm-testing`, `offensive-coding/rop-development-dev`, `offensive-coding/heap-exploitation-dev`, `offensive-coding/shellcode-dev`.
5. **Proof construction** — build the smallest script, query, exploit, decode chain, or analysis trace that demonstrates progress.
6. **Validation** — prove the result by replay, decryption check, crash control, request/response evidence, extracted artifact, or independent correlation.
7. **Writeup capture** — log only the final path plus meaningful failed hypotheses.

## Useful generic patterns from writeup research

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific pivots

- Triage binary and mitigations first; prove exact controlled primitive before payload engineering.
- Build exploit in stages: local repro, info leak, base calculation, control-flow/data-only effect, remote adaptation.
- Keep offsets, libc/loader assumptions, and environment drift explicit.

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
