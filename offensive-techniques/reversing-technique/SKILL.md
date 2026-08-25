---
name: reversing-technique
description: "Auth/lab: reverse engineering methodology; malware triage, patch diffing, firmware/protocol RE, protections, exploitability handoff evidence."
license: MIT
compatibility: "Cross-platform binaries (PE/ELF/Mach-O), firmware images,.NET assemblies, network captures; User-mode focus; kernel RE referenced but not detailed."
metadata:
  author: AeonDave
  version: "1.2"
  category: analysis
  language: asm,c,cpp,rust,go,python,csharp
  objectives:
    - malware-analysis
      - software-protection-analysis
    - patch-diffing
    - firmware-reversing
    - dotnet-reversing
    - protocol-reversing
    - vulnerability-hunting
    - exploitability-triage
    - secrets-extraction
    - custom-vm-reversing
    - anti-analysis-bypass
    - side-channel-re
    - language-specific-re
---

# Reverse Engineering Technique

**Extract actionable intelligence efficiently** by adapting workflow to your objective.

## When to activate

- **Malware analysis**: Understand behavior, C2, persistence, evasion.
- **Software protection analysis**: Identify license/protection logic, emulate validation checks, reconstruct key material where authorized.
- **Patch diffing**: Find security fixes, understand vendor patches.
- **Firmware reversing**: Extract filesystems, analyze embedded code.
- **.NET reversing**: Deobfuscate, understand managed code logic.
- **Protocol reversing**: Reconstruct proprietary protocols or file formats.
- **Vulnerability hunting**: Find bugs in closed-source components.
- **Exploitability triage**: Qualify a corruption primitive found during RE, then hand off to `binary-exploitation-technique` for chaining and proof.
- **Secrets extraction**: Recover keys, tokens, passwords.
- **Custom VM / obfuscation**: Binary has a bytecode VM, LLVM CFF dispatcher, or VMProtect/Themida packing.
- **Anti-analysis bypass**: Binary exits under debugger, detects VM, crashes analysis tools, or uses signal-handler tricks.
- **Side-channel RE**: Validation timing, instruction count, or signal behavior leaks per-character correctness.
- **Language-specific RE**: Go, Rust, Python bytecode, Unity IL2CPP, Nim, VBS/WSH, Node.js/V8 snapshots requires language-specific tooling (see `references/languages.md`, `references/nim-rev.md`, `references/node-v8-snapshots.md`).
- **In-memory loading**: Linux binary loads a second-stage ELF via `memfd_create` + `dlopen` (fileless; see `references/in-memory-loading.md`).

## Initial triage

Before diving deep, classify the artifact and the operator objective so the workflow starts in the right lane.

- **Starting state**: is the target malware, protected software, firmware, a managed assembly, a protocol artifact, a crash primitive, or an unknown binary?
- **First questions**: what do you need to learn first, what architecture/runtime/packing signals are present, and is static or dynamic evidence the fastest way to reduce uncertainty?
- **Immediate actions**: perform fast format/entropy/import/string triage, assign the objective workflow, and only then choose the decompiler/debugger/tooling mix.
- **Tool-family direction**: start with CLI/static triage families (`radare2`, `objdump`, `readelf`, `strings`, `capa`, `binwalk`) and escalate to heavy decompilation/debugging (`ghidra`, `binaryninja`, `gdb`, `x64dbg`, `windbg`, `dnspy`, `frida`) once the goal is defined.
- **Escalation rule**: objective first, tool second; do not decompile everything before deciding what question you are answering.

## Core methodology

```
1. Triage (5-10 min): Quick assessment before deep dive.
2. Define objective: What do you need to know?
3. Select tools: Based on binary type, objective, environment.
4. Static analysis: Structure understanding without execution.
5. Dynamic analysis: Validate assumptions via runtime behavior.
6. Synthesis: Pseudocode, documentation, or exploit.
7. Verification: Test findings; iterate if needed.
```

## Triage (first 5-10 minutes)

Quick assessment to decide approach:

| Check | Tool reference | What to look for |
|-------|-----------------|-------------|
| File type | `file`, `detect-it-easy` | PE/ELF/Mach-O/.NET, arch, bits |
| Packers/obfuscation | `Detect It Easy`, `binwalk` | UPX, ASPack, ConfuserEx, high entropy |
| Strings | `strings`, `radare2` (`iz`) | URLs, IPs, registry keys, crypto constants |
| Imports/exports | `radare2` (`ii`, `ie`), `ghidra` | Suspicious APIs, crypto, network, process |
| Metadata | `pefile`, `radare2` (`iI`) | Timestamps, version, compiler, PDB |
| Hashes | `sha256sum`, `rahash2` | Submit to VirusTotal, MalwareBazaar |
| Capabilities | `capa` (`offensive-tools/forensic/capa/`) | TTP fingerprint, malware family, embedded shellcode |

**Decision tree:**
- High entropy + suspicious imports → **Malware analysis** workflow
- Protection messages (registration, trial, activation) → **Software protection** workflow
- Two versions of same binary → **Patch diffing** workflow
- Firmware header (uImage, vmlinux) → **Firmware** workflow
- .NET assembly → **.NET reversing** workflow
- Network capture + unknown protocol → **Protocol RE** workflow
- Large `switch(opcode)` + byte-buffer IP loop → **Custom VM** workflow (see `references/custom-vm.md`)
- `fork()` + `ptrace(TRACEME)` or `SIGTRAP`/`SIGFPE` signal loop → **Nanomites** (see `references/custom-vm.md §2`)
- Binary exits/behaves differently under debugger or in VM → **Anti-analysis bypass** (see `references/anti-analysis.md`)
- Validation response varies by character (timing/count) → **Side-channel RE** (see `references/custom-vm.md §4`)
- Go buildid / Rust `__rust_panic` / `.pyc` file → **Language-specific RE** (see `references/languages.md`)
- LLVM control flow flattening (dispatcher switch, state variable) → `references/custom-vm.md §6`
- VMProtect / Themida packing detected → dump after OEP (see `references/anti-analysis.md §unpacking`)
- `NimMain` / `HEXnn` mangled names / `@[` slice constants → **Nim RE** (see `references/nim-rev.md`)
- `pkg/prelude` / `NODE_SEA_FUSE` / `snapshot_blob` in strings → **Node.js/V8 snapshot** (see `references/node-v8-snapshots.md`)
- `memfd_create` in strace / `/proc/self/fd/` path to `dlopen` → **In-memory loading** (see `references/in-memory-loading.md`)
- `ljmp 0x33:` / `push 0x33; retf` in 32-bit ELF → **Heaven's Gate Linux** (see `references/anti-analysis.md §Category 8`)
- PCAP / protobuf / gRPC / grpc-web / WebSocket frames / length-prefixed binary RPC → **Protocol reversing** (see `references/protocol-rev.md`)
- `.crx` / `.xpi` / `manifest.json` / MV3 service worker / `content_scripts` / `externally_connectable` → **Browser extension reversing** (see `references/browser-extension-rev.md`)
- Two binary versions for patch analysis / a single Microsoft Patch-Tuesday MSU to reconstruct / stripped library with unknown symbols → **Binary diffing / FLIRT** (see `references/binary-diffing.md`)
- Confirmed overwrite primitive with partial control over RIP/EIP/PC, heap metadata, or function pointer → **Exploitability triage** (§7b), then hand off to `offensive-techniques/binary-exploitation-technique`
- Kernel driver/module, hidden artifacts, boot-chain tampering, or EFI/bootloader changes → **Rootkit / bootkit RE** workflow (see `references/rootkit-and-bootkit-re.md`)

## CLI-first tool preference

Prefer CLI/scriptable tooling for triage, batch work, and repeatable evidence. Move to GUI decompilers/debuggers when semantics, types, or interaction speed justify it.

| Need | Prefer first | GUI/decompiler escalation |
|---|---|---|
| File metadata, imports, sections, strings | `rabin2`, `radare2`, `objdump`, `readelf`, `strings` | Ghidra/Binary Ninja project when structure matters |
| Fast static triage | `radare2` (`aaa`, `afl`, `iz`, `ii`, `iS`), `capa` | Ghidra for decompilation and type recovery |
| Linux dynamic behavior | `strace`, `ltrace`, `gdb` | Ghidra debugger only if needed |
| Windows crash/debug | `windbg`/`cdb` for dump triage | `x64dbg` for interactive patch/trace |
| Firmware extraction | `binwalk` CLI first | Ghidra/radare2 per extracted binary |
| .NET | `de4dot`/CLI metadata first | `dnspy` for decompile/debug/patch |

Formal tool skills: `offensive-tools/rev/radare2/`, `offensive-tools/rev/gdb/`, `offensive-tools/rev/frida/`, `offensive-tools/rev/binwalk/`, `offensive-tools/rev/ghidra/`, `offensive-tools/rev/binaryninja/`, `offensive-tools/rev/dnspy/`, `offensive-tools/rev/windbg/`, `offensive-tools/rev/x64dbg/`, plus `offensive-tools/forensic/capa/` for capability triage.

## Objective-driven workflows

### 1. Malware analysis

**Goal**: Understand behavior, extract IOCs, identify C2, assess threat.

**Operator flow:**
```
1. Triage: strings, imports, VirusTotal, Any.Run sandbox report.
2. Static: Load in `ghidra` or `radare2` → auto-analysis.
   - Check imports for: VirtualAlloc, CreateRemoteThread, WriteProcessMemory.
   - Cross-reference suspicious strings (URLs, IPs, registry paths).
   - Identify decryption routines (loops with XOR/RC4/AES).
3. Dynamic: Debug in `x64dbg` (Windows) or `gdb`+`pwndbg` (Linux).
   - Set breakpoints on crypto APIs, network APIs.
   - Dump decrypted strings/config from memory.
   - Monitor: Process Monitor, Wireshark, ProcMon.
   - Linux: use `strace -e trace=network,file` to log syscalls without a debugger; `ltrace` for library call interception.
4. Unpack if packed: Use `x64dbg` + Scylla, or `binwalk` for firmware.
5. Report: IOCs, TTPs, C2 config, YARA rules.
```

**Key tricks:**
- Decryption routines often precede string usage—trace backwards from strings.
- Config often in resources or appended to binary—check `binwalk`, `radare2` (`iS`).
- Anti-debug: PEB.BeingDebugged, NtGlobalFlag, RDTSC—use `ScyllaHide` or patch.
- C2 often encrypted with simple XOR—search for XOR loops with constant key.

**Key tools:** `capa` (TTP triage), `ghidra`/`radare2` (static), `x64dbg`/`gdb`+`pwndbg` (dynamic), `frida` (hooking), `binwalk` (unpacking), `strace`/`ltrace` (Linux syscall/lib tracing), `windbg` (crash dumps).

→ Full workflow: `references/re-workflow.md`. Anti-debug bypass: `references/anti-analysis.md`.

---

### 2. Software protection bypass and licensing emulation

**Goal**: Understand license/protection checks, emulate validation, and produce authorized proof of bypass or key-generation logic.

**Operator flow:**
```
1. Triage: Identify protection (ASProtect, Themida, custom).
2. Static: Load in `ghidra` → find protection strings, error messages.
   - Search for: "Invalid key", "Trial expired", "Wrong password".
   - Cross-reference strings to validation functions.
3. Dynamic: Debug in `x64dbg` or `radare2` debugger.
   - Set breakpoint on validation function or message box.
   - Trace backwards to find comparison logic.
   - Patch: NOP conditional jump, or change return value.
4. Key reconstruction: Understand algorithm from decompiled code.
   - Reconstruct in Python/C based on pseudocode.
5. Verify: Patched binary accepts valid key.
```

**Key tricks:** Cross-ref error strings to validation functions; NOP/invert the final comparison; watch for CRC re-checks after patching.

**Key tools:** `ghidra` (decompile validation), `x64dbg` (patch jumps), `frida` (hook online activation), `dnspy` (.NET).

→ Unpacking details: `references/anti-analysis.md §unpacking`. Binary diffing: `references/binary-diffing.md`.

---

### 3. Patch diffing

**Goal**: Find what changed between two binary versions (security patch, CVE reconstruction).

- Run `radiff2 -g main old new` or Ghidra Version Tracking to correlate functions.
- Focus on functions with added `if` / early-return → likely security fix.
- Verify the bug is reachable before claiming exploitability.

→ Full workflow with FLIRT, BinDiff, and symbol recovery: `references/binary-diffing.md`.

---

### 4. Firmware reversing

**Goal**: Extract filesystem, analyze embedded binaries, find backdoors.

**Operator flow:**
```
1. Triage: Identify firmware type (router, IoT, BIOS, etc.).
   - Check magic bytes: uImage (0x27051956), vmlinux, squashfs, etc.
2. Extract: preserve/hash first, identify the outer format, then follow `references/firmware-rev.md` for isolated, bounded extraction.
3. Analyze filesystem:
   - `squashfs-root/`: config files, web interfaces, binaries.
   - Search for: hardcoded credentials, backdoor accounts, crypto keys.
4. Reverse embedded binaries:
   - Identify arch: MIPS, ARM, AVR (use `radare2` or `ghidra`).
   - Load in appropriate tool with correct base address.
5. Emulate (optional): QEMU user-mode for MIPS/ARM binaries.
```

**Key tricks:**
- Firmware often has: Telnet backdoors, hardcoded SNMP community strings, private keys.
- Web interfaces: check for command injection (ping, traceroute), path traversal.
- Embedded binaries may be stripped → use `radare2` zignatures or `ghidra` function ID.
- Check `/etc/passwd`, `/etc/shadow`, SSH keys, certificate files.

**Tool citations:**
- `binwalk` — signature scan, extraction, entropy analysis.
- `ghidra` — analyze MIPS/ARM binaries, recover structs.
- `radare2` — headless analysis, scripting for batch processing.
- `frida` — dynamic analysis if firmware runs on emulated device.

**Common pitfalls:**
- Wrong architecture → decompilation nonsense.
- Wrong base address → function calls go to invalid addresses.
- Ignoring filesystem configs → missing high-value IOCs.

---

### 5. .NET reversing (managed code)

**Goal**: Understand C#/VB.NET logic, bypass obfuscation, extract configs.

1. Detect obfuscator: `de4dot --detect sample.exe`
2. Deobfuscate: `de4dot sample.exe -o clean.exe`
3. Analyze in `dnspy` — start at Entry Point (Ctrl+Shift+K); set breakpoints on decryption/config load
4. Watch for multi-stage loaders: `Assembly.Load()` + `GetManifestResourceStream` call sites
5. Network isolation is mandatory before dynamic debugging stealers/RATs

**Key tools:** `dnspy` (decompiler/debugger/patcher), `de4dot` (deobfuscation), `ghidra` (fallback).

→ Full deobfuscation table, ConfuserEx/Reactor flags, config extraction: `references/dotnet-rev.md`.

---

### 6. Protocol reversing

**Goal**: Reconstruct proprietary protocol, understand message format.

**Operator flow:**
```
1. Capture traffic: Wireshark, tcpdump, or `frida` SSL pinning bypass.
2. Triage: Identify protocol type (text, binary, encrypted).
   - Look for magic bytes, length fields, checksums.
3. Static: Analyze client/server binaries in `ghidra`.
   - Find send/recv functions → cross-reference to protocol handlers.
   - Reconstruct structs from serialization code.
4. Dynamic: Hook send/recv with `frida` → log raw packets.
   - Correlate with network capture.
5. Document: Message format, state machine, encryption (if any).
```

**Key tricks:**
- Text protocols: look for delimiters (`\n`, `|`, `;`) and command keywords.
- Binary protocols: look for length fields, magic bytes, checksums (CRC32, Adler32).
- Encryption: check for TLS, or custom crypto (XOR, AES) in binary.
- Use `frida` to intercept before encryption/after decryption.

**Tool citations:**
- `ghidra` — analyze protocol handlers, recover structs.
- `frida` — hook send/recv, bypass SSL pinning.
- `wireshark` — (external) packet analysis.
- `radare2` — headless protocol analysis scripting.

**Common pitfalls:**
- Assuming protocol is text → it's binary with magic bytes.
- Ignoring encryption → can't read payload without key.
- Not correlating static + dynamic → missing protocol state machine.

→ gRPC/protobuf/websocket/app-framing specifics and decoder bootstrap: `references/protocol-rev.md`.

---

### 7. Vulnerability hunting

**Goal**: Find bugs (buffer overflow, use-after-free, etc.) in closed-source.

**Operator flow:**
```
1. Recon: Identify attack surface, input channels, and hardening context.
   - Parsers, network listeners, IPC, config importers, update handlers.
2. Static: Load in `ghidra` or `binaryninja`.
   - Trace attacker-controlled data into size, offset, pointer, and format operations.
3. Classify the candidate primitive.
   - Overflow, UAF/double-free, integer mis-sizing, format string, command construction.
4. Dynamic validation: Debug in `gdb`+`pwndbg` or `x64dbg`.
   - Confirm branch reachability, memory/register side effects, and repeatability.
5. Symbolic execution: use `angr` for path exploration when manual analysis of branching logic is too slow — especially useful for complex key validation or constrained input recovery.
6. Fuzzing or targeted harness: Use AFL++, LibFuzzer (see `offensive-tools/fuzzing/`) if format knowledge will improve coverage.
7. Exploitability model: rank by control quality, mitigations, and environmental preconditions before claiming impact.
```

**Key tricks:**
- Focus on input parsers: file format readers, network packet handlers.
- Look for: integer overflows (size calculations), off-by-one errors.
- Use `checksec` (in `gdb`+`pwndbg`) to see mitigations (NX, PIE, CANARY).
- Patch diffing helps: find recent CVE fixes → analyze vulnerability.
- Keep one controlled input per hypothesis so crash cause and side effects stay attributable.
- Write proof requirements early: what would count as a validated primitive vs a suspicious crash?

**Tool citations:**
- `ghidra`, `binaryninja` — static analysis, decompilation.
- `gdb`+`pwndbg`/`gef` — crash analysis, exploit debugging.
- `frida` — runtime analysis, hooking.
- `angr` — symbolic execution, path exploration, automated constraint solving for input recovery.
- AFL++, LibFuzzer — fuzzing (see `offensive-tools/fuzzing/`).

**Common pitfalls:**
- Fuzzing without understanding input format → low coverage.
- Ignoring mitigations → exploit harder than expected.
- Not verifying exploitability → crash ≠ vulnerability.
- Claiming impact without proving reachability from a realistic input path.
- Missing config-dependent branches → the vulnerable path may be disabled in the default run.

---

### 7b. Exploitability triage and handoff

**Goal**: From a validated corruption primitive, qualify exploitability and hand a clean primitive to `offensive-techniques/binary-exploitation-technique`; do not build the chain here.

**Qualify before handoff:**
- Prove what is controlled (PC, stack pivot, arbitrary read/write, object/type confusion) and the bug family (overflow/UAF/type confusion/index/format string).
- Confirm deterministic, attacker-influenced reproduction under a fixed input path — a crash is not yet a primitive.
- Model the primitive's *repeatability*: read every branch of any state guard (`is_set`, `initialized`, `done`, `idx == fav`). The `else`/already-set branch frequently still performs the gated read/write/free, so an apparently one-shot primitive is a repeatable arbitrary read/write loop. Confirm which branch runs on the second invocation before declaring a path dead.
- Inventory mitigations (`checksec`, module headers): NX/DEP, ASLR/PIE, canary, RELRO, CFG/CET, allocator hardening — carry this into the handoff.

**Tools:** `gdb`+`pwndbg`/`gef`, `x64dbg`, `windbg` for control validation; `angr` for trigger-gating constraints; `radare2`/`ghidra`/`binaryninja` for gadget/function reachability.

→ Chain strategy, mitigation-aware planning, and reproducible proof: `offensive-techniques/binary-exploitation-technique`. Concrete recipes (ROP/heap/FSOP/format-string/one_gadget): `offensive-ctf/pwn-ctf/references`.

---

### 8. Secrets extraction

**Goal**: Recover hardcoded keys, passwords, tokens, C2 addresses.

**Operator flow:**
```
1. Triage: Strings (`strings`, `radare2` `iz`), look for:
   - Crypto constants (AES S-box, RSA magic, base64 patterns).
   - URLs, IPs, email addresses.
   - High-entropy regions (likely encrypted/compressed).
2. Static: Find decryption routines in `ghidra`.
   - Look for: XOR loops, AES key schedules, RC4 init.
   - Cross-reference encrypted strings to decryption function.
3. Dynamic: Breakpoint on crypto APIs (`CryptEncrypt`, `BCryptEncrypt`).
   - Dump memory after decryption (`x64dbg` memory dump).
4. Decode: Base64, hex, or emulate decryption in Python.
```

**Key tricks:**
- Secrets often: XORed with single byte, or AES with embedded key.
- C2 config: may be JSON/XML in resources, or encrypted blob.
- API keys/tokens: search for common patterns (`Bearer`, `api_key`, `secret`).
- Use `radare2` to search for crypto constants: `/R opcode` for ROP, but for crypto search bytes.

**Tool citations:**
- `ghidra` — identify crypto algorithms, recover keys.
- `radare2` — search patterns, script analysis.
- `x64dbg` — runtime memory dump after decryption.
- `frida` — hook crypto APIs, log plaintext.

**Common pitfalls:**
- Assuming strings are plaintext → they're decrypted at runtime.
- Not checking resources → secrets hidden in embedded data.
- Ignoring TLS traffic → C2 communication encrypted.

---

### 9. JavaScript / browser extension reversing

**Goal**: Understand web application logic, browser extensions, or obfuscated JS payloads.

**Operator flow:**
```
1. Triage: Is it a browser extension (zip/crx), single-page app bundle, or obfuscated script?
2. Extract:
   - Browser extension: rename .crx → .zip → extract.
   - SPA bundle: download the main JS bundle via DevTools → Sources.
3. Deobfuscate:
   - Run through JS beautifier (js-beautify, Prettier).
   - For eval-obfuscated/string-array obfuscation: use de-obfuscation pass (obfuscator.io reverse, webcrack, deobfuscate.io).
   - For packed bundles (webpack/rollup): look for chunk map → identify module boundaries.
4. Static analysis: Browser DevTools or VS Code → search for:
   - Sensitive strings: API keys, endpoints, tokens.
   - Crypto calls: subtle.crypto, CryptoJS, forge.
   - Eval / dynamic code execution.
5. Dynamic: DevTools debugger → breakpoint on XHR/fetch, DOM mutation, or suspicious function.
   - Intercept requests via proxy (mitmproxy).
   - Patch eval'd payloads with live overrides (DevTools override feature).
6. Manifest audit (extensions): check `permissions`, `content_scripts`, `background`, `externally_connectable`.
```

**Key tricks:**
- Webpack bundles expose `__webpack_require__` — iterate module map to enumerate all modules.
- Chrome extension background workers: debug via `chrome://extensions` → inspect background page.
- Eval-hidden payloads: override `eval` at load time to log all executed strings.
- API key extraction: search for `Authorization`, `api_key`, `Bearer`, `X-Api-Key`.

**Tool citations:**
- Browser DevTools — primary debugger and network inspector.
- `frida` — inject into Electron/Node.js apps using the browser engine.
- `mitmproxy` (`offensive-tools/network/mitmproxy/`) — intercept and replay browser-initiated requests.
- `radare2` / `ghidra` — if JS engine (V8) is compiled into a native binary.

→ MV2/MV3 entry points, permission-risk triage, messaging edges, and nativeMessaging / externally_connectable audit: `references/browser-extension-rev.md`.

---

## Anti-reverse engineering bypass

### Common techniques and countermeasures

| Technique | What it does | Bypass method | Tool reference |
|------------|--------------|---------------|-----------------|
| PEB.BeingDebugged | Checks PEB flag | Patch byte at PEB+0x02 to 0 | `x64dbg`, `ScyllaHide` |
| NtGlobalFlag | Sets heap flags for debugging | Clear flag at PEB+0x68 (32-bit) | `x64dbg`, `ScyllaHide` |
| RDTSC timing | Measures CPU cycles for debugger | Patch or emulate | `frida` hook |
| FindWindow/Process | Detects debugger windows | Hook with `frida` or NOP | `x64dbg` |
| CRC/integrity | Checks code section hashes | Patch check or suspend thread | `x64dbg` breakpoint |
| VM detection | Detects VirtualBox/VMware | Use real hardware or hide with VM detection bypass | `ScyllaHide` |
| Anti-dump | Prevents memory dumping | Use `Scylla` for IAT fix | `x64dbg` + Scylla |
| Obfuscation (.NET) | Renames, control flow, constants | Use `de4dot`, `dnSpy` decompile | `dnspy` |

### Unpacking workflow

```
1. Detect packer: DIE, PEiD, or manual (section names, entry point).
2. Static: Find OEP (Original Entry Point) via:
   - Pushad/popad patterns (UPX).
   - Call to GetProcAddress/LoadLibrary (custom).
3. Dynamic: Set breakpoint on VirtualAlloc (for RWX memory).
   - When hit, check size arg → likely unpacked code destination.
   - Set hardware execute BP on returned address.
   - Run → break at OEP (unpacked code).
4. Dump: Use `Scylla` (x64dbg plugin) or `radare2` `om`.
5. Fix IAT: Reconstruct imports with `Scylla` or manual.
```

## Operator checklist (per objective)

Each objective workflow in §1–9 plus §7b contains a full step-by-step flow. Quick gate:

- Triage complete before deep static analysis.
- Objective defined before tool selection.
- Isolated environment for dynamic analysis.
- Static findings validated dynamically; dynamic assumptions confirmed statically.
- Reproducible notes (hashes, tool versions, environment) captured for reporting.

## Common pitfalls (all objectives)

- **Analysis paralysis**: Disassembling everything without objective.
- **Trusting decoys**: Strings may be encrypted, fake, or irrelevant.
- **Skipping triage**: Wasting time on packed/encrypted code.
- **No isolation**: Dynamic analysis on host → infection/compromise.
- **Confirmation bias**: Ignoring evidence contradicting hypothesis.
- **Tool fixation**: Using wrong tool for binary type (e.g., `x64dbg` for ELF).
- **Ignoring anti-analysis**: Debugger detected, malware exits silently.

## Tool selection quick reference

| Objective | Primary tools (see `offensive-tools/rev/`) | Environment |
|-----------|------------------------------------------|------------|
| Malware (Windows) | `ghidra`, `x64dbg`, `frida`, `capa` | Windows VM |
| Malware (Linux) | `ghidra`, `gdb`+`pwndbg`, `radare2`, `capa` | Linux VM/WSL |
| Software protection (Windows) | `ghidra`, `x64dbg`, `dnspy` (.NET) | Windows |
| Patch diffing | `ghidra` (Version Tracking), `radare2` (`radiff2`) | Cross-platform |
| Firmware | `binwalk`, `ghidra`, `radare2` | Linux |
| .NET reversing | `dnspy`, `de4dot` | Windows |
| Protocol RE | `ghidra`, `frida`, `mitmproxy` | Depends |
| Vulnerability hunting | `ghidra`/`binaryninja`, `gdb`, AFL++ | Linux/Windows |
| Exploitability triage (→ `binary-exploitation-technique`) | `gdb`+`pwndbg`/`gef`, `x64dbg`, `windbg`, `checksec` | Linux/Windows |
| JS/Browser extension | DevTools, `frida`, `mitmproxy` | Browser/Electron |
| Kernel/crash dump | `windbg` | Windows |

## Resources

**Core sequence:**

- [references/triage.md](references/triage.md) — start here for the first 5–10 minutes: format detection, entropy, imports, language/runtime fingerprints, and next-step decisioning.
- [references/re-workflow.md](references/re-workflow.md) — core methodology after triage: static, dynamic, reconstruction, Ghidra workflow, crypto-pattern spotting, and reporting.

**Format supplements:**

- [references/pe-rev.md](references/pe-rev.md) — PE-only pivots: RVA/raw mapping, data directories, TLS/CRT pre-entry paths, IAT/EAT/delay imports, resources/overlay/Authenticode, unpacking, and mitigation handoff.
- [references/elf-rev.md](references/elf-rev.md) — ELF-only pivots: program headers, dynamic entries, PLT/GOT/relocations, RELRO/ASLR, symbol versioning, IFUNC/constructors, loader instrumentation, and packer/runtime surfaces.
- [references/dotnet-rev.md](references/dotnet-rev.md) — managed-assembly workflow: deobfuscation order, resource/config extraction, stage loading, and managed/native handoff.
- [references/firmware-rev.md](references/firmware-rev.md) — firmware container workflow: format-first bounded extraction, filesystem/control-plane mapping, startup review, and emulation handoff.

**Problem-specific deep dives:**

- [references/anti-analysis.md](references/anti-analysis.md) — Linux/Windows anti-debug, anti-VM, anti-DBI, code integrity, anti-disassembly, MBA, Heaven's Gate Linux, and bypass strategies.
- [references/custom-vm.md](references/custom-vm.md) — custom VM reversing, nanomites, self-modifying code, metamorphic decrypt loops, lattice/linear-algebra solving, side-channel attacks, and emulation frameworks.
- [references/ransomware-re.md](references/ransomware-re.md) — ransomware crypto workflow: hybrid model, Windows CryptoAPI/CNG/OpenSSL identification, implementation flaw checklist, encrypted-file analysis, public-key extraction, and YARA skeleton.
- [references/languages.md](references/languages.md) — language/runtime pivots for Go, Rust (crate fingerprinting), Python bytecode (PyInstaller/PyArmor), Nim, VBS/WSH, Unity IL2CPP, and HarmonyOS HAP.
- [references/protocol-rev.md](references/protocol-rev.md) — capture-first custom protocol reversing: text vs binary framing, gRPC/protobuf decoding, WebSocket/app-frame separation, and minimal parser outputs.
- [references/browser-extension-rev.md](references/browser-extension-rev.md) — Chrome/Edge/Firefox extension workflow: MV2/MV3 entry points, permission-risk triage, content-script isolation, messaging edges, storage, and nativeMessaging.
- [references/binary-diffing.md](references/binary-diffing.md) — binary diff workflow (radiff2, Ghidra VT, BinDiff, ghidriff), FLIRT signature generation, Ghidra FID for stripped library symbol recovery, and Windows Update MSU/CAB acquisition + `PA30` delta reconstruction for n-day patch diffing.
- Exploitability handoff: once a primitive is confirmed, `offensive-techniques/binary-exploitation-technique` owns the chaining methodology and `offensive-ctf/pwn-ctf/references` holds the concrete recipes.
- [references/rootkit-and-bootkit-re.md](references/rootkit-and-bootkit-re.md) — Windows/Linux kernel-mode RE, driver/module triage, bootkit workflow, hook/callback analysis, and boot-chain evidence.
- [references/nim-rev.md](references/nim-rev.md) — Nim binary recognition, symbol recovery, GC/memory layout, decompilation patterns, stripped binary workflow.
- [references/node-v8-snapshots.md](references/node-v8-snapshots.md) — Node.js pkg/SEA/nexe extraction, V8 startup snapshot recovery, JS deobfuscation.
- [references/in-memory-loading.md](references/in-memory-loading.md) — Linux fileless loading via memfd_create + dlopen: detection, runtime dump, layer separation.

- `offensive-tools/forensic/capa/` — capability-based binary classification (TTP/family detection).

