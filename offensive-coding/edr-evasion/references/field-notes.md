# Field Notes — S1/CS/Defender Tested Failures

Assumptions disproven by field testing (2026-03-31). Each entry cost measurable time or produced a detection regression.

---

## Disproven Assumptions

### 1. "Selective ETW suppression will satisfy S1" (F6)

S1 correlates CLR-loaded + CLR-ETW-absent = bypass. Non-CLR telemetry is irrelevant. Fix: F7 — disable DR0 entirely. ~80 lines of F6 filtering code wasted.

### 2. "More HWBP coverage = better evasion" (F2)

Each active DR is a "breakpoint without debugger" signal. Re-issued indirect_syscall adds "direct syscall from patched library." F2 expanded 4→11 targets, increasing detection. Fix: F9 — remove ALL HWBP from tool_mode.

### 3. "Indirect syscall > direct ntdll stubs" (pre-F9)

S1 validates syscall instruction address against known stub entry points. Gadget dispatch triggers detection. For backed EXE, real hooked stubs generate zero syscall indicators. Fix: F9 — PEB-resolved direct calls.

### 4. "Gating call sites removes code from binary" (F9 ph1-2)

At opt-level=0, ALL function definitions compile regardless of reachability. Dead function bodies contain `0F 05`, `mov eax, ecx; jmp r11` — statically detected. Fix: F9 ph3 (nop stubs) + ph4 (gate definitions with `#[cfg]`).

### 5. "VEH registration is invisible if handler is no-op" (pre-F9 ph5)

S1 detects VEH registration call PATTERN in .text, not handler behavior. Fix: `#[cfg]` gate VEH registration block — physically absent from tool_mode.

### 6. "SilentMoonwalk helps backed EXE" (pre-F9)

Backed .text IS a legitimate return address. SMW adds complexity + requires indirect_syscall + VEH + HWBP = 3 indicators for zero benefit. Fix: skip SMW in tool_mode. Essential for beacon (unbacked).

### 7. "More evasion features = better evasion"

1,472 lines (zero VEH/HWBP/unhooking) evades fully. 6,126 lines (all features) is detected. Every feature added to address theoretical weaknesses introduced 1-3 new real indicators. Fix: §0 minimalism — start minimal, add only when confirmed.

---

## S1 Indicator Reduction Audit

| Change | Real reduction? |
|--------|----------------|
| B1 (private RWX) | **Yes** — section kernel signal eliminated |
| F7 (disable ETW DR0) | **Yes** — ~8→~4, "ETW bypassed" eliminated |
| F9 ph3-5 (eliminate syscall/VEH/HWBP) | **Yes** — ~4→~1, 3 indicators eliminated |
| F6 (selective ETW) | **No** — S1 still detected CLR gap |
| F2 (4→11 targets) | **No** — more DRs = more signals |
| F9 ph1-2 (gate call sites only) | **No** — dead code retained signatures |

Remaining irreducible: "Malicious shellcode execution" (private RWX + PEB walk + dynamic API).

Field results: see `AGENTS.md` → Field results table.

---

## CrowdStrike Regressions (confirmed — do not reintroduce)

1. **PE header stomp**: `map → execute → zero first 0x1000` = CS shellcode loader signature (60%→90%)
2. **AMSI propagation in NtCreateThreadEx hook**: PEB walk + resolve AmsiScanBuffer + SetThreadContext inside hook body = CS SharpBlock signature (60%→90%)
3. **Removing `panic_abort`**: reintroduces Rust unwinding strings (`attempt to divide by zero`, `library/core/src/...`). Always use `build-std = ["std", "panic_abort"]` + `panic = "immediate-abort"`.

These are the three CS-specific regressions distinct from S1 findings. CS and S1 share general indicators but differ on these three.
