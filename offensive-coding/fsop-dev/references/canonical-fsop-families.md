# Canonical FSOP families

Load when selecting an FSOP target family (`_IO_list_all`, Apple, Kiwi, etc.) for a specific glibc era.

## Table of Contents
- [Classic `_IO_list_all` and fake-vtable FSOP](#classic-_io_list_all-and-fake-vtable-fsop)
- [Stream overlap and buffer redirection](#stream-overlap-and-buffer-redirection)
- [Historical heap-landed FILE attacks](#historical-heap-landed-file-attacks)
- [House of Apple 2](#house-of-apple-2)
- [House of Apple 3](#house-of-apple-3)
- [Other named families](#other-named-families)
- [Where angry-FSROP fits](#where-angry-fsrop-fits)
- [Selection rules](#selection-rules)

## Classic `_IO_list_all` and fake-vtable FSOP

**Best fit:** glibc without vtable validation, or niche situations where a valid call chain still lands on `_IO_list_all` traversal.

**Core idea:** forge a fake `FILE` chain reachable from `_IO_list_all`, satisfy flush checks, and trigger `_IO_overflow`-style dispatch during cleanup.

**Why it still matters:**

- it explains the original FSOP mental model
- many later techniques are better understood as answers to what broke in this classic path
- cleanup and chain traversal still matter even when the raw fake-vtable trick does not

**Reality check:** do not teach this as the default modern route.

## Stream overlap and buffer redirection

**Best fit:** you can allocate over `stdout`, `stderr`, or `stdin`, but code execution is not yet the shortest path.

**Core outcomes:**

- leak libc, stack, TLS, or other memory via `_IO_write_base` / `_IO_write_ptr`
- redirect input/output buffers for arbitrary read/write
- prepare later pointer-guard, destructor, or callback abuse

**Why it matters:** some of the strongest modern FSOP wins are leak-first.

## Historical heap-landed FILE attacks

These are worth knowing because many real exploit chains **arrive from heap bugs**, but the win condition is still FILE/libio logic.

### Fastbin `stdout` two-stage hijack

- old-school overlap of `_IO_2_1_stdout_`
- first stage redirects a vtable slot to an input primitive like `gets`
- second stage rewrites the stream again into `system`

Treat it as a historical reminder that FILE attacks often begin as heap placement problems but become **dispatch-path problems** immediately after the overlap exists.

### `stdin` `_IO_buf_base` null-byte redirection

- off-by-one / null-byte corruption lands `_IO_buf_base` inside the FILE struct near `_short_buf`
- next `scanf` / `fgets` writes into the stream itself
- follow-up read turns into arbitrary write or a hook-era endgame

This is a classic hybrid route: heap primitive first, FILE self-overwrite second.

### glibc 2.24+ two-hop vtable-validation bypass

- keep the main vtable inside the validated libc section
- abuse an internal sub-function or offset relationship that reaches an unchecked second dereference
- useful mostly as a historical bridge between “fake raw vtable” and “modern path hunting”

### Unsorted-bin attacks on `stdin` / `mp_`

- overwrite `stdin` buffer bounds or nearby libc globals via unsorted-bin writes
- next stdio call becomes disclosure or a hook-era write-what-where bridge

Use these patterns to recognize **heap-to-FILE hybrids**, not as the full modern FSOP playbook.

## House of Apple 2

**Best fit:** post-hook glibc, writable stream overlap or fake FILE placement, and reliable access to `_wide_data`.

**Core idea:** steer the main stream dispatch into a wide-character path, then reach `_IO_wdoallocbuf` / `_IO_WDOALLOCATE` so the unvalidated `_wide_vtable` dispatches to an attacker-chosen function.

**Typical ending:**

- `system(fp)` / `system("sh")`-style shelling on permissive targets
- `setcontext` pivot for ORW or SUID-safe chains

**Common requirements:**

- main `vtable` still points inside libc vtable section, usually with a deliberate misalignment into `_IO_wfile_jumps`
- `_wide_data` points to attacker-controlled state
- `_wide_data->_IO_write_base == 0`
- `_wide_data->_IO_buf_base == 0`
- `_flags` do not set `_IO_NO_WRITES` or `_IO_UNBUFFERED` in ways that kill the path
- `_lock` stays valid enough for the chosen trigger

**Reality check:** this is the primary post-hook baseline for a reason. Start here before hunting rarer families.

## House of Apple 3

**Best fit:** `_codecvt` is easier to shape than `_wide_vtable`, or the natural misalignment lands in codecvt helpers.

**Core idea:** redirect dispatch into `__libio_codecvt_in`, `__libio_codecvt_out`, or `__libio_codecvt_length`, then use a carefully shaped fake `_IO_codecvt`-backed layout to reach an indirect call.

**What makes it harder:**

- more precise constraints
- awkward register geometry in some paths
- gadget or helper needs may appear where Apple 2 could call directly

**Why it matters:** Apple 3 is not just “Apple 2 but weirder”; it is the codecvt family.

## Other named families

### House of Pig

- historically useful FILE-chain overwrite family
- often described from heap-exploit perspective
- less attractive on modern post-hook builds as a first choice

### House of Kiwi

- assertion or failure-path driven idea, often associated with stderr/sync/`setcontext`-style pivots
- treat as trigger methodology, not default route

### House of Cat

- Apple-adjacent assert/`__malloc_assert`-style recipe using stderr/largebin-driven setup
- good when the natural trigger is allocator failure, not regular output

### House of Emma

- cookie-file and pointer-guard adjacent family
- validated main-vtable setup often pivots into `_IO_cookie_jumps` with a deliberate offset such as `+0x40`
- fake `_IO_cookie_file` layout matters beyond the normal FILE tail: `__cookie` and `__io_functions.write` become the real targets
- often requires pointer-guard recovery, overwrite, or brute-force-informed targeting because callback slots are mangled
- strongest use case is when FSOP must bridge into a guarded callback, `setcontext`, ORW, or another staged pivot instead of a direct `system`

## Where angry-FSROP fits

angry-FSROP is best treated as a **class of path-discovery techniques**, not a single named exploit.

It matters because it shows that modern FSOP is really a search over valid libio call paths and field constraints, not just a small menu of public houses.

Key lessons:

- multiple valid paths exist besides the best-known Apple chains
- obstack and codecvt paths are real, not trivia
- path constraints can be expressed as field predicates, which is excellent for hint-mode triage

Useful path index to keep in your head:

- `_IO_wfile_overflow -> _IO_wdoallocbuf -> _IO_WDOALLOCATE` → Apple-2 baseline
- `_IO_wfile_seekoff -> _IO_switch_to_wget_mode -> _IO_WOVERFLOW` → wide-data alternative when seek/orientation state is friendlier than overflow
- `_IO_obstack_overflow -> _obstack_newchunk` → adjacency-heavy obstack family
- `_IO_wfile_underflow -> __libio_codecvt_in` and `_IO_wfile_sync -> __libio_codecvt_out` / `__libio_codecvt_length` → Apple-3 / codecvt family

That path index matters more than memorizing house names, because modern FSOP selection is really **which validated entry point reaches which unchecked or useful sink with the fewest stable fields**.

## Selection rules

- **Need a default post-hook route** → Apple 2.
- **Need codecvt-backed indirect call** → Apple 3.
- **Need historical heap-to-FILE route recognition** → use the historical section, then remap it to the target glibc era.
- **Need assert/failure dispatch** → Cat/Kiwi-style reasoning.
- **Need leak or arbitrary disclosure first** → stream overlap and buffer redirection.
- **Need guarded callback or encrypted pointer bridge** → Emma/pointer-guard-adjacent reasoning.
- **Need to search beyond public named houses** → load the trigger/hint references and think in angry-FSROP path terms.
