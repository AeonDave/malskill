# Cross-Platform Offensive Dev Best Practices

Load when designing a new loader / implant / tool or auditing an existing one. Applies to Windows and Linux; examples cite platform-specific constructs.

Doctrine: signal minimization + indistinguishability, never invisibility. Every construct is a detection surface. Ship the smallest thing that clears the target's sensor stack for the operation profile.

Canonical homes for content that could otherwise duplicate here — do not restate:

- Evasion minimalism principle & feature-add gate: `SKILL.md` §0.
- Loader execution ordering: `SKILL.md` §0a.
- Cleanup order: `SKILL.md` §7.
- Section-ratio and encryption rules: `SKILL.md` §10, §11.
- Kernel-visible signal ceiling: `references/kernel-telemetry.md`.
- Disproven assumptions: `references/constraints.md` → Disproven Assumptions.

---

## 1. Threat model gate

Name these before writing code. Unknown → run enum first (`kernel-telemetry.md` fingerprint block; `linux-edr-evasion.md` §1).

- **Target EDR**: product + agent version (Falcon 8.x, Defender build, S1 x.y, Falco 0.x, Tetragon x.y, Elastic Defend x.y).
- **Deployment mode**: block / alert / monitor-only.
- **Sensor stack actually running**: usermode hooks, kernel callbacks, ETW-TI, eBPF, LSM BPF, auditd.
- **Operation profile**: one-shot tool / long-running beacon / silent persistence.
- **Burn cost of detection**: operator burn / payload burn / technique burn.

Design against the sensor stack that is actually there. Designing for the worst possible EDR yields a loader that trips weaker ones on primitives it didn't need.

---

## 2. Signal-cost budget

Weight every construct. Sum per stage. Ship only when the subtotal is below the target's correlation threshold. Recalibrate weights per target after enum.

| Weight | Windows | Linux |
|---|---|---|
| 0 (free) | PEB byte read, RDTSC delta, `KUSER_SHARED_DATA` read | vDSO `clock_gettime`, `/proc/self/status` read, `getauxval` |
| 1 (low) | `NtWriteVirtualMemory(-1,self)`, module-stomp write, indirect syscall on unbacked | LD_PRELOAD hook, io_uring op on Falco <0.40, `mprotect(RW)` |
| 2 (medium) | `NtProtectVirtualMemory(RW→RX)` private, `NtCreateThreadEx(self)`, ETW-TI event 25/27 | `memfd_create`+`fexecve`, `process_vm_writev`, `openat(/etc/*)` |
| 3 (high) | Cross-process `NtWriteVirtualMemory`, VEH register, `SetThreadContext(DR7!=0)`, private RWX, ETW-TI event 24 | `execve`, `connect`, `ptrace`, `bpf(BPF_PROG_LOAD)`, `finit_module` |
| 4 (loud) | LSASS handle open, PPL bypass, `NtLoadDriver`, ObRegisterCallbacks-blocked ops | `openat(/etc/ld.so.preload,O_WRONLY)`, cross-namespace pivot, kernel-object hiding |

Rule: any stage subtotal > 8 → split the stage or drop a construct. Loader / injection / C2 stages should stay ≤ 3 medium items each.

Budget worksheet (per stage):

```
Stage: <name>
  Construct                 Weight   Suppressor / why unavoidable
  ────────────────────────  ──────   ───────────────────────────
  <api / syscall>            <n>     <what quiets it, or "must accept">
  ...
  ────────────────────────
  Subtotal                  <sum>    Target: <threshold>
```

---

## 3. Multi-stage architecture

Hard boundaries between stages. Each stage compiled as a distinct artifact where feasible. One binary that contains multiple stages' feature sets carries the **union** of their signatures.

| Stage | Purpose | Allowed constructs | Exit boundary |
|---|---|---|---|
| S0 dropper | Enum sensor stack; decide continue / abort | Passive only (weight ≤ 0); no `Nt*` beyond `NtQueryVirtualMemory` | Discards itself; passes fingerprint to S1 via inline blob or stdin |
| S1 loader | Setup: syscall dispatch, spoof state, ETW policy, memory arrangement | All evasion features live here, `#[cfg]`/`#ifdef`-gated on S0's fingerprint | Terminates before S2 runs — `SKILL.md` §0a |
| S2 payload | Business logic (C2, collection) | Minimal syscall surface; does **not** re-establish S1's primitives (`SKILL.md` §0a) | Cleanup handoff or `ExitProcess` |
| S3 cleanup | Zero, unmap, free (`SKILL.md` §7) | No new evasion features | Process exit |

Rules:

- Different stages get different feature sets. Do not fold S1's syscall gate and S2's C2 crypto into one binary unless the target actually exercises both.
- No stage reopens a signal a previous stage closed. Reintroducing `VirtualProtect` in S2 when S1 established byte-patch ETW via `NtWriteVirtualMemory` wastes S1's budget.
- Feature ownership: each evasion feature belongs to exactly one stage. Cross-stage feature-flag drift is an anti-pattern (§9).

---

## 4. Feature-gate discipline

Gate every optional evasion feature at the **definition** site, not the call site. Verified failure mode is in `constraints.md` → Disproven Assumptions → "Gating call sites removes bytes".

Rust:

```rust
#[cfg(feature = "hwbp")]
mod hwbp { pub fn arm(...) { ... } }

// Not: fn arm() { if cfg!(feature="hwbp") { ... } else { return; } }
```

C/C++:

```c
#ifdef FEATURE_HWBP
static void arm_hwbp(void) { ... }
#endif
```

Verification after every gate change:

```powershell
# Windows: syscall / gadget patterns for a disabled feature must be absent.
dumpbin /disasm build\loader.exe | Select-String -Pattern '0f 05|jmp r11'
```

```bash
# Linux
objdump -d build/loader | grep -E '0f 05|jmp r11|syscall'
size build/loader                    # delta must match the gated feature's cost
strings build/loader | grep -i hwbp  # symbol names must be gone too
```

Pattern grep hitting for a disabled feature → gate is at call site only. Fix at the definition.

---

## 5. Build & compile hygiene

Rust (both platforms):

- Cargo `release` profile: `panic = "abort"`, `lto = true`, `codegen-units = 1`, `strip = "symbols"`, `opt-level = 1` (validate against `SKILL.md` §11 section-ratio table before changing).
- Flags: `RUSTFLAGS="-C panic=abort"`. For maximum panic-string stripping (nightly): `-Zbuild-std=std,panic_abort -Zbuild-std-features=panic_immediate_abort`.
- Post-build path-leak check: `strings target/release/loader | grep -Ei 'target/release|cargo|rustup|/home/|/users/|maldev|src/main'`. Any hit → move build into a sanitized sysroot or remap paths (`--remap-path-prefix`).

Windows PE:

- MSVC: `/GL /LTCG /O1 /GS- /Gy /Zc:threadSafeInit- /DEBUG:NONE /INCREMENTAL:NO`.
- Clang-cl + lld-link: `-flto -O1 -Wl,/DEBUG:NONE`.
- Remove `IMAGE_DEBUG_DIRECTORY`, PDB signature (RSDS), and `IMAGE_LOAD_CONFIG_DIRECTORY` if unused.
- Set `IMAGE_FILE_HEADER.TimeDateStamp` to a stable value across rebuilds (per-build timestamp otherwise leaks as a per-operator fingerprint).

Linux ELF:

- musl-static preferred: `--target x86_64-unknown-linux-musl` (Rust) or `-static -static-libgcc` (C).
- `strip -s --remove-section=.note --remove-section=.comment --remove-section=.gnu_debuglink build/loader`.
- Reproducible builds: pinned toolchain container, `-frandom-seed=<sha>` when PIE cannot be disabled.

---

## 6. Toolchain per stage

| Stage / target | Runtime | Rationale |
|---|---|---|
| Windows PIC loader (unbacked beacon) | `no_std` Rust or C99 no-CRT | CRT init is signal-noisy; PIC forbids heap use |
| Windows backed EXE tool_mode | full `std` Rust or MSVC C++ | Backed `.text` must look like a normal PE, not stripped-down PIC |
| Linux static staged loader | musl-Rust with `panic=abort`, or musl-C99 | LD_PRELOAD immunity + minimal syscall surface |
| Linux LKM for BPF sensor blinding | C99 kernel-tree build | ftrace + BPF map hooks require kernel-mode |
| Linux eBPF-only rootkit (no LKM) | libbpf-C or ebpf-go | verifier-bound; ephemeral persistence, LSM-immune only if LSM off |

Do not mix runtimes across stages compiled into a single artifact — mixed CRT symbols and mixed panic runtimes leak signatures.

---

## 7. Sample rotation

Each deployment must be byte-distinct:

- Per-build random XOR / stream cipher seed (`SKILL.md` §10 pattern).
- Per-build randomization of memfd / mutex / named-pipe / mailslot strings.
- Rotate `TimeDateStamp` (PE) or `BuildID` (ELF) per build.
- Section names stay in the safe list (`SKILL.md` §11) — do not randomize (randomness is itself a signal).

Do not:

- Ship the same binary twice (identical SHA-256 = shared signature).
- Rely on a runtime crypter over a shared stub — the stub is the signature.
- Patch bytes in-place at deploy time — the patch pattern becomes the signature.

---

## 8. Public-sandbox & test-infra hygiene

- Never upload production payloads to VirusTotal, any.run, Hybrid Analysis, Joe, Intezer, Triage. All feed vendor telemetry within hours.
- If a public verdict is truly required, upload a NOOP-payload variant with the same evasion stack — the loader fingerprint leaks but the payload doesn't.
- Never test from operator IP against target vendor cloud (S1 / Falcon / Elastic / Sysdig backends). Use isolated test infrastructure with fresh netblocks.
- CI EDR-under-test pipeline (run before every material change):
  1. Snapshot-restore fresh VM (or fresh pod for Falco/Tetragon/Tracee).
  2. Install target EDR at the exact deployed version — not latest.
  3. Run the loader.
  4. Capture: EDR alerts, Sysmon/ETW (Windows), Security 4688 / auditd (both), PCAP.
  5. Diff against previous-commit baseline; `+N` alert delta at commit X pinpoints the change that added signal.

Matrix: (product) × (agent version) × (OS build) × (loader profile). Manual once-per-milestone testing regresses silently between milestones.

---

## 9. Anti-patterns ledger

Field-regressed patterns. Do not reintroduce.

| Pattern | Why it fails |
|---|---|
| Copying a public PoC's evasion feature without measuring cost against target EDR | Public tools have public signatures; ML models already trained |
| Enabling all evasion knobs "for safety" | Feature accumulation regresses (`SKILL.md` §0) |
| Duplicating a fact between `SKILL.md` and a reference | Divergence over time; both become half-wrong |
| Gating evasion at call site only (`if false {...}`) | Dead code retains signature bytes (`constraints.md` disproven assumptions) |
| Shipping one binary containing multiple stage feature sets | Union of signatures across stages — every target EDR triggers on the widest set |
| Cross-stage feature-flag drift (S1 enables HWBP, S2 assumes it, S0 didn't fingerprint) | Silent regressions; feature owned by no stage |
| `VirtualProtect(RX→RW)` on `ntdll .text` for ETW patch | Deterministic usermode-hook alert (`SKILL.md` §5) |
| Software AES / AES-CTR embedded for payload encryption | Algorithmic fingerprint (GF poly, ShiftRows, MixColumns) — `SKILL.md` §10 |
| Linking `openssl` / `libcrypto` for one primitive alone | Import table gives away the plan |
| `.rsrc` section for raw payload | Malforms `DataDirectory[2]` (`SKILL.md` §11) |
| Removing `panic_abort` to "clean up" a Rust build | Rust unwinding strings return (`constraints.md` CS regressions) |
| Building on the operator machine (build path / hostname / user in binary strings) | Fingerprint leakage into every deployed sample |
| Uploading a production loader to VT | Vendor ingest → ML learns → next build starts flagged |
| Testing against target vendor cloud from operator IP | Fingerprint leakage to defender infra |
| Adding features to counter theoretical weaknesses | Adds real signals against unproven risk (`SKILL.md` §0) |
| Random-looking section names (`.r5rc`, `.xyz1`) | Randomness itself is a signal; use standard names |
| Long-lived DR-register HWBP on hot path | Frequency-analysis fingerprint (`SKILL.md` §5b) |
| Reused hardcoded string-obfuscation keys across builds | Recovers as cross-sample pattern |
| Ignoring `SKILL.md` §11 section-ratio table when changing `opt-level` | ML classifiers flag data-dominant binaries |
| Mixing PIC `no_std` loader with `std` payload in one artifact | Mixed CRT symbols; two panic runtimes; hybrid fingerprint |
| Rotating section names at deploy time via patch | Patch pattern itself becomes the signature |
| Leaving `println!` / `fprintf` in release "in case we need debug" | Strings ship |
| Randomizing every build via `--codegen-units` variance without measuring | Uncontrolled variance defeats reproducibility; regressions become unattributable |

