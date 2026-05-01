---
name: capa
description: |
  Mandiant capa: capability detection for executables, shellcode, and sandbox reports. Identifies
  what a binary can do — persistence, credential access, C2, discovery, defense evasion — mapped
  to MITRE ATT&CK and MBC without running the file. Use to triage unknown binaries before RE,
  understand malware behavior for AV/EDR evasion research, classify dropper vs payload vs loader,
  and prioritize which functions to analyze in Ghidra/radare2.
license: Apache-2.0
compatibility: "Windows/Linux/macOS; standalone binary or Python. pip install capa. github.com/mandiant/capa"
metadata:
  author: AeonDave
  version: "2.0"
---

# capa

Static capability detection for binaries — maps code behavior to ATT&CK/MBC without execution.

## Installation

```bash
# Standalone binary (recommended — no Python deps)
# Download from: https://github.com/mandiant/capa/releases
# Linux
wget https://github.com/mandiant/capa/releases/latest/download/capa-v7.x.x-linux.zip
unzip capa-*.zip && chmod +x capa

# Windows: download capa.exe from releases

# Python package
pip install capa

# Verify
capa --version
```

---

## Basic Usage

```bash
# Static analysis (default — fastest)
capa suspicious.exe

# Verbose: show matched rules and evidence locations
capa -v suspicious.exe

# Very verbose: show all matched bytes/addresses
capa -vv suspicious.exe

# Analyze shellcode (raw bytes, not PE)
capa --format sc32 shellcode_32bit.bin
capa --format sc64 shellcode_64bit.bin

# Analyze ELF
capa suspicious.elf

# Analyze .NET assemblies
capa dotnet_malware.exe

# JSON output (machine-readable, parse with jq)
capa -j suspicious.exe > capa_result.json
capa -j suspicious.exe | jq '.

# Dynamic analysis report (CAPE/sandbox JSON)
capa report.json

# Disable ASLR/PE analysis for raw shellcode
capa --format sc32 payload.bin
```

---

## Output Interpretation

### Standard output structure

```
+------------------------+---+
| md5                    | abc123...             |
| sha1                   | def456...             |
| sha256                 | ghi789...             |
| path                   | suspicious.exe        |
| size                   | 45056                 |
| arch                   | x86                   |
| os                     | windows               |
| format                 | pe                    |
| ...                    |                       |
+------------------------+---+

+----------------------------------------------------------------------+------+
| CAPABILITY                                                           | N/A  |
|----------------------------------------------------------------------+------|
| create process (2 matches)                                           | ✓    |
| write file (3 matches)                                               | ✓    |
| connect to URL (1 match)                                             | ✓    |
| schedule task via at                                                 | ✓    |
| create thread (1 match)                                              | ✓    |
+----------------------------------------------------------------------+------+
```

### ATT&CK output section

```
ATT&CK Tactic                ATT&CK Technique
Execution                    T1059.003 Windows Command Shell
Persistence                  T1053.005 Scheduled Task/Job: Scheduled Task
Defense Evasion              T1055.001 Process Injection: DLL Injection
Command and Control          T1071.001 Application Layer Protocol: Web Protocols
```

### MBC output section (Malware Behavior Catalog)

```
MBC Objective    MBC Behavior
Anti-Analysis    Software Packing (F0001)
Communication    HTTP Communication (C0002)
Execution        Execute Code (B0024)
```

---

## Key Capabilities to Watch For

| Capability | Implication |
|-----------|-------------|
| `inject into process` | Process injection — DLL/shellcode injection |
| `allocate RWX memory` | Shellcode staging area |
| `write to process memory` | Code injection target |
| `create remote thread` | Remote thread injection |
| `hide process` | Rootkit behavior |
| `hook API` | API hooking (keylogger, AMSI bypass) |
| `connect to URL` / `send HTTP request` | C2 communication |
| `resolve API by hash` | Obfuscated API calls (common in loaders) |
| `enumerate processes` | Discovery / targeting |
| `schedule task` / `modify registry run key` | Persistence |
| `dump credentials` | Credential harvesting |
| `read credentials from browser` | Browser credential theft |
| `encrypt data using AES` | Data encryption (ransomware, C2) |
| `decode data using Base64` | Encoded payload / C2 data |

---

## Workflows

### Workflow 1: Quick binary triage

```bash
# 1. Check what binary can do (30 seconds)
capa malware.exe 2>/dev/null

# 2. If packed/obfuscated (capa says "packed"):
capa malware.exe | grep -i "pack\|obfuscat\|encrypt"

# 3. If packed, try unpacking first:
upx -d malware_packed.exe -o malware_unpacked.exe
capa malware_unpacked.exe

# 4. Get JSON for further analysis
capa -j malware.exe > analysis.json
```

### Workflow 2: API hash resolution detection

```bash
capa -v malware.exe | grep -i "hash\|resolve\|GetProcAddress"

# If "resolve API by hash" is detected:
# → binary uses dynamic API resolution (common evasion)
# → look in Ghidra/radare2 for hash computation loops
# → common hash algorithms: ROR13, DJBX33A, FNV1a
```

### Workflow 3: Understand malware before RE

```bash
capa -vv malware.exe > capa_full.txt

# Extract function addresses of interest
grep "0x" capa_full.txt | grep -i "inject\|encrypt\|connect"

# Use those addresses as RE entry points in Ghidra
# Load malware.exe in Ghidra → Go to address from capa output
```

### Workflow 4: Classify sample type

```bash
# Check capabilities to determine type
capa sample.exe 2>/dev/null | grep -E "download|inject|persist|dump|keylog|encrypt"

# Loader indicators:
#   allocate RWX, write shellcode, create thread, resolve API by hash

# Dropper indicators:
#   write file, create process, schedule task

# Ransomware indicators:
#   enumerate files, encrypt data, delete shadow copies

# RAT indicators:
#   capture screenshot, log keystrokes, send HTTP, create remote shell
```

### Workflow 5: AV/EDR evasion research

```bash
# Find what triggers detection
capa -vv malware.exe | grep -i "hook\|amsi\|etw\|patch\|bypass"

# Identify suspicious imports that EDR flags
capa -v malware.exe | grep -i "VirtualAlloc\|WriteProcessMemory\|CreateRemoteThread"

# Compare clean vs evasive tool
capa -j legit_tool.exe > clean.json
capa -j evasive_tool.exe > evasive.json
diff <(jq '.capabilities | keys[]' clean.json | sort) <(jq '.capabilities | keys[]' evasive.json | sort)
```

---

## Dynamic Analysis (Sandbox Reports)

capa supports CAPE sandbox JSON output for dynamic capability extraction:

```bash
# CAPE sandbox output
capa report.json --format cape

# Dynamic capa finds capabilities that only appear at runtime:
#   - packed code that capa can't read statically
#   - capabilities invoked via reflective loading
```

---

## JSON Output and Parsing

```bash
# Full JSON output
capa -j malware.exe | tee capa.json

# Extract capability names only
capa -j malware.exe | jq '.capabilities | keys[]'

# Get ATT&CK technique IDs
capa -j malware.exe | jq '.attack | .[] | .[] | .id'

# Get function addresses for specific capability
capa -j malware.exe | jq '.rules[] | select(.name | contains("inject")) | .matches | keys[]'

# List all matched capabilities with match count
capa -j malware.exe | jq '.rules[] | {name: .name, count: (.matches | length)}'
```

---

## Integration with RE Tools

```bash
# Step 1: capa for overview
capa malware.exe -v > capa_output.txt

# Step 2: extract function addresses of interest
grep "0x" capa_output.txt | head -20

# Step 3: load in Ghidra
# Script → Go to address → paste address from capa output
# Focus RE on identified functions

# Step 4: use capa rules to guide YARA rule creation
# capa rules are in: https://github.com/mandiant/capa-rules
# Use matched strings from capa -vv as YARA string candidates
```

---

## Rule Customization

```bash
# Clone capa rules for inspection/customization
git clone https://github.com/mandiant/capa-rules

# Use custom rule directory
capa --rules /path/to/custom-rules malware.exe

# Combine built-in + custom
capa --rules /path/to/capa-rules --rules /path/to/custom-rules malware.exe
```

**capa rule format (YAML):**
```yaml
rule:
  meta:
    name: detect custom packer
    namespace: anti-analysis/packer
    att&ck:
      - Defense Evasion::Obfuscated Files or Information [T1027]
  features:
    - and:
      - mnemonic: pushad
      - mnemonic: popad
      - number: 0x1000
```

---

## Tips

- `capa` cannot see into packed/encrypted code — unpack first (UPX, custom) then re-run
- `-vv` output shows exact VA addresses → use as RE starting points in Ghidra/r2
- "resolve API by hash" = obfuscated imports → look for `GetProcAddress` + hash computation
- Dynamic sandbox report mode finds runtime-only behaviors static mode misses
- Compare capa JSON output of malware family variants to find common capabilities across samples

## Resources

| File | When to load |
|------|--------------|
| `references/` | Capability interpretation guide, RE pivot strategy, sandbox report setup |
