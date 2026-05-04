# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-reverse`
- Target skill: `reverse-ctf`
- Preserved files: 19

## Imported files and topic cues

### `source-skill.md`

- CTF Reverse Engineering
- Prerequisites
- For Python 3.9+ bytecode: build pycdc from source
- Additional Resources
- When to Pivot
- Problem-Solving Workflow
- Quick Wins (Try First!)
- Plaintext flag extraction
- Dynamic analysis - often captures flag directly
- Hex dump search
- Run with test inputs
- Initial Analysis
- Memory Dumping Strategy
- Decoy Flag Detection
- GDB PIE Debugging
- Comparison Direction (Critical!)
- Common Encryption Patterns
- Quick Tool Reference
- Radare2
- Ghidra (headless)
- IDA
- Deep-Dive Notes

### `anti-analysis-ctf.md`

- CTF Reverse - Anti-Analysis CTF Writeups
- Table of Contents
- SIGILL Handler for Execution Mode Switching
- SIGFPE Signal Handler Side-Channel via strace Counting
- Count SIGFPE signals per input character guess
- Character producing the most SIGFPEs is correct
- Repeat for each position, extending the known prefix
- Instruction Trace Inversion with Keystone and Unicorn
- IDAPython: collect non-jump instructions in the obfuscated routine
- Invert: reverse order, swap add/sub and rol/ror
- Assemble inverted instructions with Keystone, emulate with Unicorn
- Set initial register state to the observed output value
- Call-less Function Chaining via Stack Frame Manipulation
- Reversed processing chain (each function applied via leave/ret):
- Apply in reverse order, then reverse the character sequence
- Parent-Patched Child Binary Dump via strace process_vm_writev
- Record every process_vm_writev the parent performs, including full iov contents.
- Each entry looks like:
- process_vm_writev(child_pid, [{iov_base="\x48\x89\xe5...", iov_len=12}], 1,
- [{iov_base=0x400c80, iov_len=12}], 1, 0) = 12
- ConfuserEx Dynamic Module Dump via Constructor Breakpoint

### `anti-analysis.md`

- CTF Reverse - Anti-Analysis Techniques & Bypasses
- Table of Contents
- Linux Anti-Debug (Advanced)
- ptrace-Based
- 1. LD_PRELOAD (see patterns.md for full hook)
- 2. Patch with pwntools
- 3. GDB: catch the syscall
- When it stops at ptrace:
- 4. Kernel config (requires root)
- /proc Filesystem Checks
- 1. LD_PRELOAD fopen/fread to fake /proc contents
- 2. Mount namespace isolation
- 3. GDB: set breakpoint at fopen, change filename argument
- Timing-Based Detection
- 1. Frida hook (see tools-dynamic.md for clock_gettime hook)
- 2. GDB: skip rdtsc by patching with constant
- 3. Pin tool to fix TSC reads
- 4. faketime library
- Signal-Based Anti-Debug
- GDB: pass signals to program instead of handling them
- For alarm-based: patch alarm() to return immediately
- Syscall-Level Evasion
- GDB: catch syscall
- Windows Anti-Debug (Advanced)

### `field-notes.md`

- Reverse Engineering Field Notes
- Table of Contents
- Binary Types
- Python.pyc
- WASM
- WASM patching (game challenges):
- Edit WAT: flip comparisons, change constants
- Android APK
- Flutter APK (Dart AOT)
- .NET
- Packed (UPX)
- Tauri Packed Desktop Apps
- Anti-Debugging Bypass
- Specialized Patterns
- S-Box / Keystream Patterns
- Custom VM Analysis
- Python Bytecode Reversing
- Signal-Based Binary Exploration
- Malware Anti-Analysis Bypass via Patching
- Expected Values Tables
- x86-64 Gotchas
- Iterative Solver Pattern
- Unicorn Emulation (Complex State)
- Multi-Stage Shellcode Loaders

### `languages-compiled.md`

- CTF Reverse - Compiled Language Reversing (Go, Rust)
- Table of Contents
- Go Binary Reversing
- Recognition
- Detect Go binary
- Go version embedded in binary
- Symbol Recovery
- GoReSym - recovers function names, types, interfaces from Go binaries
- https://github.com/mandiant/GoReSym
- Parse output
- Install: Ghidra → Window → Script Manager → search "golang"
- Or use: https://github.com/getCUJO/ThreatFox/tree/main/ghidra-golang
- Recovers function names, string references, interface tables
- https://github.com/goretk/redress
- Go Memory Layout
- String: {pointer, length} (16 bytes on 64-bit)
- NOT null-terminated! Length field is critical.
- Slice: {pointer, length, capacity} (24 bytes on 64-bit)
- Interface: {type_descriptor, data_pointer} (16 bytes)
- Map: pointer to runtime.hmap struct
- Channel: pointer to runtime.hchan struct
- Goroutine and Concurrency Analysis
- Identify goroutine spawns in disassembly
- newproc1 is the internal goroutine creation function

### `languages-platforms.md`

- CTF Reverse - Platform & Framework-Specific Techniques
- Table of Contents
- Roblox Place File Analysis
- Extract placeId and universeId from game page HTML
- Query each version (requires.ROBLOSECURITY cookie):
- Download location URL → place_v1.rbxlbin
- Godot Game Asset Extraction
- Rust serde_json Schema Recovery
- Android JNI RegisterNatives Obfuscation
- x86_64 gives best Ghidra decompilation (most similar to desktop code)
- Extract from APK:
- Android DEX Runtime Bytecode Patching via /proc/self/maps
- Reconstruct the patched DEX offline:
- 1. Extract the embedded DEX from the APK
- 2. Find the XOR key and patch offsets in the native.so (IDA/Ghidra)
- 3. Apply the same patches to the static DEX
- Patch 144 bytes starting at offset found in.so
- 4. Recompute DEX checksum and SHA-1 hash
- 5. Decompile with jadx or baksmali
- Android Native.so Loading Bypass in New Project
- Frida Firebase Cloud Functions Bypass
- Verilog/Hardware Reverse Engineering
- Map each action to its cycle count (determined from Verilog state machines)
- COINS_HISTORY is a shift register updated each cycle

### `languages.md`

- CTF Reverse - Language-Specific Techniques
- Table of Contents
- Python Bytecode Reversing (dis.dis output)
- Common Pattern: XOR Validation with Split Indices
- Given: p1, p2 (expected values), key1, key2 (XOR keys)
- Bytecode Analysis Tips
- Python Opcode Remapping
- Identification
- Recovery
- Pyarmor 8/9 Static Unpack (1shot)
- Specify runtime explicitly
- Write outputs to another directory
- DOS Stub Analysis
- Unity IL2CPP Games
- HarmonyOS HAP/ABC Reverse (abc-decompiler)
- Basic decompile to directory
- Decompile.abc (recommended for this scenario)
- Brainfuck/Esolangs
- Brainfuck Character-by-Character Static Analysis
- Split on comma (input read) — each segment handles one character
- Brainfuck Side-Channel via Read Count Oracle
- Recover flag character by character
- Brainfuck Comparison Idiom Detection
- Expected bytes from comparisons reveal the flag

### `patterns-ctf-2.md`

- CTF Reverse - Competition-Specific Patterns (Part 2)
- Table of Contents
- Multi-Layer Self-Decrypting Binary
- Embedded ZIP + XOR License Decryption
- EMBEDDED_ZIP at offset 0x2220, 384 bytes
- ENCRYPTED_MESSAGE at offset 0x21e0, 35 bytes
- Find PK\x03\x04 magic in.rodata
- Extract ZIP (size from symbol table or until next symbol)
- Stack String Deobfuscation from.rodata XOR Blob
- Prefix Hash Brute-Force
- CVP/LLL Lattice for Constrained Integer Validation
- M * x = v (mod 2^32)
- Gaussian elimination in Z/(2^32)
- Decision Tree Function Obfuscation
- Extract comparison constants from all tree functions
- Run via: analyzeHeadless project/ tmp -import binary -postScript extract_tree.py
- GF(2^8) Gaussian Elimination for Flag Recovery
- Extract N×N matrix + N-byte augmentation from binary.rodata
- Build augmented matrix: N rows × (N+1) cols
- ROP Chain Obfuscation in Modified Binary
- GDB script to trace ROP gadgets
- Brute-force the sum that produces correct MD5 prefix
- XOR embedded values with MD5 keystream to get flag

### `patterns-ctf-3.md`

- CTF Reverse - Competition-Specific Patterns (Part 3)
- Table of Contents
- Z3 for Single-Line Python Boolean Circuit
- Parse semicolon-separated statements
- Model walrus chains as LShR(ari, shift_amount)
- Evaluate boolean expressions symbolically
- Final assertion: result_var == 0
- Sliding Window Popcount Differential Propagation
- Brute-force the initial 16-bit window (must have popcount = expected[0])
- Morse Code from Keyboard LEDs via ioctl
- Step 1: Bypass ptrace anti-debug
- Patch ptrace call at offset with NOP (0x90)
- Step 2: Run under strace, capture ioctl calls
- Step 3: Decode timing patterns
- Short blink (250ms) = dit (.), long blink (750ms) = dah ()
- Inter-character pause = 3x, inter-word pause = 7x
- Parse strace output to extract Morse
- Map LED on-durations to dots/dashes, group by pauses
- C++ Destructor-Hidden Validation
- In IDA/Ghidra: look for atexit registrations
- Destructor contains actual validation:
- - Regex pattern matching on 4-byte blocks (8 sequential checks)
- - Arithmetic: v2 += -3 * s[i] + 36 + (s[i] ^ 0x2FCFBA)
- - Modular verification of accumulated sum

### `patterns-ctf.md`

- CTF Reverse - Competition-Specific Patterns (Part 1)
- Table of Contents
- Hidden Emulator Opcodes + LD_PRELOAD Key Extraction
- include <openssl/evp.h>
- Spectre-RSB SPN Cipher — Static Parameter Extraction
- Extract from binary data section
- Image XOR Mask Recovery via Smoothness
- Shellcode in Data Section via mmap RWX
- Recursive execve Subtraction
- Byte-at-a-Time Block Cipher Attack
- Mathematical Convergence Bitmap
- Read coordinates and render bitmap
- Windows PE XOR Bitmap Extraction + OCR
- Extract from.rdata section (offsets from reversing)
- Reshape as BGRA image (dimensions from reversing)
- OCR with charset whitelist
- Two-Stage Loader: RC4 Gate + VM Constraints
- Key from binary strings, ciphertext from stored hex
- GBA ROM VM Hash Inversion via Meet-in-the-Middle
- FNV-1a variant with XOR/multiply
- Forward pass: enumerate first 3 characters from seed state
- Backward pass: invert fmix64 and final multiply, enumerate last 3 chars
- Sprague-Grundy Game Theory Binary
- Critical: state[2] updated ONLY by user moves (XOR of pile_idx, amount, new_value)

### `patterns-runtime.md`

- CTF Reverse - Runtime Patching and Oracle Techniques
- Table of Contents
- Malware Anti-Analysis Bypass via Patching
- Multi-Stage Shellcode Loaders
- Final stage loads flag 4 bytes at a time via mov ebx, value
- Extract little-endian 4-byte chunks
- Timing Side-Channel Attack
- Multi-Thread Anti-Debug with Decoy + Signal Handler Mixed Boolean-Arithmetic
- MBA helpers (extracted from assembly)
- S-box (SHA-256 initial hash values repurposed)
- Two interleaved rodata arrays
- INT3 Patch + Coredump Brute-Force Oracle
- Patch byte at transform output point to 0xCC
- Brute-force each position:
- Signal Handler Chain + LD_PRELOAD Oracle
- include <signal.h>
- printf Format String VM Decompilation to Z3
- Normalize numbers and count unique patterns
- Constrain to printable ASCII
- Add constraints from decompiled format string operations
- e.g., flag[3] + flag[7] == 0xAB (mod 256)
- These come from the write sequences: each %hhn accumulates
- character counts and writes the result to a target byte
- ... (add all constraints from decompilation)

### `patterns.md`

- CTF Reverse - Patterns & Techniques
- Table of Contents
- Custom VM Reversing
- Analysis Steps
- Common VM Patterns
- RVA-Based Opcode Dispatching
- State Machine VMs (90K+ states)
- Custom VM Reverse Engineering via Fuzzing and Instruction Set Discovery
- XOR from AND/OR/NOT:  XOR(a, b) = (a OR b) AND NOT(a AND b)
- ADD via full-adder chains using AND/OR/NOT for carry propagation
- Anti-Debugging Techniques
- Common Checks
- Bypass Technique
- In radare2
- LD_PRELOAD Hook
- define _GNU_SOURCE
- include <dlfcn.h>
- include <sys/ptrace.h>
- pwntools Binary Patching
- Nanomites
- Linux (Signal-Based)
- Windows (Debug Events)
- Analysis
- Self-Modifying Code

### `platforms-hardware.md`

- CTF Reverse - Hardware and Advanced Architecture Reversing
- Table of Contents
- HD44780 LCD Controller GPIO Reconstruction
- RISC-V (Advanced)
- Custom Extensions
- Privileged Modes
- RISC-V Debugging
- OpenOCD + GDB for hardware debugging
- GDB for RISC-V
- QEMU with GDB server
- ARM64/AArch64 Reversing and Exploitation
- Install cross-toolchain and emulator
- Run AArch64 binary on x86 host
- Debug with GDB
- With library preloading (for challenges that ship libc)
- PC-relative address loading (equivalent to x86 LEA):
- Function prologue:
- Function epilogue:
- Switch/jump table:
- AArch64 gadgets differ from x86:
- - "pop {x0}; ret" equivalent: LDP x0, x1, [sp], #0x10; RET
- - Prologue gadgets: LDP x29, x30, [sp, #0x20];... RET
- - system() call: x0 = pointer to "/bin/sh", BLR to system
- Common gadget pattern in AArch64 libc:

### `platforms.md`

- CTF Reverse - Platform-Specific Reversing
- Table of Contents
- macOS / iOS Reversing
- Mach-O Binary Format
- File identification
- Universal (fat) binaries — multiple architectures in one file
- Segments and sections
- Key segments: __TEXT (code), __DATA (globals), __LINKEDIT (symbols)
- Key sections: __text (instructions), __cstring (C strings), __objc_methname
- Code Signing & Entitlements
- Check code signature
- Extract entitlements (capability permissions)
- Key entitlements: com.apple.security.app-sandbox, com.apple.security.network.client
- Remove code signature (for patching)
- Re-sign (ad-hoc, for testing)
- Objective-C Runtime RE
- Dump Objective-C class info
- Shows: @interface, @protocol, method signatures with types
- Runtime inspection with lldb
- Method swizzling detection (anti-tamper)
- Look for: method_exchangeImplementations, class_replaceMethod
- objc_msgSend(receiver, selector,...) is THE dispatch mechanism
- RDI = self (receiver), RSI = selector (char* method name)
- In Ghidra/IDA, look for:

### `tools-advanced-2.md`

- Advanced Reverse Engineering Tools (Part 2)
- Table of Contents
- Advanced GDB Techniques
- Python Scripting
- ~/.gdbinit or source from GDB
- Usage in GDB:
- (gdb) source trace_cmp.py
- (gdb) python TraceCompare(0x401234)
- Brute-Force with GDB Script
- Byte-by-byte brute force via GDB Python API
- Conditional Breakpoints
- Break only when register has specific value
- Break on Nth hit
- Log without stopping
- Watchpoints
- Hardware watchpoint — break when memory changes
- Watch a variable by name (needs debug symbols)
- Conditional watchpoint
- Reverse Debugging (rr)
- Record execution
- Replay with reverse execution support
- In rr replay (GDB commands plus):
- Set checkpoint and return to it
- GDB Dashboard / GEF / pwndbg

### `tools-advanced.md`

- CTF Reverse - Advanced Tools & Deobfuscation
- Table of Contents
- VMProtect Analysis
- Recognition
- VMProtect signatures
- PE sections:.vmp0,.vmp1 (VMProtect adds its own sections)
- Large binary with entropy > 7.5 in certain sections
- Approach
- Tools
- CTF Strategy
- Trace VM execution dynamically to extract operations on flag
- Hook VM handler dispatch to log opcode + operands
- Themida / WinLicense Analysis
- Themida Recognition
- Approach for CTF
- x64dbg workflow for Themida:
- Binary Diffing
- BinDiff
- Export from IDA/Ghidra first, then diff
- IDA: File → BinExport → Export as BinExport2
- Ghidra: Use BinExport plugin
- Command line diffing
- Opens in BinDiff GUI — shows matched/unmatched functions
- Diaphora

### `tools-dynamic.md`

- CTF Reverse - Dynamic Analysis Tools
- Table of Contents
- Frida (Dynamic Instrumentation)
- Installation
- Verify
- Basic Function Hooking
- Attach to running process
- Spawn and instrument from start
- One-liner: hook strcmp and dump comparisons
- Anti-Debug Bypass
- Memory Scanning and Patching
- Function Replacement
- Tracing and Stalker
- r2frida (Radare2 + Frida Integration)
- Attach radare2 to process via Frida
- r2frida commands
- Frida for Android/iOS
- Android (requires rooted device or Frida server)
- Hook Android Java methods
- Frida Memoization for Recursive Function Speedup
- Usage
- angr (Symbolic Execution)
- angr Installation
- Basic Path Exploration

### `tools-emulation.md`

- CTF Reverse - Emulation and Side-Channel Tooling
- Table of Contents
- Qiling Framework (Cross-Platform Emulation)
- Qiling Installation
- Download rootfs for target OS:
- Basic Usage
- Linux ELF emulation
- Windows PE emulation (no Windows needed!)
- ARM/MIPS emulation (IoT firmware)
- Anti-Debug Bypass via Emulation
- Hook ptrace syscall — return 0 (success)
- Hook specific address (e.g., anti-VM check)
- Input Fuzzing with Qiling
- Emulate binary with different inputs to find flag
- Triton (Dynamic Symbolic Execution)
- Symbolize input buffer
- Process instructions and collect constraints
- At comparison point, solve for flag
- Intel Pin Instruction-Counting Side Channel
- Intel Pin Instruction Counting with Genetic Algorithm
- Genetic algorithm parameters
- Initialize random population
- Opcode-Only Trace Reconstruction
- LD_PRELOAD time() Freeze for Deterministic Analysis

### `tools.md`

- CTF Reverse - Tools Reference
- Table of Contents
- GDB
- Basic Commands
- PIE Binary Debugging
- One-liner Automation
- Memory Examination
- Radare2
- Basic Session
- r2pipe Automation
- Ghidra
- Headless Analysis
- Emulator for Decryption
- MCP Commands
- Unicorn Emulation
- Basic Setup
- Map code segment
- Map stack
- Run
- Mixed-Mode (64 to 32) Switch
- When a 64-bit stub jumps into 32-bit code via retf/retfq:
- - retf pops 4-byte EIP + 2-byte CS (6 bytes)
- - retfq pops 8-byte RIP + 8-byte CS (16 bytes)
- Copy memory regions, then GPRs

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
