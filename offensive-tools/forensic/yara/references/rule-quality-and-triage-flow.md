# YARA — Deep Reference

## PE Module Field Reference

```yara
import "pe"

rule PEDetails {
    condition:
        pe.is_pe and
        pe.machine == pe.MACHINE_AMD64 and          // x64
        pe.subsystem == pe.SUBSYSTEM_WINDOWS_GUI and
        pe.number_of_sections > 4 and
        pe.number_of_imports > 50 and

        // Section checks
        pe.sections[0].name == ".text" and
        for any i in (0..pe.number_of_sections - 1): (
            pe.sections[i].characteristics & pe.SECTION_MEM_EXECUTE != 0 and
            pe.sections[i].characteristics & pe.SECTION_MEM_WRITE != 0
        ) and   // RWX section = packer/injector

        // Import checks
        pe.imports("kernel32.dll", "VirtualAlloc") and
        pe.imports("kernel32.dll", "WriteProcessMemory") and
        pe.imports("kernel32.dll", "CreateRemoteThread")
}
```

**Useful pe.* fields:**

| Field | Description |
|-------|-------------|
| `pe.is_pe` | True if valid PE |
| `pe.machine` | MACHINE_I386, MACHINE_AMD64, MACHINE_ARM64 |
| `pe.subsystem` | SUBSYSTEM_WINDOWS_GUI, SUBSYSTEM_WINDOWS_CUI, etc. |
| `pe.timestamp` | Compilation timestamp (Unix) |
| `pe.number_of_sections` | Section count |
| `pe.number_of_imports` | Import count |
| `pe.entry_point` | EP virtual address |
| `pe.sections[i].name` | Section name |
| `pe.sections[i].virtual_size` | Size in memory |
| `pe.sections[i].raw_size` | Size on disk |
| `pe.sections[i].characteristics` | SECTION_MEM_EXECUTE, SECTION_MEM_WRITE, etc. |
| `pe.imports("dll", "func")` | Check specific import |
| `pe.exports("func")` | Check specific export |
| `pe.version_info["ProductName"]` | Version info string |
| `pe.is_dll` | True if DLL |
| `pe.overlay.offset` | Overlay data start (appended data) |
| `pe.resources[i].type` | Resource type |

---

## ELF Module Field Reference

```yara
import "elf"

rule ELFAnalysis {
    condition:
        elf.type == elf.ET_EXEC and              // executable (not ET_DYN/ET_REL)
        elf.machine == elf.EM_386 and            // x86
        elf.number_of_sections > 5
}
```

| Field | Values |
|-------|--------|
| `elf.type` | `ET_NONE`, `ET_REL`, `ET_EXEC`, `ET_DYN` |
| `elf.machine` | `EM_386`, `EM_X86_64`, `EM_ARM`, `EM_AARCH64` |
| `elf.number_of_sections` | count |
| `elf.sections[i].name` | section name |
| `elf.sections[i].flags` | `SHF_ALLOC`, `SHF_EXECINSTR`, `SHF_WRITE` |

---

## math Module: Entropy Detection

```yara
import "math"

// Packed/encrypted section has entropy > 7.0
rule HighEntropy {
    condition:
        math.entropy(0, filesize) > 7.2
}

// Check specific range (e.g., first 512 bytes)
rule HighEntropyHeader {
    condition:
        math.entropy(0, 512) > 6.5
}

// Combined: PE with high-entropy section
rule PackedPE {
    condition:
        pe.is_pe and
        for any i in (0..pe.number_of_sections-1): (
            math.entropy(pe.sections[i].raw_offset, pe.sections[i].raw_size) > 7.5
        )
}
```

Entropy reference:
- 0-3: plain text / structured data
- 3-6: compressed or semi-random
- 6-7: compressed code (packed executables)
- 7-8: encrypted or high-entropy (packed, shellcode)

---

## hash Module

```yara
import "hash"

// Match by exact MD5 hash
rule SpecificSample {
    condition:
        hash.md5(0, filesize) == "d41d8cd98f00b204e9800998ecf8427e"
}

// Hash of specific section
rule SectionHash {
    condition:
        hash.sha256(pe.sections[0].raw_offset, pe.sections[0].raw_size) == "abc123..."
}
```

---

## Condition Operators Reference

```yara
// String at specific offset
$s at 0                           // at beginning
$s at (filesize - 10)             // near end
$s in (0..1024)                   // within first 1KB

// Count
#s1 > 5                           // string appears > 5 times
#s1 in (0..512) > 2              // appears 2+ times in first 512 bytes

// Offset array
@s1[0] < 100                     // first occurrence < offset 100
@s1[1] > 500                     // second occurrence > offset 500

// Any/all syntax
any of ($s*)                     // any string matching s prefix
all of ($b*)                     // all b* strings
2 of ($s1, $s2, $s3)            // exactly 2 of listed
any of them                      // any string in rule

// File size
filesize < 1MB
filesize > 100KB
filesize == 45056

// For loops
for any i in (0..pe.number_of_sections - 1): (
    pe.sections[i].name == ".packed"
)
for all i in (0..pe.number_of_imports - 1): (
    pe.imports[i].library_name == "KERNEL32.DLL"
)
```

---

## Writing Rules for Challenge Artifacts

### Find encoded flag (base64, hex, XOR)

```yara
rule EncodedData {
    strings:
        $b64 = /[A-Za-z0-9+\/]{20,}={0,2}/
        $hex = /[0-9a-fA-F]{32,}/
        $xored_flag = { 66 6C 61 67 }    // "flag" XOR 0x00 (plaintext as hex)

    condition:
        any of them
}
```

### Detect in-memory shellcode characteristics

```yara
rule ShellcodeSignature {
    strings:
        $nop = { 90 90 90 90 90 90 }
        $call_pop = { E8 00 00 00 00 5? }    // call+pop (PIC shellcode)
        $find_kernel32 = { 64 A1 30 00 00 00 }  // FS:[0x30] = PEB
        $xor_loop = { 30 [1-4] 4? }            // XOR byte, increment

    condition:
        2 of them
}
```

### Detect common RAT capabilities

```yara
rule RATIndicators {
    strings:
        $screenshot = "BitBlt" wide ascii nocase
        $keylog = "SetWindowsHookEx" wide ascii nocase
        $cmd = "cmd.exe" wide ascii nocase
        $powershell = "powershell" wide ascii nocase
        $reg_run = "\\CurrentVersion\\Run" wide ascii nocase
        $self_delete = "del /f /q" wide ascii nocase

    condition:
        3 of them
}
```

---

## Performance Optimization

- Put file-size constraints first — they short-circuit immediately:
  ```yara
  condition: filesize < 2MB and pe.is_pe and $s1
  ```
- Avoid `all of them` if strings are many — use specific counts
- Use `nocase` only when necessary — doubles matching overhead
- Hex patterns `{ ?? }` with many wildcards are slow on large files
- `math.entropy()` is expensive — put as last condition after cheaper checks
- For bulk scanning, compile rules once: `yara --compiled-rules rules.yrc`
  ```bash
  yarac rules.yar rules.yrc
  yara --compiled-rules rules.yrc target_dir/
  ```

---

## Volatility3 + YARA Integration

```bash
# Scan process virtual memory with YARA rule
python3 vol.py -f memory.raw windows.vadyarascan --yara-rules 'rule X { strings: $f = "flag{" condition: $f }' --pid 1234

# Scan all processes
python3 vol.py -f memory.raw windows.vadyarascan --yara-rules 'rule X { strings: $f = /flag\{[^\}]+\}/ condition: $f }'

# Scan from rule file
python3 vol.py -f memory.raw windows.vadyarascan --yara-file rules.yar

# Kernel space scan
python3 vol.py -f memory.raw windows.driverirp --yara-rules "rule X { ... }"
```
