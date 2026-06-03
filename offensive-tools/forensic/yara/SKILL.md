---
name: yara
description: "Auth/lab ref: YARA pattern matching; files, binaries, memory images, strings/regex/byte rules, malware/stego/IOC classification."
license: BSD-3-Clause
compatibility: "Windows/Linux/macOS CLI + yara-python."
metadata:
  author: AeonDave
  version: "2.0"
---

# YARA

Rule-based file/binary pattern matcher — strings, bytes, regex, structure. Scan files, directories, memory dumps.

## Installation

```bash
# Linux
sudo apt install yara

# macOS
brew install yara

# Python module
pip install yara-python

# Verify
yara --version
```

---

## Basic Usage

```bash
# Scan single file
yara rules.yar suspicious.exe

# Verbose (show matching strings)
yara -s rules.yar suspicious.exe

# Scan directory recursively
yara -r rules.yar /path/to/dir/

# Multiple rule files
yara rule1.yar rule2.yar target.bin

# Scan memory dump
yara -r rules.yar memdump.raw

# Scan process memory (Linux, root required)
yara rules.yar <PID>

# Count matches only
yara -c rules.yar target.bin

# Invert match (files NOT matching rule)
yara -n rules.yar target.bin

# Timeout per file (seconds)
yara --timeout=60 rules.yar large_file.bin

# Print tags only
yara -t rules.yar target.bin
```

---

## Rule Syntax

### Basic structure

```yara
rule RuleName : tag1 tag2
{
    meta:
        author = "Dave"
        description = "Detects X"
        date = "2024-01-01"

    strings:
        $s1 = "plain text string"
        $s2 = "case insensitive" nocase
        $s3 = "wide string" wide               // UTF-16LE (Windows strings)
        $s4 = "both encodings" wide ascii
        $s5 = /regex[0-9]{4}/                  // regex
        $s6 = /flag\{[a-zA-Z0-9_]+\}/          // flag pattern regex
        $b1 = { 4D 5A 90 00 }                  // hex bytes (PE MZ header)
        $b2 = { 6A 40 68 00 30 00 00 }         // hex shellcode pattern
        $b3 = { FF D? }                         // ? = wildcard nibble
        $b4 = { 6A [2-4] 68 }                  // [n] = n bytes jump, [n-m] = range

    condition:
        any of them
}
```

### Conditions

```yara
condition:
    $s1                         // string present
    not $s1                     // string absent
    #s1 > 3                     // string count
    @s1 < 100                   // string offset < 100 bytes from start
    $s1 at 0                    // string at exact offset
    $s1 in (0..512)             // string in byte range
    all of them                 // all strings match
    any of them                 // at least one matches
    2 of ($s*)                  // at least 2 of s* group
    all of ($b*)                // all b* hex patterns
    filesize < 1MB              // file size constraint
    filesize > 100KB and $s1
    uint16(0) == 0x5A4D         // MZ header check (PE file)
    uint32(0) == 0x464C457F     // ELF magic
```

---

## Common Rule Patterns

### Find flag in binary

```yara
rule FindFlag
{
    strings:
        $f1 = /flag\{[a-zA-Z0-9_!@#$%^&*\-]+\}/ nocase
        $f2 = /HTB\{[a-zA-Z0-9_]+\}/ nocase
        $f3 = /PICOCTF\{[a-zA-Z0-9_]+\}/ nocase
        $f4 = "flag" nocase

    condition:
        any of them
}
```

### Detect PE file

```yara
rule IsPE
{
    condition:
        uint16(0) == 0x5A4D and
        uint32(uint32(0x3C)) == 0x00004550
}
```

### Find base64-encoded data

```yara
rule Base64Blob
{
    strings:
        $b64 = /[A-Za-z0-9+\/]{40,}={0,2}/

    condition:
        $b64
}
```

### Detect shellcode patterns (common sequences)

```yara
rule ShellcodeIndicator
{
    strings:
        $nop_sled = { 90 90 90 90 90 90 90 90 }
        $push_esp  = { 54 5C }
        $call_eax  = { FF D0 }
        $xor_eax   = { 33 C0 }

    condition:
        2 of them
}
```

### Find XOR-encoded string

```yara
rule XORHint
{
    strings:
        // Common XOR key indicator: repetitive byte patterns
        $xor1 = { EB ?? [1-16] }
        $xor2 = /\x00.{0,8}\x00.{0,8}\x00/

    condition:
        any of them and filesize < 500KB
}
```

---

## YARA Modules

Modules extend matching to structured formats:

```yara
import "pe"
import "elf"
import "math"
import "hash"
import "time"

// PE module examples
rule PEAnalysis
{
    condition:
        pe.is_pe and
        pe.number_of_sections > 6 and
        pe.entry_point < pe.sections[0].virtual_address
}

// Check section entropy (packed/encrypted = high entropy)
rule PackedBinary
{
    condition:
        math.entropy(0, filesize) > 7.5
}

// Hash-based matching
rule SpecificMD5
{
    condition:
        hash.md5(0, filesize) == "d41d8cd98f00b204e9800998ecf8427e"
}

// ELF
rule ELFExecutable
{
    condition:
        elf.type == elf.ET_EXEC
}
```

---

## Scanning Memory Dumps with YARA

```bash
# Scan raw memory dump for strings
yara -s rules.yar memdump.raw

# Find flag pattern in memory dump
yara -s flag_rule.yar memory.dmp

# Scan with Volatility3 (built-in yara scanning)
python3 vol.py -f memory.raw windows.vadyarascan --yara-rules "flag{" --pid 1234
python3 vol.py -f memory.raw windows.dumpfiles --pid 1234   # then yara on dumps

# Linux: scan all processes
python3 vol.py -f memory.raw linux.proc_maps --pid 1234 --dump
yara -r rules.yar pid.1234/
```

---

## Community Rule Sources

```bash
# Clone YARA rules from major sources
git clone https://github.com/Yara-Rules/rules yara-rules-repo/
git clone https://github.com/Neo23x0/signature-base signature-base/
git clone https://github.com/mandiant/red_team_tool_countermeasures mandiant-rules/

# Use downloaded rules
yara -r yara-rules-repo/malware/*.yar target/

# Scan with multiple rule sets
yara -r yara-rules-repo/malware/*.yar \
        signature-base/yara/*.yar \
        target_file.exe
```

---

## Python API (yara-python)

```python
import yara

# Compile rule inline
rule = yara.compile(source='''
rule FindFlag {
    strings:
        $f = /flag\{[a-zA-Z0-9_]+\}/
    condition:
        $f
}
''')

# Scan file
matches = rule.match('/path/to/file.bin')
for m in matches:
    print(m.rule)
    for s in m.strings:
        print(f"  Offset {s.instances[0].offset}: {s.instances[0].matched_data}")

# Scan bytes in memory
data = open('file.bin', 'rb').read()
matches = rule.match(data=data)

# Scan process memory (Linux, root)
matches = rule.match(pid=1234)
```

---

## Common Investigation Workflows

### Quick scan: find flag in any file

```bash
# Create quick rule
cat > flag_hunt.yar << 'EOF'
rule FlagHunt {
    strings:
        $f1 = /[Ff][Ll][Aa][Gg]\{[^\}]+\}/
        $f2 = /HTB\{[^\}]+\}/
        $f3 = /picoCTF\{[^\}]+\}/
    condition:
        any of them
}
EOF

# Scan everything
yara -rs flag_hunt.yar /path/to/challenge/
```

### Scan extracted files from Autopsy/TSK

```bash
# Extract all files
tsk_recover -o 2048 disk.img recovered/

# Scan with known-bad rules
yara -r yara-rules-repo/malware/*.yar recovered/
```

### Scan Volatility dump output

```bash
# After dumping process with volatility
python3 vol.py -f memory.raw windows.procdump --pid 1234
yara -s rules.yar pid.1234.0x400000.dmp
```

### Find crypto keys/encoded data

```bash
cat > crypto_hunt.yar << 'EOF'
rule CryptoIndicators {
    strings:
        $pem = "-----BEGIN"
        $b64 = /[A-Za-z0-9+\/]{60,}={0,2}/
        $hex = /[0-9a-fA-F]{64}/    // SHA256-length hex
        $key = "AES" nocase
        $rsa = "RSA" nocase

    condition:
        2 of them
}
EOF

yara -s crypto_hunt.yar suspicious.bin
```

---

## Tips

- Use `-s` always — without it you only see rule name match, not which string matched or where
- Test rules against known-benign files before deploying to avoid false positives
- Wide strings (`wide`) catch UTF-16LE strings common in Windows executables
- Hex wildcards `??` and `[n-m]` handle obfuscated/variable shellcode sequences
- `math.entropy() > 7.5` reliably detects packed/encrypted sections
- Community rules (Neo23x0/signature-base) have strong malware family coverage

## Resources

| File | When to load |
|------|--------------|
| `references/` | Module reference, rule optimization, integration with Volatility |
