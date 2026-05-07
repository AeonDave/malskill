# Windows Pwn Patterns

Use this reference for Windows-native binary exploitation patterns that do not fit the Linux-first `overflow.md`, `rop.md`, or `advanced-primitives.md` references.

## Table of Contents
- [SEH overwrite and DEP bypass](#seh-overwrite-and-dep-bypass)
- [Privilege abuse after code execution](#privilege-abuse-after-code-execution)
- [CFG-aware call-target hijacks](#cfg-aware-call-target-hijacks)
- [Position-independent API resolution shellcode](#position-independent-api-resolution-shellcode)

## SEH overwrite and DEP bypass

### Windows SEH Overwrite + `pushad` VirtualAlloc ROP

This is the classic 32-bit Windows chain for binaries with:
- ASLR enabled,
- DEP enabled,
- GS enabled,
- SafeSEH disabled or otherwise bypassable.

Reliable sequence:
1. use a format-string or equivalent info leak to derive the module base,
2. trigger a buffer overflow that reaches the SEH chain,
3. pivot from the exception handler into a ROP buffer,
4. use a short ret-slide to absorb crash-offset jitter,
5. preload registers for `VirtualAlloc`,
6. use `pushad` to build the whole call frame in one instruction,
7. jump into freshly executable shellcode.

Why `pushad` matters:
- good `mov [esp+N], reg` gadgets are rare in 32-bit PE ROP,
- `pushad` pushes all eight general-purpose registers in call-friendly order,
- once the registers are staged, DEP bypass becomes compact and reliable.

Practical notes:
- resolving `VirtualAlloc` indirectly from a nearby imported API such as `TlsAlloc` is often easier than hunting a direct import,
- bad characters frequently include `\x00`, whitespace, and `%` when the initial bug is format-string-adjacent,
- thread-based servers may need a detached launcher process because the original thread can die after exploitation.

## Privilege abuse after code execution

### SeDebugPrivilege to SYSTEM

If a landed Windows context has `SeDebugPrivilege`, treat it as a near-direct path to SYSTEM.

Fast path:
1. confirm privileges with `whoami /priv`,
2. enable or use the debug privilege in your post-exploitation tool,
3. migrate or inject into a SYSTEM-owned process such as `winlogon.exe`,
4. inherit SYSTEM context.

Key idea:
- even when shown as "Disabled", this privilege is often activatable by the current token,
- the privilege is more important than local admin cosmetics because it authorizes debugging and code injection into higher-privilege processes.

## CFG-aware call-target hijacks

### Windows CFG Bypass Using `system()` as Valid Call Target

Control Flow Guard blocks jumps to arbitrary addresses, but it does not block jumps to legitimate exported function entry points.

Exploit rule:
- overwrite a function pointer, vtable entry, or callback with `system()` from `msvcrt`,
- provide a controlled first argument string,
- let CFG bless the call because `system()` is a valid call target.

Practical payload notes:
- when spaces are filtered, `cmd.exe` often tolerates commas as argument separators,
- `^` is useful for escaping characters in command strings under restrictive filters.

This is not a CFG bypass in the sense of defeating the bitmap; it is a control-target substitution that remains CFG-valid.

## Position-independent API resolution shellcode

### Windows x64 PEB-Walk Shellcode

When shellcode must survive ASLR without imports, walk the PEB at `gs:[0x60]`, locate `kernel32.dll` through loader lists, parse its export table, and resolve APIs such as `WinExec` or `CreateProcessA` by name.

Core chain:
- `gs:[0x60]` → PEB
- `PEB + 0x18` → `PEB_LDR_DATA`
- loader list walk → `kernel32.dll` base
- parse PE export directory
- locate target API by name or name hash
- call the resolved function with position-independent data

Useful shellcode habits:
- keep the stack aligned before API calls,
- avoid hardcoded addresses entirely,
- use arithmetic tricks for immediate values when bad-byte filtering applies,
- prefer API-name matching or hashing over fixed offsets.

This is the Windows analogue of ELF shellcode that resolves symbols at runtime instead of trusting libc offsets.

## See also

- `exotic-arch.md` — ARM32/ARM64, RISC-V, and MIPS exploitation notes
- `advanced-primitives.md` — pointer-guarded exit handlers, runtime pivots, and general weird-edge exploit patterns
- `sandbox.md` — command execution, fd tricks, and restricted-environment escapes that may follow Windows or mixed-platform footholds
