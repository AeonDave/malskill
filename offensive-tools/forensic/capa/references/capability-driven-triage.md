# capa — Deep Reference

## Namespace Taxonomy

capa organizes rules into a namespace hierarchy. Understanding namespaces helps interpret output and write custom rules.

```
anti-analysis/
    obfuscation/
        string-obfuscation
        packer/
    anti-debugging/
    anti-sandbox/
    anti-vm/
collection/
    file-managers
    keyloggers/
    screenshot
    system-information/
communication/
    c2/
    dns/
    ftp/
    http/
    smtp/
data-manipulation/
    compression/
    encryption/
        aes/
        rc4/
        xor/
    hashing/
executable/
    pe/
host-interaction/
    driver/
    file-system/
    process/
    registry/
impact/
    denial-of-service/
    destruct/
    ransomware/
internal/
lib/
linking/
load-code/
    pe/
    shellcode/
persistence/
    registry/
    startup-folder/
    scheduled-tasks/
```

---

## Custom Rule Format

```yaml
# capa uses YAML rule files with feature-based logic

rule:
  meta:
    name: detect XOR decode loop
    namespace: data-manipulation/encryption/xor
    authors:
      - dave@example.com
    description: Detects a simple XOR decode loop using a single-byte key
    att&ck:
      - Defense Evasion::Obfuscated Files or Information [T1027]
    mbc:
      - Anti-Static Analysis::Executable Code Obfuscation [F0001.008]
    references:
      - https://github.com/mandiant/capa-rules

  features:
    - and:
      - mnemonic: xor              # has xor instruction
      - mnemonic: loop             # has loop/loopne instruction
      - not:
        - mnemonic: xor eax, eax   # exclude zeroing pattern

---

# String-based rule
rule:
  meta:
    name: detect curl user agent
    namespace: communication/http
  features:
    - and:
      - string: "curl/"
        description: curl user agent string
      - api: wininet.HttpSendRequest
```

**Supported feature types:**
```yaml
features:
  - string: "literal"               # exact string
  - string: /regex/                 # regex (limited support)
  - bytes: "6A 40 68"               # hex bytes
  - api: CreateRemoteThread         # API call
  - api: kernel32.VirtualAlloc      # DLL.Function
  - mnemonic: push                  # assembly instruction
  - number: 0x1000                  # immediate value
  - offset: 0x4c                    # memory offset
  - characteristic: peb access      # structural characteristic
  - os: windows                     # OS constraint
  - arch: x32                       # architecture constraint
  - format: pe                      # file format
```

---

## Custom Rule Directory

```bash
# Clone official rules
git clone https://github.com/mandiant/capa-rules

# Use custom rules
capa --rules /path/to/capa-rules --rules /path/to/custom/ target.exe

# Only custom rules
capa --rules /path/to/custom/ target.exe

# Test rule against sample
capa --rules /path/to/rule.yml target.exe -v
```

---

## CAPE Sandbox Dynamic Analysis

```bash
# Run CAPE sandbox locally (Docker)
git clone https://github.com/kevoreilly/CAPEv2
cd CAPEv2 && docker compose up -d

# Submit sample and download report
# GET http://localhost:8000/apiv2/tasks/get/report/<task_id>/

# Run capa on CAPE JSON report
capa report.json --format cape -j | jq '.capabilities | keys[]'

# Dynamic capa finds:
# - Anti-sandbox checks (invoked at runtime)
# - Network communication after unpacking
# - Registry persistence writes
# - Process injection observed during execution
```

---

## Packed Sample Workflow

```bash
# Step 1: detect packing
capa malware.exe 2>/dev/null | grep -i "pack\|obfuscat\|encrypt\|anti"

# Step 2: identify packer
capa -vv malware.exe | grep "namespace"
# or
file malware.exe       # "UPX compressed"
strings malware.exe | grep -i "upx\|aspack\|themida\|vmprotect"

# Step 3: unpack
# UPX:
upx -d malware_packed.exe -o malware_unpacked.exe

# Generic: use x64dbg/OllyDbg or automated unpacker
# https://github.com/malwarelab-eu/unipacker
pip install unipacker
unipacker malware.exe

# Step 4: rerun capa on unpacked
capa malware_unpacked.exe
```

---

## Interpretation Guide: High-Risk Capability Clusters

| Capability cluster | Likely sample type |
|-------------------|--------------------|
| `allocate RWX` + `write shellcode` + `create remote thread` | Injector / dropper |
| `connect to URL` + `decode base64` + `create process` | Downloader / stager |
| `enumerate processes` + `inject into process` + `hook API` | Injector + keylogger |
| `schedule task` + `modify registry run` + `write file` | Persistent dropper |
| `enumerate files` + `encrypt data` + `delete shadow copies` | Ransomware |
| `capture screenshot` + `log keystrokes` + `send HTTP request` | RAT / spyware |
| `resolve API by hash` + `allocate RWX` | Shellcode loader |
| `anti-analysis` + `anti-sandbox` + many checks | Evasive malware |

---

## JSON Output: Full Extraction

```bash
# Generate full JSON
capa -j malware.exe > capa.json

# Extract all detected capabilities
jq '.rules | to_entries[] | {name: .key, count: (.value.matches | length)}' capa.json

# Extract ATT&CK techniques
jq '.rules[].meta["att&ck"][]?' capa.json | jq -r '"\(.tactic.id)\t\(.technique.id)\t\(.technique.name)"' | sort -u

# Extract function addresses for a capability
jq '.rules["detect XOR decode loop"].matches | keys[]' capa.json

# Filter by namespace
jq '.rules | to_entries[] | select(.value.meta.namespace | startswith("communication")) | .key' capa.json

# Compare two samples
diff <(capa -j sample1.exe | jq '.capabilities | keys[]' | sort) \
     <(capa -j sample2.exe | jq '.capabilities | keys[]' | sort)
```

---

## Correlation with Other Tools

| capa finding | Follow-up tool + action |
|-------------|------------------------|
| `allocate RWX` + `write shellcode` | **Ghidra**: navigate to VirtualAlloc call, trace write target |
| `resolve API by hash` | **radare2/x64dbg**: find hash computation loop, decode API names |
| `connect to URL` | **Zeek/Wireshark**: check pcap for C2 URIs matching capa-identified patterns |
| `capture screenshot` + HTTP | **Wireshark**: filter for image MIME types in POST requests |
| `log keystrokes` | **Volatility3**: windows.handles to find SetWindowsHookEx handle |
| `encrypt data using AES` | **x64dbg**: breakpoint at AES init → dump key + IV from memory |
| Persistence namespace | **Autopsy/TSK**: check registry Run keys and scheduled tasks on disk |
