---
name: fsop-dev
description: "Auth/lab dev: glibc FILE/FSOP exploitability research; libio structures, vtables, wide data, trigger paths, mitigation-aware modeling."
license: MIT
compatibility: "glibc/libio-focused Linux user-mode exploitability research; Primarily relevant to glibc 2.23 through current post-hook builds."
metadata:
  author: AeonDave
  version: "1.0"
  category: exploitation
  language: c,cpp,asm,python
---

# FSOP Development

Goal: turn FILE-structure corruption into the **right libio dispatch path** for that glibc era, trigger surface, and endgame — not into random `_IO_FILE` cargo cult.

Repository positioning: keep `offensive-coding/heap-exploitation-dev` as the allocator and overlap router, then switch here once success depends more on **libio structure modeling, validated jump-table reuse, wide/codecvt/cookie-file dispatch, or trigger choice** than on heap choreography itself.

## When to activate

- Heap, UAF, overlap, arbitrary write, partial overwrite, or stream-adjacent corruption reaches `stdin`, `stdout`, `stderr`, another `FILE *`, or a fake `FILE` region.
- The exploit reaches a heap-allocated or dangling stream from `fopen`/`fdopen`/custom `FILE *`, and the real question becomes how `fputs`/`fwrite`/cleanup will consume it.
- Need to decide whether the target is classic `_IO_list_all`, vtable-misalignment, `_wide_vtable`, `_codecvt`, obstack, or leak-only FILE abuse.
- Hooks are removed or unrealistic, and the real exploit question is whether FSOP beats return-address, callback, or data-only alternatives.
- Need to reason about `FILE`, `_IO_FILE_plus`, `_IO_wide_data`, `_IO_codecvt`, pointer-guard-adjacent surfaces, or valid jump-table placement.
- Need a hint-style recognition pass for stream corruption opportunities before building a full heap chain.
- The initial bug is not purely “heap-themed” anymore — for example, a relative libc write into a standard stream, an mmapped chunk reaching libc FILE data, or a direct stream-specific corruption bug.

If the problem is mostly allocator selection, heap shaping, tcache/largebin choreography, or House-family routing before the stream overlap exists, start with `offensive-coding/heap-exploitation-dev` and return here once FSOP is a real candidate.

## First classify the FSOP problem

1. **Identify the stream target**
   - `stdout` for output-driven paths like `puts`, `printf`, `fflush`
   - `stderr` for low-noise or assert/abort-driven paths
   - `stdin` for leak or arbitrary-read/write redirection
   - custom `FILE *` / `fopen` object / socket-backed stream / heap fake FILE
2. **Identify the glibc era**
   - pre-2.24: no vtable validation
   - 2.24+: vtable range validation
   - 2.34+: hooks removed, FSOP becomes first-class endgame
   - 2.35+ / modern: `_wide_vtable`, codecvt, and angr-mapped paths matter more than fake raw heap vtables
3. **Decide the capability you actually need**
   - leak arbitrary memory
   - arbitrary read/write through buffer redirection
   - direct PC control / indirect call
   - `setcontext` pivot / ORW / SUID-safe chain
   - exit-time or assert-time execution
4. **Map the available corruption**
   - full stream overlap / arbitrary write into stream
   - only a few stable fields
   - only `vtable`-adjacent control
   - only `_wide_data` or `_codecvt` reachability
   - only trigger-side influence with limited field control
5. **Choose the natural trigger surface**
   - `puts`, `printf`, `fprintf`, `fwrite`
   - `fflush`, `fclose`, `setbuf`, sync/finish paths
   - `exit`, `return from main`, abort/assert, `__malloc_assert`
   - read-side paths like `fgets`, underflow/seekoff, orientation switches

## Era-first selection

| Era | Bias toward | Avoid or de-prioritize |
|---|---|---|
| glibc <= 2.23 | classic fake vtable, `_IO_list_all`, `_IO_OVERFLOW`, raw FILE-chain abuse | post-hook-only thinking |
| glibc 2.24-2.33 | vtable-misalignment, validated jump-table reuse, `_wide_vtable` routes, leak-first stream abuse | fake heap vtable pointers outside libc vtable section |
| glibc 2.34+ | House of Apple 2/3, `_wide_vtable`, codecvt, stderr/stdout overlap, `setcontext`/ORW endings | `__free_hook` nostalgia |
| glibc 2.35+ and modern | angry-FSROP paths, `_IO_wdoallocbuf`, `_IO_switch_to_wget_mode`, codecvt, obstack, TLS/pointer-guard-adjacent pivots | assuming only one Apple chain exists |

## Technique families worth prioritizing

| Family | Good fit | Typical result | Reality check |
|---|---|---|---|
| classic `_IO_list_all` FSOP | pre-vtable-check or controlled valid vtable path | exit-time `_IO_overflow` dispatch | foundational, but not the modern default |
| stdout/stderr overlap | arbitrary allocation/write over standard streams | trigger via normal output, `fflush`, or assert path | still one of the best practical setups |
| buffer redirection | control `_IO_read_*` / `_IO_write_*` ranges | arbitrary read/write or targeted leak | not all FSOP ends in RIP control |
| vtable misalignment | validated vtable section but wrong slot alignment | call a different libc libio function than intended | central post-2.24 concept |
| House of Apple 2 | `_wide_data->_wide_vtable` reachable | direct call, `system`, or `setcontext` | primary post-hook baseline |
| House of Apple 3 | `_codecvt` path easier than wide-data path | indirect call through codecvt helper | higher setup cost, but powerful |
| obstack paths | stream or neighboring stream state controllable | call via `_obstack_newchunk` | underused but real |
| leak-oriented FSOP | need TLS/libc/stack/tcb leak more than immediate RCE | stdout/stderr disclosure, pointer-guard recovery | often better than forcing shell-first |
| pointer-guard-adjacent FSOP | TLS/pointer-guard or encrypted callback surfaces in play | unlock later destructor/cookie-file hijack | usually a bridge, not the first stage |

## Hint-mode recognition rules

Load `references/hints-and-recognition.md` when triaging quickly. The shortest recognition cues are:

- If you can overlap `stdout` or `stderr`, ask **which natural call path touches it next** before chasing ROP.
- If the `vtable` must stay inside libc, ask **which misaligned slot or alternate jump table** gives the call you want.
- If `_wide_data` is reachable, ask **can I force `_IO_wdoallocbuf` or `_IO_WOVERFLOW`?**
- If `_codecvt` is reachable, ask **is this really Apple 3 / codecvt-in/out/length?**
- If a heap exploit already gives largebin/tcache positioning over a stream, bias toward FSOP before exotic leakless Houses.
- If seccomp or SUID makes `system("/bin/sh")` weak, bias toward `setcontext`, ORW, or a leak-first destructor chain.
- If normal output mangles your crafted state, prefer `stderr` or assert-time dispatch.

## Trigger-driven rules

- **`puts` / `printf` / `fprintf`**: excellent when stdout is the target and you can satisfy byte-oriented path checks.
- **`fflush` / sync / finish**: strong when you want a quieter dispatch point or an internal sync path.
- **`exit` / return from `main`**: best when `_IO_list_all` traversal or cleanup logic is your dispatch engine.
- **abort / `__malloc_assert`**: strong when only failure-driven flushing is realistic; think Cat/Kiwi/Apple-style assert triggers.
- **read-side functions**: use when the win is disclosure or when underflow/seekoff/orientation paths reach `_wide_vtable` or codecvt.

## Endgame selection

- **Need simplest post-hook RCE**: House of Apple 2 first.
- **Need SUID-safe or seccomp-safe execution**: `setcontext` pivot, ORW, or structured ROP over `system`.
- **Need arbitrary disclosure or pointer-guard recovery**: leak-oriented stdout/stderr FSOP first, execution second.
- **Need valid-target, libc-internal dispatch with few writes**: pick a misalignment or angry-FSROP path with the smallest stable field set.
- **Have a cheaper application-owned callback overwrite already**: do not force FSOP just because it is glamorous.

## Reliability checklist

- Confirm the exact glibc version and whether your offsets match the target build.
- Separate **overlap/corruption**, **dispatch path**, and **endgame**.
- Keep `_lock` valid and writable unless the chosen path proves it will not be touched.
- Track whether `_mode` must stay negative, become positive, or remain zero for the intended path.
- Re-check whether read/write helpers will clobber `_IO_read_*`, `_IO_write_*`, `_wide_data`, or adjacent bytes before dispatch.
- Verify whether the chosen path expects byte-oriented, wide-oriented, or codecvt-backed state.
- Prefer the stream whose normal use interferes least with your crafted layout.
- If the chain rewrites a libc GOT/relocation target or relies on a low-byte pointer patch, load [`pwn-ctf` RELRO/ASLR relocation guidance](../../offensive-ctf/pwn-ctf/references/relro-aslr-relocations.md) and prove object-specific RELRO, page permissions, and ASLR invariance first.

## Anti-patterns

- Treating every FILE corruption as House of Apple 2.
- Overwriting a vtable pointer to raw heap memory on glibc with validation enabled.
- Forgetting that many FSOP wins are leak/read/write primitives, not immediate PC control.
- Recommending `system("/bin/sh")` on SUID or seccomp targets by reflex.
- Ignoring normal stream activity that mutates `_IO_write_ptr`, `_IO_buf_base`, `_mode`, or `_flags` before the trigger fires.

## Resources

- [references/libio-model-and-eras.md](references/libio-model-and-eras.md) — `FILE`, `_IO_FILE_plus`, `_IO_wide_data`, `_IO_codecvt`, vtable validation, and era map.
- [references/canonical-fsop-families.md](references/canonical-fsop-families.md) — classic `_IO_list_all`, Apple 2/3, Pig, Cat, Kiwi, Emma, and where angry-FSROP paths fit.
- [references/triggers-and-call-paths.md](references/triggers-and-call-paths.md) — `puts`, `printf`, `fflush`, `exit`, assert/abort, underflow, seekoff, and why some paths are cleaner than others.
- [references/hints-and-recognition.md](references/hints-and-recognition.md) — fast hint-mode triage, constraint heuristics, target-selection rules, and endgame cues.

Load references only after the target stream, glibc era, available corruption, and intended trigger are clear.
