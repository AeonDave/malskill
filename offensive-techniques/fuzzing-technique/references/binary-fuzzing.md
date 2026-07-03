# Binary fuzzing methodology

## Primary objective

Find memory-safety and logic bugs with a pipeline that is fast, reproducible, and easy to triage.

## Pick execution mode by target reality

1. **Source available**
	- Prefer source instrumentation and narrow harnesses.
	- Persistent execution is typically the biggest throughput win.

2. **Binary only**
	- Use binary instrumentation/emulation workflow (dynamic rewriting, static rewriting, Intel PT, QEMU/Unicorn).
	- For full-system, kernel, or multi-process targets prefer snapshot/VM fuzzing (Nyx-class, LibAFL QEMU/hypervisor) over per-process instrumentation.
	- Expect lower exec/s and spend more effort on seed quality and timeouts.

3. **Mixed environment (local + CI + continuous)**
	- Keep one local exploratory campaign and one reproducible CI profile.
	- Reuse minimized corpus between runs.

## Campaign design

### 1) Prepare target and harness

- Keep harness stateless and deterministic across iterations.
- Ensure malformed input does not terminate the process except genuine faults.
- Build variants: high-throughput and sanitizer-focused.

### 2) Build seed corpus

- Collect valid samples from tests, bug reports, and real-world artifacts.
- Remove duplicates and minimize while preserving coverage.
- Add dictionaries for structured formats or keyword-heavy grammars.

### 3) Parallelize intentionally

- Use diversified instances (different schedules/mutators) instead of clones.
- Reserve at least one instance for comparison-guided or similar deep-input solving.
- Keep one coordinator/main synchronization role in multi-instance setups.

### 4) Track health, not just crash count

- Watch edge/feature growth trends and stability metrics.
- Apply memory/time bounds to prevent pathological inputs from starving cycles.
- If stability drops, inspect non-deterministic code paths before scaling out.

## Plateau playbook

If coverage stalls early:

- Narrow harness scope to the most complex parser/transform path.
- Improve dictionary and token extraction.
- Add fresh seed classes rather than only increasing run time.
- Enable value/compare guidance modes when available.

## Triage loop

1. Bucket crashes by stack signature and failure class.
2. Minimize each representative reproducer.
3. Confirm reproducibility under debug/sanitizer build.
4. Prioritize by exploitability signal and reachability.
5. Feed fixes/new constraints back into corpus and harness.

## Common failure modes

- Fuzzing full applications instead of focused entrypoints.
- Huge unminimized corpora causing long calibration and weak mutation efficiency.
- Running many identical instances with no strategy diversity.
- Ignoring startup seed crashes/timeouts that hide real signal.

## Related references

- AFL++ in-depth campaign flow and triage guidance.
- libFuzzer target constraints (determinism, speed, no exit-on-invalid input).
- Sanitizer profiles (ASan/UBSan/MSan/TSan/LSan) and their options (e.g. `abort_on_error`, `detect_leaks`, `allocator_may_return_null`, `symbolize`) surfaced through the tool-level skills.
- OSS-Fuzz reproducibility and coverage workflows.
