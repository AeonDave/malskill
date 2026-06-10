# Evasion Surface

Load when modeling Windows telemetry layers such as AMSI, ETW, hooks, kernel callbacks, and VBS-backed protections.

## The telemetry stack

```
                    ┌──────────────────────────────────────────┐
                    │   EDR cloud / SIEM (correlation)         │
                    └──────────────────┬───────────────────────┘
                                       │
┌──────────────────┬──────────┬────────┴────────┬──────────────────┐
│  ETW sessions    │  Event   │  WEF             │  Sysmon event   │
│  (TraceLogging,  │  Log     │  (forwarder)     │  channel        │
│   ETW-TI,        │  (sec/   │                  │                 │
│   Microsoft-     │   app/   │                  │                 │
│   Windows-*)     │   sys)   │                  │                 │
└────────┬─────────┴──────────┴──────────────────┴─────────────────┘
         │ consumed by kernel-mode providers + filter drivers
         ▼
┌───────────────────────────────────────────────────────────────────┐
│   Kernel callbacks: PsSetCreateProcessNotifyRoutineEx2,           │
│   PsSetCreateThreadNotifyRoutine, PsSetLoadImageNotifyRoutine,    │
│   ObRegisterCallbacks, CmRegisterCallbackEx, FltMgr minifilters   │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────┴───────────────────────────────────────┐
│   Userland hooks in EDR agent DLL injected into each process:      │
│   - ntdll (NtCreateThreadEx, NtAllocateVirtualMemory, NtProtect*, │
│            NtWriteVirtualMemory, NtMapViewOfSection, NtSetContext*)│
│   - kernelbase (CreateProcessW, VirtualAlloc*, LoadLibrary*)      │
│   - winhttp / wininet (C2 egress)                                  │
│   - amsi.dll (AmsiScanBuffer / AmsiScanString)                    │
└────────────────────────────────────────────────────────────────────┘
```

Each layer can be defeated independently, but all must be defeated simultaneously for sustained stealth.

## AMSI (Antimalware Scan Interface)

COM-ish API (`amsi.dll`) mediating between scripting hosts (PowerShell, WScript, .NET, VBA) and registered antimalware providers. Microsoft Defender registers as the built-in provider.

Entry points:

```c
HRESULT AmsiInitialize(LPCWSTR appName, HAMSICONTEXT* amsiContext);
HRESULT AmsiScanBuffer(HAMSICONTEXT ctx, PVOID buf, ULONG len,
                       LPCWSTR contentName, HAMSISESSION session,
                       AMSI_RESULT* result);
HRESULT AmsiScanString(HAMSICONTEXT ctx, LPCWSTR str,
                       LPCWSTR contentName, HAMSISESSION session,
                       AMSI_RESULT* result);
```

`AMSI_RESULT`: values >= `AMSI_RESULT_DETECTED` (32768) mean block.

### The classic 6-byte patch

`AmsiScanBuffer` prologue on x64 Win10/11:

```asm
AmsiScanBuffer:
    4C 8B DC              mov     r11, rsp
    49 89 5B 08           mov     [r11+8], rbx
    49 89 6B 10           mov     [r11+10h], rbp
    ...
```

Patch approach 1 — force invalid-parameter return:

```asm
B8 57 00 07 80            mov     eax, 80070057h      ; E_INVALIDARG
C3                        ret
```

Six bytes at the function entry. `E_INVALIDARG` makes the caller treat the scan as never-happened, failing open.

Patch approach 2 — force "clean":

```asm
33 C0                     xor     eax, eax            ; S_OK
C3                        ret
```

Then set `*result = AMSI_RESULT_CLEAN (0)` if caller pattern allows, OR patch the result-write path. Usually approach 1 is cleaner because of caller check idioms.

### Other patch sites

| Target | Why |
|---|---|
| `AmsiScanBuffer` | Most common path (PowerShell, .NET) |
| `AmsiScanString` | Older callers |
| `AmsiOpenSession` | Ref-counted session bracket |
| `AmsiInitialize` | Kills all scanning for caller — blunt but effective |

In-process AMSI bypass must:

1. `LoadLibraryW(L"amsi.dll")` — or find existing mapping, AMSI is loaded lazily.
2. `GetProcAddress(hAmsi, "AmsiScanBuffer")`.
3. `VirtualProtect` to `PAGE_EXECUTE_READWRITE`, write patch, restore.
4. Flush instruction cache: `FlushInstructionCache(GetCurrentProcess(), addr, 6)` — harmless on x64 (cache-coherent) but recommended on ARM64.

### Hardened AMSI (recent changes)

- **Win11 24H2**: `AmsiScanBuffer` is in a CFG-guarded region; patching still works because patch writes to function prologue, not indirect-call targets — CFG check is on callers.
- **Defender Mar 2023+**: monitors `AmsiScanBuffer` prologue via a secondary signal; patch within some patterns triggers `AmsiUacBypassModule` detection. Use variants (not the literal stock patch bytes).
- **PowerShell CLM (Constrained Language Mode)** combined with Applocker/WDAC blocks dynamic invocation of `[Reflection]::GetField` to reach the `amsiContext`, closing the "null-context" classic bypass.
- **.NET AMSI**: `System.Management.Automation` calls AMSI before compiling. .NET 4.8+ added direct AMSI integration bypassable via patching `System.Management.Automation.AmsiUtils.amsiInitFailed` field (Matt Graeber's original — still works in some .NET versions).

### Bypass strategies hierarchy

1. **Patch-in-memory** (simplest; requires in-process execution): patch `AmsiScanBuffer` → block scanning for this process.
2. **Hardware breakpoints** (stealthier; no memory write): set DR0 on `AmsiScanBuffer`, VEH fixes RIP to return `E_INVALIDARG`. See [memory-management.md](memory-management.md).
3. **COM unregister**: `CLSID` hijacking prevents Defender provider from being instantiated. Requires registry write under `HKLM\Software\Microsoft\AMSI\Providers\{GUID}` — typically flagged by registry callbacks.
4. **Replace `amsi.dll`**: DLL sideloading or forcing `KnownDlls` substitution. High effort, very stealthy if achievable.

## ETW (Event Tracing for Windows)

Microsoft's flagship in-kernel telemetry bus. Providers emit events; sessions (consumers) subscribe. Kernel providers bypass userland entirely.

Key structures per process:

- `ntdll!EtwpEventRegistrationTable` / `EtwpProvRegistrationTable` — per-process provider registrations.
- `ntdll!EtwEventWrite`, `EtwEventWriteEx`, `EtwEventWriteFull` — userland event emission path.
- Each registered provider has a `REG_HANDLE` → `ETW_REG_ENTRY` with `ProviderEnableInfo`, `Level`, `MatchAnyKeyword`, `MatchAllKeyword`.

### ETW patching (process-local)

Two approaches:

**A) Patch `EtwEventWrite` / `NtTraceEvent` prologue**:

```asm
EtwEventWrite:
    48 89 5C 24 08    mov  [rsp+8], rbx
    ...
```

Replace with:

```asm
C3                    ret
```

or `xor eax, eax; ret` — all subsequent `EtwWrite*` return success without emitting.

**B) Disable per-provider enable bits**:

For each `ETW_REG_ENTRY`, clear `ProviderEnableInfo` (a `TRACE_ENABLE_INFO`-ish struct with `IsEnabled`, `Level`, `EnableProperty`). Benefit: more surgical — only silences specific providers rather than all ETW. Lookup:

```c
// Walk EtwpEventRegistrationTable (RtlGenericTable)
for each ETW_REG_ENTRY {
    reg->ProviderEnableInfo.IsEnabled = 0;
    reg->ProviderEnableInfo.Level = 0;
    reg->ProviderEnableInfo.EnableProperty = 0;
    // Optional: zero MatchAnyKeyword / MatchAllKeyword
}
```

### Process-local ETW silencers

| Technique | Target | Scope |
|---|---|---|
| `NtTraceEvent` / `EtwEventWrite` prologue patch | All events from process | Entire process |
| Clear `EtwpEventRegistrationTable` entries | Specific providers | Entire process |
| `EtwEventUnregister` loop | Every registered provider | Entire process |
| Patch `EtwTraceMessage` / `EtwWriteUMSecurityEvent` | Microsoft security providers | Defender-adjacent |

All of these are **in-process** silencers only. Kernel ETW-TI (next section) is untouched.

### ETW-TI (Microsoft-Windows-Threat-Intelligence)

Kernel-mode ETW provider `{F4E1897C-BB5D-5668-F1D8-040F4D8DD344}`. Only consumable by **Protected Processes signed with Antimalware signer** — i.e., Defender's `MsMpEng.exe` and third-party AV drivers. Userland cannot subscribe.

Documented events (`EtwTi*` routines exported by `ntoskrnl.exe`, called from syscall handlers):

| Event | Fires on |
|---|---|
| `EtwTiLogAllocExecVm` | `NtAllocateVirtualMemory(Ex)` with PAGE_EXECUTE_* |
| `EtwTiLogProtectExecVm` | `NtProtectVirtualMemory` transitioning to executable |
| `EtwTiLogMapExecView` | `NtMapViewOfSection(Ex)` with execute rights |
| `EtwTiLogAllocExecVmRemote` | Same as AllocExecVm but target != caller |
| `EtwTiLogProtectExecVmRemote` | Remote protect-to-exec |
| `EtwTiLogMapExecViewRemote` | Remote map-exec |
| `EtwTiLogWriteVm` | `NtWriteVirtualMemory` — local-to-process writes NOT logged; cross-process always |
| `EtwTiLogReadWriteVm` | Large or unusual read/write patterns |
| `EtwTiLogSuspendResume` | Cross-process thread/process suspend+resume (classic sleep obfuscation) |
| `EtwTiLogContextModification` | `NtSetContextThread` cross-process |
| `EtwTiLogQueueApcThread` | APC queued (pre-Win10 19H1 only for cross-process; later all) |
| `EtwTiLogQueueUserApc` | Queue user APC (including Special) |
| `EtwTiLogSetProcessTokenInfo` | Token manipulation |
| `EtwTiLogDriverObjectLoad` | Driver loaded |
| `EtwTiLogDriverObjectUnload` | Driver unloaded |
| `EtwTiLogImpersonateToken` | Thread impersonation |
| `EtwTiLogOpenProcess` | `NtOpenProcess` (full or reduced access) |
| `EtwTiLogOpenThread` | `NtOpenThread` |
| `EtwTiLogReadWriteVmProtected` | Read/write against protected process |

These are the events EDRs weigh most heavily. Suspect patterns: AllocExecVm → WriteVm → QueueApcThread in same process chain is classic injection.

### ETW-TI bypass

Only works from kernel mode (userland cannot observe these events either, but also cannot silence them with just in-process patching).

**Kernel-write primitive (BYOVD) bypass**:

1. Locate `EtwThreatIntProvRegHandle` export.
2. Dereference → `ETW_REG_ENTRY`.
3. Zero `ProviderEnableInfo.IsEnabled` or swap the entry's `EnableInfo` pointer to a no-op block.

PatchGuard implications: `EtwThreatIntProvRegHandle` itself is kernel data, not code, and historically NOT in KPP's direct watch set. But third-party EDRs increasingly compare the handle state at runtime and alarm on zero.

**No-kernel-access alternative**: run as a PPL-Antimalware process and disable the provider via its own registration. Requires signing with Antimalware signer (not realistic outside legitimate AV vendors).

**Defer the syscall to a less-monitored path**: `ETW_TI` fires from syscall handlers, so any syscall taken via Hell's Gate / direct `syscall` hits it. Only kernel-mode or driver-mediated alternatives avoid it, but those require ring 0.

## CFG / XFG / CET

### Control Flow Guard (CFG)

Compiler+loader feature that validates indirect-call targets at runtime. `IMAGE_LOAD_CONFIG_DIRECTORY` exposes:

- `GuardCFCheckFunctionPointer` — `ntdll!LdrpValidateUserCallTarget` on load; compiler emits `call [GuardCFCheckFunctionPointer]` before every indirect call.
- `GuardCFFunctionTable` — bitmap of valid call targets (8 bits per 16-byte chunk).
- `GuardCFFunctionCount` — entries count.
- `GuardFlags` — `IMAGE_GUARD_CF_INSTRUMENTED`, `IMAGE_GUARD_CFW_INSTRUMENTED`, `IMAGE_GUARD_CF_FUNCTION_TABLE_PRESENT`, `IMAGE_GUARD_CF_EXPORT_SUPPRESSION_INFO_PRESENT`, `IMAGE_GUARD_CF_ENABLE_EXPORT_SUPPRESSION`, `IMAGE_GUARD_RF_INSTRUMENTED` (Return Flow Guard), `IMAGE_GUARD_RF_ENABLE` (enforce), `IMAGE_GUARD_RETPOLINE_PRESENT`, `IMAGE_GUARD_EH_CONTINUATION_TABLE_PRESENT` (EH guard).

Export suppression: dynamic APIs like `GetProcAddress` can return "suppressed" exports; calling them needs a second `SetProcessValidCallTargets` whitelist step.

**Bypasses / impact**:

- JOP/ROP gadget landing points not at function starts — CFG bitmap marks them invalid.
- Shellcode injected into RWX region — bitmap has no entries for it; indirect calls to it fail.
- `SetProcessValidCallTargets` (requires `PROCESS_SET_LIMITED_INFORMATION`) — add target to bitmap. Hooked/watched by some EDRs.
- `NtSetInformationVirtualMemory(VmCfgCallTargetInformation)` — kernel equivalent used by CoreCLR for JIT.
- `NtContinue` to CFG-marked target → OS-safe way to pivot execution (base of many bypass chains).
- Exception dispatcher path `KiUserExceptionDispatcher` → `RtlRestoreContext` — not CFG-checked historically; used as redirect primitive.

### eXtended Flow Guard (XFG)

CFG extension: each call site carries a type signature hash; target function has matching hash in its preamble. Enforced on newer builds for specific binaries (Edge renderer, parts of the browser sandbox). Makes type-confusion "call-to-valid-but-wrong-signature" harder.

### CET (Control-flow Enforcement Technology)

Intel Tiger Lake+ / AMD Zen 3+ hardware feature with two components:

- **Shadow Stack (SS)**: hardware-maintained shadow copy of return addresses. `CALL` pushes to both normal stack and shadow stack; `RET` pops from both and compares. Mismatch → `#CP` fault.
- **Indirect Branch Tracking (IBT)**: every indirect jump target must begin with `ENDBR64` (or `ENDBR32`). Jumping to a non-ENDBR instruction → `#CP`.

Windows integration:

- User-mode Shadow Stack enabled per process via `PROCESS_MITIGATION_USER_SHADOW_STACK_POLICY` (`UpdateProcThreadAttribute` / `NtSetInformationProcess(ProcessDynamicEnforcedCetCompatibleRanges)`).
- Default in Edge, Teams, parts of explorer; off by default for most user apps unless policy dictates.
- Shadow stack allocated per thread — `TEB->SSP` accessible via `GetThreadDynamicEnforcedCetCompatibleRanges`.
- Compatibility mode tolerates non-ENDBR targets in specified ranges; strict mode does not.

**Impact on offensive tooling**:

- ROP on shadow-stack-enabled processes requires corresponding shadow stack manipulation — cannot just pivot RSP.
- SilentMoonwalk-style call-stack spoofing requires careful SSP treatment: either allocate a matching fake shadow stack (requires `SSPW`/`SAVEPREVSSP` instructions) or target only processes without CET.
- `NtContinue` is CET-aware on Win11 24H2; the old trick of using it as unchecked call-gate is neutralized when shadow stack is on.

Detection: if process is CET-enabled, injecting normally-positioned ROP and hoping it doesn't land on a `CALL` target won't work — any `RET` through forged frames mismatches shadow stack.

### Retpoline

Spectre v2 mitigation: indirect calls replaced with return-based construct that defeats branch target injection. User-mode retpoline thunks in `RetpolineUser`. Operationally transparent to offensive code but restricts gadget-chain fidelity for some speculative patterns.

## VBS, HVCI, Credential Guard

### VBS (Virtualization-Based Security)

Uses Hyper-V to host a separate VTL1 ("Virtual Trust Level 1") where critical security code runs. The normal kernel runs in VTL0. VTL1 is controlled by `securekernel.exe` + `lsass.exe` VTL1 half (isoLSA).

Enable state check:

```powershell
Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard
# VirtualizationBasedSecurityStatus: 2 = running
# SecurityServicesRunning: {1=CG, 2=HVCI, 3=SystemGuard, 4=SMM, 5=APIC, 6=SecureMOR, 7=SecureKernel, ...}
```

### HVCI (Hypervisor-protected Code Integrity)

VTL1 enforces that VTL0 kernel pages can be either writable OR executable, never both (W^X in VTL0). Page table modifications marking RX require VTL1 approval via EPT hypercall — `securekernel` verifies signature against CI policy (`SIPolicy.p7b`).

Consequences:

- Classic kernel shellcode injection dead: allocating a kernel RWX buffer impossible; `ExAllocatePool(NonPagedPoolExecute)` returns memory that VTL1 refuses to mark executable.
- Driver code must be signed and whitelisted (WHQL + Microsoft CI policy).
- BYOVD still works because driver IS signed — but the attacker's derived capability is DKOM (data edits), not code injection into ring 0.
- Writing to existing kernel code (`.text`) blocked — page protection prevents, PatchGuard reinforces.

### Credential Guard / LSAIso

LSASS is split: classic `lsass.exe` runs in VTL0; a minimal `LsaIso.exe` runs in VTL1 holding the credential material (NTLM hashes, Kerberos keys). VTL0 LSASS calls into VTL1 via controlled surface for auth operations — cannot read the keys directly.

Impact:

- `mimikatz sekurlsa::logonpasswords` on CG host returns LUKS-style blobs instead of plaintext — useless.
- Kerberos TGT/TGS extraction via `sekurlsa::tickets` similarly defanged.
- NTLM hash extraction dead for CG-protected logon sessions (interactive, RemoteInteractive).
- Workarounds: coerce authentication to attacker endpoint (Potato/Coerce), DPAPI master-key theft where possible (still accessible via SYSTEM without CG protection), token theft from open sessions.

CG protects **credentials at rest**. Token theft (impersonation) still works because tokens are VTL0 objects. See [tokens-privileges.md](tokens-privileges.md).

### SMM / System Guard

SMM protections (Secure Memory Mode) add firmware-layer guarantees. System Guard Secure Launch (DRTM) uses AMD SKINIT or Intel TXT to re-measure the chain on every boot. Offensively out of scope — firmware-level attacks against SMM are APT-grade.

## Userland hooking — what EDRs do

EDR agent injects a DLL into every process. That DLL inline-hooks selected `ntdll` / `kernelbase` / `amsi` / `winhttp` functions. Typical patched functions:

```
ntdll!NtCreateThreadEx
ntdll!NtAllocateVirtualMemory
ntdll!NtAllocateVirtualMemoryEx
ntdll!NtProtectVirtualMemory
ntdll!NtWriteVirtualMemory
ntdll!NtReadVirtualMemory
ntdll!NtMapViewOfSection
ntdll!NtMapViewOfSectionEx
ntdll!NtUnmapViewOfSection
ntdll!NtCreateSection
ntdll!NtSetContextThread
ntdll!NtGetContextThread
ntdll!NtQueueApcThread
ntdll!NtQueueApcThreadEx
ntdll!NtResumeThread
ntdll!NtCreateUserProcess
ntdll!NtOpenProcess
ntdll!NtOpenThread
ntdll!NtDuplicateObject
ntdll!LdrLoadDll
ntdll!LdrGetProcedureAddress
kernelbase!CreateFileW
kernelbase!CreateProcessInternalW
kernel32!WinExec
amsi!AmsiScanBuffer
wininet!HttpSendRequestW
winhttp!WinHttpSendRequest
```

Hook types:

- **5-byte jump**: `E9 XX XX XX XX` pattern at function entry. 32-bit RIP-relative jump to EDR trampoline. Standard for x64 when hook in same 2GB range.
- **14-byte jump**: `FF 25 00 00 00 00 + imm64` for arbitrary absolute. More robust, more recognizable.
- **Hot-patch (2-byte)**: `EB F9` backward jump into a 5-byte patch region preceding the function (Microsoft hot-patchable prologue convention: `MOV EDI, EDI` → `JMP`).
- **IAT hook**: patch import table entries. Less common in modern EDRs.
- **Breakpoint hook (INT 3)**: rare; used by some specialty products.

### Detection of hooks

Compare in-memory `.text` of `ntdll` against the on-disk copy. Any mismatch at function entry is a hook. Pseudocode:

```c
HMODULE hNtdll = GetModuleHandleW(L"ntdll.dll");
PIMAGE_NT_HEADERS nt = ImageNtHeader(hNtdll);
PIMAGE_SECTION_HEADER text = find_section(nt, ".text");

HANDLE hFile = CreateFileW(L"C:\\Windows\\System32\\ntdll.dll", GENERIC_READ, ...);
HANDLE hMap  = CreateFileMapping(hFile, NULL, SEC_IMAGE|PAGE_READONLY, 0, 0, NULL);
LPVOID pDisk = MapViewOfFile(hMap, FILE_MAP_READ, 0, 0, 0);

BYTE* memText  = (BYTE*)hNtdll + text->VirtualAddress;
BYTE* diskText = (BYTE*)pDisk  + text->VirtualAddress;

if (memcmp(memText, diskText, text->Misc.VirtualSize) != 0) { /* hooked */ }
```

### Unhooking strategies

1. **Fresh-copy unhook**: map pristine `ntdll` from disk (`NtCreateSection(SEC_IMAGE)` on disk file), copy `.text` into current process `ntdll` `.text`. Requires `VirtualProtect` to RWX briefly. Effective vs naive hook-scanning EDRs; detectable by kernel callbacks watching protection transitions.
2. **KnownDlls unhook**: open `\KnownDlls\ntdll.dll` section (always the signed, non-hooked image), map into process, copy `.text`. No disk I/O, EDR agent cannot have pre-hooked this mapping. Detection: `ObRegisterCallbacks` may strip `SECTION_MAP_*` access to sections; kernel-side callbacks see the handle open.
3. **Suspended-process unhook**: spawn suspended child, read pristine `ntdll` `.text` from its memory (before EDR DLL injection completes) — race-condition-sensitive. Modern EDRs inject synchronously or before first user-mode instruction, closing this window.
4. **Perun's Fart**: read `ntdll` from a freshly suspended process with creation flag combinations that delay DLL injection. Still works against some agents.
5. **Syscall stub rebuilding**: synthesize your own syscall stubs (Hell's Gate / DWhisper) without touching `ntdll`. See [syscalls.md](syscalls.md). Best current answer — avoid the hooked path entirely.
6. **Hardware breakpoints**: set DR0-DR3 on hooked functions, VEH fixes register state and skips. No memory write. Good for AMSI specifically; less practical for full syscall coverage.

### Indirect syscalls as unhook alternative

Instead of unhooking, bypass the hook by jumping past it. The pattern `mov r10, rcx; mov eax, SSN; syscall; ret` inside ntdll is unhooked 99% of the time — only function entry is patched. Indirect syscalls:

1. Resolve SSN from ntdll exports (Hell's Gate).
2. Find a `syscall; ret` gadget in a ntdll `Nt*` function (any one — `Nt` stubs all end the same).
3. Set up RAX (SSN), R10=RCX (first arg), other args, then jump to the gadget.

From [syscalls.md](syscalls.md):

```asm
mov  r10, rcx
mov  eax, SSN
jmp  [gadget_syscall_ret_in_ntdll]
```

EDR hook at function entry is skipped. Kernel callbacks (ETW-TI) still fire — they observe the syscall after the SYSCALL instruction lands in ring 0.

## Call-stack spoofing

See [exception-unwind.md](exception-unwind.md) for full detail. Summary:

- EDR hook in `NtCreateThreadEx` might inspect the call stack to see "legitimate" caller.
- A thread stack with frames `ntdll!NtCreateThreadEx ← evil_shellcode ← 0x00000000` is suspicious.
- Desired appearance: `ntdll!NtCreateThreadEx ← kernelbase!CreateThread ← kernel32!BaseThreadInitThunk ← RtlUserThreadStart`.
- Achieved by either return-address-spoofing (SilentMoonwalk / Draugr — replace return addresses before call and restore after) or fully synthesized stack (`RtlAddFunctionTable` fake unwind info).

Detection-side:

- `RtlCaptureStackBackTrace` from within the syscall path — if invoked by an EDR's pre-handler hook, sees the spoofed stack.
- `RtlVirtualUnwind` walks via `.pdata` — if fake unwind entries registered via `RtlAddFunctionTable`, they're honored.
- Out-of-process stack walk via `StackWalk64` on external analysis: same semantics.
- The real defensive answer is ETW-TI events — the syscall fired regardless of who appears to have called it. Stack spoof evades userland hook telemetry but NOT kernel telemetry.

## Scanner evasion

Static / memory scanners look for:

1. **MZ/PE header** at allocation bases — obscure by not keeping PE header in memory after load, or mangle magic.
2. **Known malware strings**: encrypt all strings, decode at use-time only. Never plaintext API names.
3. **Known hash-of-import** patterns: use unique hash function per build (salt-parameterized DJB2).
4. **Sleep-obfuscation patterns**: memory that is RX at scan but RW at sleep (Ekko/Deathsleep/Zilean). Defender scans only during specific intervals; sleep obfuscation schedules encrypt → sleep → decrypt cycles to coincide with non-scan windows. Advanced scanners trigger on any RX → RW → RX transition via ETW-TI `EtwTiLogProtectExecVm`.

### Sleep obfuscation patterns

- **Ekko** (timer-queue based): uses `CreateTimerQueueTimer` with `RtlCaptureContext` / `NtContinue` chain; timer fires → encrypt memory + stack → sleep → decrypt. Stack is RX during sleep but contains encrypted data only.
- **Zilean** (`WaitForSingleObjectEx`-alertable based): APC-based wake.
- **Foliage**: fibers + APC.
- **Deathsleep** (SilentMoonwalk-inspired): encrypt and hide entire heap allocation; unhide via spoofed unwind.

All share: temporarily remove executable rights from the beacon memory during sleep. Scanner looking for `MZ` in RX memory finds nothing during sleep. Wake restores RX, re-encrypts when sleeping again.

Modern EDR detections:

- ETW-TI `EtwTiLogProtectExecVm` fires on every RX→RW→RX dance. Kernel pipeline counts transitions per process; sustained high-rate transitions trigger alert.
- Stack walk during sleep: if thread is sleeping in `NtWaitForSingleObject`, stack frames from `NtWaitForSingleObject ← Beacon ← ...`. Modern sleep obfuscation spoofs these to appear coming from legitimate Windows threads.

## Detection table (unified)

| Technique | Kernel signal | Userland signal | Neutralized by |
|---|---|---|---|
| Classic `CreateRemoteThread` | `EtwTiLogQueueApcThread`-adjacent? No — direct `PsSetCreateThreadNotifyRoutine` fires | hook on `kernel32!CreateRemoteThread` / `ntdll!NtCreateThreadEx` | Manual thread creation is hard to hide; prefer hijack or APC |
| `NtCreateThreadEx` remote | `PsSetCreateThreadNotifyRoutine` fires | ntdll hook | Kernel callback is not bypassable from userland — this pattern is detected |
| `NtQueueApcThreadEx` on alertable remote thread | `EtwTiLogQueueApcThread` | ntdll hook | Same; Special APC (`NtQueueApcThreadEx2` w/ flag 0x1) may be quieter but still fires kernel event |
| `NtWriteVirtualMemory` cross-process | `EtwTiLogWriteVm` | ntdll hook | Avoid entirely — map section instead of direct write |
| `NtAllocateVirtualMemory` RWX | `EtwTiLogAllocExecVm` | ntdll hook | Allocate RW, NtProtect to RX only when needed; still fires `EtwTiLogProtectExecVm` |
| `NtMapViewOfSection` local | Lightweight | ntdll hook | Section created privately (not SEC_IMAGE) doesn't fire image-load callback |
| `NtMapViewOfSection` SEC_IMAGE | `PsSetLoadImageNotifyRoutine` fires | ntdll hook | Manual PE loading (no section at all) doesn't fire image-load callback |
| Syscall via ntdll stub | Syscall handler fires every ETW-TI event regardless | ntdll hook at stub entry | Indirect syscall skips userland hook; kernel events still fire |
| Direct syscall (custom assembly) | Same kernel events | No userland hook hit | — |
| Process hollowing | `PsSetCreateProcessNotifyRoutineEx2` fires (child spawn), `EtwTiLogWriteVm` (write to suspended) | multiple ntdll hooks | Detected via write-to-suspended-child pattern |
| Module stomping | No image-load event (writing into existing mapping) | `NtProtectVirtualMemory` to RX → ETW-TI | Quieter than hollowing; still hits ProtectExecVm |
| Phantom DLL hollowing (TxF) | `PsSetLoadImageNotifyRoutine` shows original file contents; discrepancy detectable | — | Requires transaction support (WoW64 subsystem path); TxF deprecated on recent builds |
| Thread hijack + `NtSetContextThread` | `EtwTiLogContextModification` (cross-process) | ntdll hook | Same-process hijack (inside own process) does NOT fire context-mod ETW-TI |
| Sleep obfuscation | `EtwTiLogProtectExecVm` every encrypt/decrypt cycle | — | Frequency + pattern triggers EDR heuristics; mitigate via timing variance |
| AMSI patch | — | EDR's internal AMSI integrity check if any | Patch bytes variant, hardware-breakpoint bypass |
| ETW patch (EtwEventWrite) | — | — | Irrelevant to kernel ETW-TI; silences only process-local userland ETW |
| Hook removal | `NtProtectVirtualMemory` to RWX on ntdll .text → `EtwTiLogProtectExecVm`! | — | Never unhook; use indirect syscalls |
| BYOVD | `PsSetLoadImageNotifyRoutine` on driver | Service install event (4697) | HVCI blocks load-time if driver on blocklist |
| Token steal (LSASS) | `ObRegisterCallbacks` strips write access | Opened w/ reduced rights | LSASS as PPL blocks even SYSTEM from opening with VM_READ; SeDebugPrivilege does not override PP |

## Practical evasion hierarchy (2026)

1. **Avoid userland hooks entirely**: indirect syscalls via Halo's/Tartarus Gate.
2. **Avoid cross-process primitives** when possible: in-process execution avoids `EtwTiLog*Remote` variants.
3. **Avoid executable-memory transitions**: keep code in .text of a benign module (module stomping with care), or design for infrequent RX-toggle.
4. **Call-stack spoof userland hooks**: even if indirect syscall used, some EDRs do out-of-band stack walks on events — spoofed stack buys deniability.
5. **Minimize high-signal syscalls**: `NtQueueApcThread`, `NtSetContextThread` (cross-process), `NtWriteVirtualMemory` (cross-process) are ETW-TI tripwires. Prefer alternatives (local threads, code-cave patching via section mapping).
6. **Accept the kernel signal if the syscall must happen**: nothing in userland silences ETW-TI. The only question is whether the event correlates to "malicious" in the EDR's ruleset. Pacing, pattern variation, and benign-looking parameters matter.
7. **BYOVD only when necessary**: once ring 0, the full arsenal opens (ETW-TI provider disable, PatchGuard-level callback removal) but the BYOVD driver itself is high-signal to load (event 4697, `PsSetLoadImageNotifyRoutine`).
8. **Credential access**: LSASS dump with CG off → classic, detected heavily. CG on → shift to coerce / token theft. Silver-bullet alternative: in-memory dumper (`MiniDumpWriteDump` replacement) on non-PPL LSASS with silent handle-access path.
9. **Persistence**: avoid Run keys, Scheduled Tasks, Services (all high-signal via Event Log + Sysmon). Prefer DLL sideloading, COM hijack with offline-accessible CLSIDs, AppInit/AppCert (blocked on modern builds; ignore), Image File Execution Options (IFEO), Office templates, WMI event subscription (high-signal but less monitored by default).

## Supporting observability: what you CAN see as an analyst

Quick host surveys to understand the battlefield:

| Check | Command | Info |
|---|---|---|
| Defender running | `Get-MpComputerStatus` | Real-time protection, engine version, tamper protection |
| VBS / HVCI / CG state | `Get-CimInstance Win32_DeviceGuard ...` | VBS status, running services |
| EDR agent | `fltmc.exe` | Loaded minifilters (altitude + driver name) |
| Kernel callbacks | Driver-mapped tools (kprocesshacker) | Callback arrays |
| ETW sessions | `logman query -ets` | Active trace sessions and consumers |
| Installed drivers | `driverquery /v` | Full driver list with state |
| Process mitigations (per process) | `Get-ProcessMitigation -Id <pid>` | CFG/ACG/CIG/CET/etc state |
| CET capability | `coreinfo.exe -v` | CPU features |
| AMSI registered providers | `reg query HKLM\Software\Microsoft\AMSI\Providers` | CLSID list |

Cross-reference with `tasklist /m <dll>` to identify which processes hold which EDR DLL before making tradeoff decisions.
