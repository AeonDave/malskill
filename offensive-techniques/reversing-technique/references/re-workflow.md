# Reverse Engineering Workflow

## Phase 1: Target Identification & Information Gathering

### 1.1 Define Clear Objective
- What specific information do you need? (e.g., "Find authentication bypass", "Extract C2 server address", "Understand file format")
- Avoid "just looking around" - focus drives efficiency
- Write down your objective before starting

### 1.2 Basic File Triage
- **File type**: `file` command, `detect-it-easy` for packer detection
- **Size analysis**: Unusually small/large may indicate packing
- **Entropy check**: High entropy (>7.0) suggests encryption/compression
- **Metadata**: Timestamps, version info, digital signatures
- **Strings extraction**: `strings` or `rabin2 -z` for ASCII/Unicode

### 1.3 Import/Export Analysis
- **Windows**: Dependencies (DLLs), exported functions
- **Linux**: Shared library dependencies, symbols
- **Suspicious imports**: Network APIs, file system, crypto, process manipulation
- **Missing imports**: May indicate custom syscalls or direct invocation

### 1.4 Packer Detection
- **Signatures**: UPX, ASPack, Themida, VMProtect, custom
- **Indicators**: 
  - Few imports but complex behavior
  - High entropy sections
  - Executable section with weird name (.UPX0, .packed)
  - Entry point in suspicious section
- **Action**: Note packer type for later unpacking strategy

## Phase 2: Static Analysis (Objective-Driven)

### Verify OS/runtime behavior

Load this workflow when an old tutorial, undocumented structure, or runtime claim must be checked on the actual target. State one falsifiable question, such as which image runs first or whether an initializer precedes the user entry function.

1. **Bind the environment.** Record OS/kernel build and revision, architecture, compiler/linker and flags, runtime/package revision, and the actual loaded module paths, versions, and hashes. A Windows product-name string or OS build is not a DLL version; a WSL kernel version is not a glibc version. Note discrepancies rather than choosing the most convenient label.
2. **Separate contracts from implementations.** Start with the applicable ABI/API/specification. Retrieve the vendor/distro source revision and patches for the observed implementation. Windows public symbols expose selected names/types; they do not supply all source or private runtime state. ReactOS/Wine, blog diagrams, and upstream `master` are hypotheses to compare, not substitutes for the target build.
3. **Match symbols to images.** Linux: inspect `readelf -n` build IDs and `.gnu_debuglink`, then obtain corresponding distro debug/source packages or debuginfod results. GDB uses build IDs or debug-link CRCs to select separate debug files. Windows: retain the PE CodeView PDB identity (modern RSDS GUID plus age) and matching PDB; use the symbol server/debugger's matching checks, not filename or product version alone. [GDB debug-file matching](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Separate-Debug-Files.html), [Microsoft symbol matching](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/symbols).
4. **Recover the path statically.** Locate the relevant header entry/RVA or function, then follow disassembly and compare it with matching source. Record module-relative addresses and account for thunks, inlining, optimized-out arguments, and absent private symbols. Missing symbols are not evidence that a stage does not exist; pseudocode is a hypothesis until checked against instructions/data.
5. **Test the smallest observable claim.** Build a harmless local probe or use the authorized target's isolated test environment. Set breakpoints before the disputed boundary, capture the loaded base, instructions, arguments, call stack, and marker order. Compare a normal run with the debugger run; vary one relevant factor such as architecture or CRT linkage. Log order alone cannot identify the responsible loader/runtime routine.
6. **Persist a scoped rule.** Label it documented, observed, inferred, or unresolved. Save the source locator/revision, image hash/build ID/PDB identity, tool versions, commands/flags, observed result, and untested branches. Re-check after changes to the module, toolchain, architecture, linkage, or vendor patches; edit the canonical fact and its routing, not duplicate diagrams across skills.

For Windows identity gathering in PowerShell:

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Version, BuildNumber, OSArchitecture
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' |
    Select-Object CurrentBuild, UBR, DisplayVersion, BuildLabEx
(Get-Item -LiteralPath $modulePath).VersionInfo |
    Select-Object FileVersion, ProductVersion
Get-FileHash -Algorithm SHA256 -LiteralPath $modulePath
```

Set `$modulePath` to the image actually loaded by the target. For WinDbg, `.symfix`, `.reload /f MODULE`, `lmvm MODULE`, and `!lmi MODULE` show module/symbol evidence; replace `MODULE` with its debugger module name. If matching fails, use `!sym noisy` and inspect the selected file before trusting names/types. Do not force-load mismatched symbols to turn an unresolved claim into a result. [Microsoft symbol workflow](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/symbols).

For startup-specific boundaries and executable commands, load `linux-internals-dev` → `references/elf-format.md` or `windows-internals-dev` → `references/pe-format.md`.

### 2.1 Entry Point Analysis
- Distinguish interpreter/loader entry, executable ELF `e_entry` or PE `AddressOfEntryPoint`, and user `main`/`WinMain`/`DllMain`.
- Follow initialization through the actual runtime; a breakpoint at `main` can miss earlier application logic.
- Note early anti-analysis checks (often in startup)

### 2.2 Function Identification
- **From strings**: Find where interesting strings are used
- **From imports**: Trace API usage back to callers
- **From exports**: Analyze exported functions (if DLL/library)
- **From symbols**: Use debug symbols if available

### 2.3 Control Flow Analysis
- Identify loops, conditionals, switch statements
- Look for security checks (comparisons followed by jumps)
- Map out major code paths based on objective
- Note error handling patterns

### 2.4 Data Structure Recognition
- Identify structs via pointer arithmetic and field access
- Look for arrays, linked lists, trees
- Note magic values, constants, offsets
- Cross-reference data usage across functions

### 2.5 Algorithm Understanding
- Focus on objective-relevant code only
- Trace data flow from input to output
- Identify transformations (encryption, compression, encoding)
- Look for key schedules, state updates, round functions

## Phase 3: Dynamic Analysis (Validation & Discovery)

### 3.1 Environment Setup
- Isolated VM with snapshots
- Network simulation (INetSim, fake DNS)
- Monitoring tools (Process Monitor, Wireshark)
- Debugger configured (x64dbg, GDB, WinDbg)

### 3.2 Breakpoint Strategy
- **Entry points**: Validate initialization assumptions
- **String usage**: See when/where strings are decrypted/used
- **API calls of interest**: Monitor parameters and return values
- **Suspicious loops**: Break on iteration counts or exits
- **Memory accesses**: Watch for decryption buffers

### 3.3 Execution Monitoring
- **Process creation**: DLL injection, process hollowing
- **Registry/file changes**: Persistence mechanisms
- **Network traffic**: C2 communication, exfiltration
- **Memory allocations**: Heap spraying, buffer allocations
- **Register states**: Argument passing, return values

### 3.4 Interactive Debugging
- **Step over**: Skip known library code
- **Step into**: Explore interesting functions
- **Modify registers**: Change flow, test conditions
- **Patch memory**: NOP checks, change values
- **Call stack**: Understand callers and context

### 3.5 Memory Analysis
- **String discovery**: Watch for decrypted strings in memory
- **Key material**: Look for AES keys, XOR buffers
- **Structures**: Identify live data structures
- **Heap analysis**: Find allocated buffers and their contents
- **Stack inspection**: Local variables, return addresses

### 3.6 Core Dump Analysis

Use core dumps when the binary decrypts secrets in memory temporarily, or when stopping for interactive debugging changes timing-sensitive behavior.

**Trigger a dump at peak decryption:**
```bash
# Option A: dump while process is alive (Linux)
gcore <pid>              # Write core file without killing the process
# Or: in GDB after hitting a breakpoint at the decryption endpoint
(gdb) generate-core-file /tmp/dump_decrypted.core

# Option B: configure crash dump (for binaries that exit immediately)
ulimit -c unlimited
GOTRACEBACK=crash ./binary   # Forces crash dump on abnormal exit (Go)
# Or for generic binaries:
echo '/tmp/core_%e_%p' | sudo tee /proc/sys/kernel/core_pattern
./binary; ls /tmp/core_*

# Option C: force crash at a controlled point
kill -SIGABRT <pid>         # Sends SIGABRT → dump if ulimit allows
```

**Load and analyze the dump:**
```bash
# GDB
gdb ./binary /tmp/dump_decrypted.core
(gdb) info proc mappings          # All memory regions at crash time
(gdb) x/100s 0x<suspect_addr>    # Read strings from a suspect region
(gdb) dump binary memory /tmp/region.bin 0x<start> 0x<end>

# radare2
r2 -F elf ./binary /tmp/dump_decrypted.core
[0x0]> iS                         # Sections reconstructed from core
[0x0]> /iz                        # Search for strings in all segments

# strings (quick pass)
strings /tmp/dump_decrypted.core | grep -iE "key|pass|secret|token|credential"
```

**Extract a specific mapped region:**
```bash
# From /proc/<pid>/maps while alive:
cat /proc/<pid>/maps
# Find the region of interest (e.g., heap or anonymous mapping)
dd if=/proc/<pid>/mem bs=1 skip=<decimal_start> count=<size> of=/tmp/region.bin 2>/dev/null
```

**Common use case — secret overwritten after validation:**
1. Set a breakpoint immediately after the decryption function returns
2. At the breakpoint: `generate-core-file` or `dump binary memory`
3. Resume → binary will overwrite/free the secret
4. Analyze the dump offline at leisure
- Use comments to explain non-obvious operations
- Group related code into logical functions

### 4.2 Data Modeling
- Reconstruct structs and unions
- Document field purposes and values
- Note memory layout and padding
- Track how data flows through structures

### 4.3 Flow Charting
- Create control flow diagrams for complex logic
- Show decision points and branches
- Map data flow between components
- Highlight objective-related paths

### 4.4 Documentation
- Update findings continuously
- Link static observations to dynamic behavior
- Note uncertainties and assumptions
- Create summary tied to original objective

## Phase 5: Verification & Iteration

### 5.1 Hypothesis Testing
- Modify binary to test assumptions (NOP, patch)
- Observe behavior changes in debugger
- Validate string decryption results
- Confirm API call parameters/returns

### 5.2 Gap Analysis
- Identify missing pieces in understanding
- Return to static/dynamic analysis as needed
- Use new information to refine hypotheses
- Iterate until objective is satisfied

### 5.3 Alternative Approaches
- If stuck, try different entry points
- Consider alternative interpretations
- Look for obfuscation that may hide true functionality
- Consider multiple layers (packer -> protector -> actual code)

### 5.4 Evidence-Bound Conclusions
- Keep one controlled input per hypothesis whenever possible.
- Distinguish clearly between **candidate**, **likely**, and **validated** findings.
- Record reachability preconditions (format, auth state, config, timing, environment).
- Record mitigation interactions separately from the primitive itself.
- State unknowns explicitly instead of silently filling gaps with intuition.

**Minimal handoff artifact for deeper work:**
1. priority target function(s)
2. attacker-controlled inputs and constraints
3. proof required to validate the hypothesis
4. runtime checkpoints (registers, memory, API calls, or side effects)

## Tools Context (Reference Only)
- Disassemblers: Ghidra, IDA Pro, Binary Ninja, radare2, objdump
- Debuggers: x64dbg, WinDbg, GDB, OllyDbg, lldb
- Packet capture: Wireshark, tcpdump
- System monitoring: Process Monitor, ProcMon, API Monitor
- Unpacking: UPX, custom scripts, manual in debugger
- Strings: strings, rabin2, FLOSS
- Metadata: PEiD, Detect It Easy, pedump, readelf

Remember: Tools assist the process but don't replace methodology. Your objective determines depth and focus.
---

## Phase 6: Ghidra-Specific Analysis Tips

### 6.1 Navigation Shortcuts

| Key | Action |
|---|---|
| `G` | Go to address |
| `X` | Show all cross-references to current location |
| `Ctrl+E` | Open Decompiler window for current function |
| `S` | Search memory (bytes, hex, string, regex) |
| `Ctrl+Shift+F` | Search program text (listing tokens) |
| Menu: Search → For Strings... | Locate ASCII/Unicode strings program-wide |
| `L` | Rename label / function |
| `;` | Add comment |
| `T` | Retype variable |
| `Ctrl+L` | Retype return value |

**Start navigation:** entry point -> Symbol Tree -> imported functions -> X on suspicious APIs. Sort Functions window by size -- large functions usually contain core logic.

### 6.2 Encryption Pattern Identification

| Algorithm | Static indicators | Dynamic indicators |
|---|---|---|
| XOR | Loop with XOR byte op; single-byte or rolling key | Plaintext visible in memory after loop |
| RC4 | Two nested loops; 256-byte S-box init (KSA + PRGA) | S-box visible in heap during init |
| AES | S-box `63 7c 77 7b...` in .rodata; CryptEncrypt/BCryptEncrypt calls | Key schedule in allocated buffer |
| ChaCha20 | `expand 32-byte k` constant in .rodata | 64-byte state block in memory |
| Base64 | Lookup table `A-Za-z0-9+/=` | Decoded data in string form after call |
| Custom | Arithmetic-only loops (ADD/SUB/ROL/ROR + XOR); no standard constants | Trace with GDB / x64dbg |

**FindCrypt plugin**: `Analyze -> One Shot -> Find Crypto Constants` -- auto-highlights AES, SHA, CRC, MD5, RSA constants.

### 6.3 C2 Protocol Reversing (5-Step Flow)

1. Locate InternetOpenA / WinHttpOpen in Symbol Tree -> X -> wrapper function
2. Trace: config blob -> decrypt -> string concat -> URL (rename vars as you go)
3. Identify: HTTP method, custom headers, POST body format (JSON / binary / Base64)
4. Find response parser: HttpQueryInfo / WinHttpReadData -> JSON deserializer or binary switch/case
5. Map all dispatcher cases: download, execute, exfiltrate, update, uninstall, sleep

### 6.4 YARA Generation from Ghidra

Highlight bytes in Listing -> right-click -> **Copy Special -> Byte String (No Spaces)** -> paste into YARA strings.

### 6.5 Headless Batch Analysis

Run Ghidra without GUI for batch triage:
`/opt/ghidra/support/analyzeHeadless /tmp/proj Proj -import suspect.exe -postScript Script.py -deleteProject`
