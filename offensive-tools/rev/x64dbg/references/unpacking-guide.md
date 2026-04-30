# x64dbg — Unpacking Guide & OEP Finding

## Core Concept

Packed malware: original code compressed/encrypted into stub. Stub decrypts → jumps to Original Entry Point (OEP). Goal: find OEP, dump, rebuild imports.

## General Unpacking Methodology

```
1. Run sample → stop at system entrypoint
2. Find how the stub decrypts the payload
3. Identify when decryption is complete
4. Break at OEP (first instruction of real code)
5. Dump the unpacked PE from memory
6. Rebuild the Import Address Table (IAT)
7. Load and analyze the clean dump
```

## Method 1: VirtualAlloc + Execute (most common)

```
# Set breakpoints on allocation + execution
bp VirtualAlloc
bp VirtualProtect

F9 (run)
# When VirtualAlloc hits, check 3rd arg (size) and 4th arg (protection):
# r8 (64-bit) or [rsp+10] (32-bit) = flAllocationType
# r9 (64-bit) or [rsp+14] (32-bit) = flProtect (0x40 = PAGE_EXECUTE_READWRITE)

# Execute until return (Ctrl+F9)
# RAX = allocated region address

# Set hardware execute breakpoint on that region:
bphws rax, "x"

F9 → lands at OEP
```

**Command bar alternative:**
```
# Script for VirtualAlloc → OEP
bp VirtualAlloc
run
rtr                        # Return from VirtualAlloc (RAX = alloc base)
bphws rax, "x"             # HW execute BP
run
msg "OEP reached!"
```

## Method 2: mprotect/VirtualProtect (changing permissions)

```
# When packer writes code, then marks it executable:
bp VirtualProtect
F9
# When hit: check last arg (flNewProtect)
# 0x20 = PAGE_EXECUTE_READ
# 0x40 = PAGE_EXECUTE_READWRITE

# After VirtualProtect, set BP on the newly protected region:
# Follow rcx (lpAddress) in disasm → F2 (breakpoint there)
# Or use hardware execute BP on first byte
bphws rcx, "x"
F9
```

## Method 3: TLS Callbacks (anti-debug trick)

```
# Some packers use TLS callbacks executed before OEP
# In x64dbg: Options → Preferences → Events → check "TLS Callbacks"
# x64dbg will break at each TLS callback automatically
```

## Method 4: ESP Trick (classic)

Classic technique for simple packers (UPX, MEW, etc.):

```
1. Run to entrypoint (x64dbg default behavior)
2. Note RSP value (e.g., 0x19FF80)
3. Set HW write watchpoint on RSP - 4 (or RSP value):
   bphws rsp-4, "w"
   (packer pushes registers → will restore ESP → triggers watchpoint)
4. F9 → triggers near OEP when packer restores stack
5. Step (F8) a few times to reach actual OEP (JMP to original code)
```

## Method 5: PUSHAD/POPAD Pattern

Many packers save all registers with PUSHAD at start, restore with POPAD at end.

```
1. At entrypoint, check if first instruction is PUSHAD
2. If yes: set HW write watchpoint on RSP-4 (where POPAD will write ESP):
   bphws rsp-4, "w"
3. F9 → hits when POPAD executes
4. Step to the JMP after POPAD → that's OEP (or very close)
```

## Method 6: Trace (for small packers)

```
# Very small packers (< 1000 instructions):
# Use trace to find JMP to OEP

# Trace Into Conditional Log:
# Debug → Trace Into → set condition: module "mainmodule" == false
# Logs all instructions outside the main module
# When it jumps back → OEP

# Or manual: F8 (step over) watching the IP register
# When IP jumps far (to original code section) = OEP reached
```

## UPX-Specific

```
# UPX is easy — OEP is always after POPAD + JMP

1. Run to EP (x64dbg default)
2. Search for POPAD + JMP pattern:
   Ctrl+F → search "POPAD" in disassembly
3. Set BP on the JMP after POPAD
4. F9 → JMP target = OEP
5. Or: just Ctrl+F for pattern: 61 E9 (POPAD + JMP)

# Alternatively: Plugins → OllyDumpEx → Detect OEP
# Or use upx -d to decompress without debugging
```

## Dumping the Unpacked PE

### With Scylla (recommended)

```
1. At OEP: note the address (shown in EIP register display)
2. Plugins → Scylla (or Ctrl+I if mapped)
3. "IAT Autosearch" → finds IAT automatically
4. "Get Imports" → populates import list
5. Fix invalid imports: right-click invalid → "Trace & Fix" or delete
6. "Dump" → saves raw memory dump
7. "Fix Dump" → patches the dumped file to be a valid PE
   → Select the "raw dump" file from step 6
   → Output: "*.exe_SCY.exe" or similar
```

### Manual dump with x64dbg

```
1. At OEP: Memory Map → find main module (RWX region)
2. Right-click → "Dump Memory to File"
3. Save as "dumped.exe"
4. Header may be wrong — run PE-bear or CFF Explorer to fix PE header
```

## Import Reconstruction

If Scylla's auto-import fails:

```
# Manual IAT fix in Scylla:
1. Get Imports → check the import list
2. Invalid imports show with red X
3. Right-click invalid → "Delete Thunk"
   OR: try "Trace & Fix" to resolve via tracing

# Add missing import manually:
1. Right-click in Imports area → "Add Import"
2. Module: kernel32.dll, Function: CreateFileW, Address: <IAT address>

# Verify after fix:
# Load dumped+fixed binary in IDA/Ghidra → check if imports resolve
```

## Anti-Dump Bypass

Some packers use tricks to prevent dumping:

### SizeOfImage manipulation

```
# Packer sets SizeOfImage too small to hide code
# Fix: in Scylla, before dumping, set SizeOfImage to larger value
# Or use PE editor to fix NT header after dump
```

### PE header wipe

```
# Some packers zero out the PE header in memory
# Fix: restore from disk version or use PE reconstruction tool
# PE-bear or lordPE can help reconstruct
```

### Integrity checks (CRC)

```
# Packer checksums its own code and will crash if patched
# Strategy: fix after dump (CRC happens at runtime, not in dumped file)
# Or: patch the CRC check routine before dumping
```

## x64dbg Script for Automated Unpacking

```javascript
// x64dbg script: auto-find OEP via VirtualAlloc
bp VirtualAlloc
msg "Breakpoint set on VirtualAlloc. Press OK to run."
run

// Loop: run VirtualAlloc until RWX allocation
:loop
rtr                                   // Return from VirtualAlloc
cmp r9, 0x40                          // Check protection = PAGE_EXECUTE_READWRITE
jne :next
msg "RWX allocation found!"
jmp :found

:next
run
jmp :loop

:found
bphws rax, "x"                        // HW exec BP on allocated region
run
msg "Possible OEP found!"
// Now inspect, dump with Scylla
```

## Post-Dump Verification

```
# Verify the dump is valid before loading in disassembler:
python3 -c "
import pefile
pe = pefile.PE('dumped_SCY.exe')
print('Entry point:', hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    print(f'  {imp.dll.decode()}: {len(imp.imports)} funcs')
"

# Load in x64dbg for quick check:
File → Open → dumped_SCY.exe
# Check if it runs to main cleanly
# Check if imports look valid in Symbols tab
```

## Common Packers Reference

| Packer | Detection | Method |
|--------|-----------|--------|
| UPX | `upx -t binary` | ESP trick or POPAD+JMP |
| MPRESS | Section name `MPRESS1` | VirtualAlloc or VirtualProtect |
| .NET Reactor | Native stub + managed | Run to Assembly.Load, dump |
| Themida/WinLicense | Anti-VM, anti-debug heavy | ScyllaHide required, complex |
| VMProtect | Virtualized code paths | Partial: dump unvirtualized code |
| PECompact | Section entropy scan | VirtualAlloc + hardware BP |
| Custom XOR | Manual analysis | Find decrypt loop, BP after |
