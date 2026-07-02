# Dynamic-linker resolver pivots

Load when a leakless exploit can modify loader or DSO metadata and can reach `_dl_fixup` through an unresolved PLT entry.

## Prove resolver reachability first

Do not equate an unresolved slot with a reachable slot.

1. Enumerate unresolved `JUMP_SLOT` relocations in every relevant object.
2. Trace the complete exploit input and record which PLT stubs are actually called.
3. Vary parser lengths and allocation thresholds; internal scratch-buffer growth, locale handling, or error paths can introduce lazy calls absent from normal inputs.
4. Break at the PLT stub, `_dl_runtime_resolve`, and `_dl_fixup`.
5. Reject triggers that occur before required metadata staging or after the process destroys it.

Use the final payload state. A clean-process trigger is only a candidate if earlier heap or stdio corruption leaves the same path viable.

## Model the forged lookup

Record the exact loader build and live `link_map` before changing dynamic tags. For each planned resolution, capture:

```text
object and link_map:
relocation index and symbol index:
effective DT_SYMTAB / DT_STRTAB / DT_JMPREL:
fake Elf64_Sym address:
fields read by this _dl_fixup path:
resolved address formula:
destination GOT slot:
```

Derive these fields from the target loader's disassembly and live memory. Do not import structure offsets from another glibc build.

When redirecting `DT_SYMTAB` to writable storage, verify symbol alignment:

```text
fake_sym = effective_symtab + symbol_index * sizeof(Elf64_Sym)
```

Write only fields the resolver consumes. Minimal writes reduce collisions with adjacent GOT entries, loader state, or application data. Snapshot neighboring qwords before staging and watch them through the trigger.

## Chain resolver calls when the first ABI state is insufficient

The first resolved target inherits registers from the real lazy call site. If the useful pointer is not in `rdi`:

1. Photograph all argument and callee-saved registers at the unresolved stub.
2. Find a base-relative gadget or function fragment that moves the useful register into `rdi`.
3. Prefer a fragment that calls a second unresolved PLT entry.
4. Forge the first symbol to resolve to that fragment.
5. Forge the second symbol to resolve to the final function or entry.
6. Break at both resolver invocations and the final target.

Treat the chain as:

```text
real lazy call -> resolver #1 -> register-transfer fragment
               -> second lazy call -> resolver #2 -> final target
```

Verify that the first resolution does not overwrite metadata needed by the second.

## Recheck ABI and representation constraints

- A resolver jump can enter a function with different stack parity than a normal compiler-generated call. If the target faults on `movaps`, record `rsp % 16` at entry and at the fault.
- Prefer an alignment-preserving fragment. Use a shifted internal entry only when its skipped prologue effects are understood and the objective is completed before any unsafe epilogue.
- Inspect command and string storage after the trigger begins. Parser or stdio fields may overlap the chosen bytes and replace the terminator.
- If controlled bytes overlap a lock or pointer field, prove the runtime path no longer dereferences it; do not label padding by appearance alone.
- Validate the actual success oracle. A captured output or one-shot objective may succeed even if the process crashes after the decisive child or syscall completes.

## Final evidence gate

Require one trace containing:

- staged dynamic tag and fake-symbol bytes
- first lazy stub and `_dl_fixup` arguments
- first resolved target and register transfer
- second lazy stub and `_dl_fixup` arguments
- final target entry, stack alignment, and complete first argument
- objective output or syscall result

Then replay outside the debugger with ASLR enabled for the full number of independent processes required by the service.
