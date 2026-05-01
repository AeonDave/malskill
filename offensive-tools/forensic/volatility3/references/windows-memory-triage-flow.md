# Volatility3 — Deep Reference

## Vol2 → Vol3 Command Translation

| Vol2 | Vol3 |
|------|------|
| `imageinfo` | `windows.info` |
| `pslist -p PID` | `windows.pslist --pid PID` |
| `dlllist -p PID` | `windows.dlllist --pid PID` |
| `cmdscan` | `windows.cmdline` |
| `netscan` | `windows.netscan` |
| `connscan` | `windows.netstat` |
| `malfind -p PID` | `windows.malfind --pid PID` |
| `dumpfiles -Q ADDR` | `windows.dumpfiles --virtaddr ADDR` |
| `procdump -p PID` | `windows.procdump --pid PID` |
| `memdump -p PID` | `windows.memmap --pid PID --dump` |
| `hivelist` | `windows.registry.hivelist` |
| `printkey -K "path"` | `windows.registry.printkey --key "path"` |
| `mftparser` | `windows.mftscan.MFTScan` |
| `shimcache` | `windows.shimcachemem` |
| `svcscan` | `windows.svcscan` |
| `modules` | `windows.modules` |
| `modscan` | `windows.modscan` |
| `ldrmodules -p PID` | `windows.ldrmodules --pid PID` |
| `hashdump` | `windows.hashdump` |
| `cachedump` | `windows.cachedump` |
| `lsadump` | `windows.lsadump` |
| `atoms` | `windows.atoms` |
| `atomscan` | `windows.atomscan` |
| `ssdt` | `windows.ssdt` |
| `clipboard` | `windows.clipboard` |

---

## Symbol Table Troubleshooting

```bash
# Auto-download check
python3 vol.py -f memory.raw isfinfo

# Symbols stored at: ~/.cache/volatility3/ or volatility3/volatility3/symbols/

# Manual offline install:
# Download from https://github.com/volatilityfoundation/volatility3/releases
# windows.zip, linux.zip, mac.zip
# Extract to: volatility3/volatility3/symbols/

# Force custom symbol path
python3 vol.py -f memory.raw --symbol-dirs /path/to/symbols/ windows.pslist

# Check if ISF exists for kernel
python3 vol.py -f memory.raw isfinfo 2>&1 | head -20

# Build ISF from PDB (for custom/updated kernels)
pip install pdbconv
pdbconv.py -o ntkrnlmp.json ntkrnlmp.pdb
# Place in volatility3/volatility3/symbols/windows/ntkrnlmp.json
```

---

## Linux Memory Analysis

```bash
# Build kernel ISF (dwarf2json — requires debug kernel)
git clone https://github.com/volatilityfoundation/dwarf2json
cd dwarf2json && go build .
./dwarf2json linux --elf /usr/lib/debug/boot/vmlinux-$(uname -r) > linux-kernel.json
# Place in: volatility3/volatility3/symbols/linux/

# Core Linux plugins
python3 vol.py -f linux.mem linux.pslist
python3 vol.py -f linux.mem linux.pstree
python3 vol.py -f linux.mem linux.bash             # bash history from memory
python3 vol.py -f linux.mem linux.netstat
python3 vol.py -f linux.mem linux.lsmod            # loaded kernel modules
python3 vol.py -f linux.mem linux.check_modules    # find hidden/rogue modules
python3 vol.py -f linux.mem linux.malfind
python3 vol.py -f linux.mem linux.envars           # env vars per process
python3 vol.py -f linux.mem linux.proc.maps        # memory maps per process
python3 vol.py -f linux.mem linux.keyboard_notifiers  # keylogger kernel hooks
python3 vol.py -f linux.mem linux.find_file --path /etc/shadow
python3 vol.py -f linux.mem linux.find_file --path /tmp/backdoor
```

---

## Advanced Injection Detection

### Process Hollowing

```bash
# Cross-check: VAD base address differs from known PE base
python3 vol.py -f memory.raw windows.vadinfo --pid 1234 | grep "EXECUTE"

# Dump suspicious region
python3 vol.py -f memory.raw windows.malfind --pid 1234 --dump
strings pid.1234.*.dmp | grep -iE "flag|cmd|powershell|http"
```

### Hidden DLLs (Reflective Injection)

```bash
# ldrmodules: False False False = DLL not in PEB loader list
python3 vol.py -f memory.raw windows.ldrmodules 2>/dev/null | grep "False.*False.*False"

# Dump hidden DLL address
python3 vol.py -f memory.raw windows.dumpfiles --virtaddr 0xXXXXXXXX
file module.0xXXX.dat    # identify type
```

### Kernel Rootkit: SSDT Hooks

```bash
# Hooked SSDT entries = non-ntoskrnl function pointers
python3 vol.py -f memory.raw windows.ssdt 2>/dev/null | grep -v "ntoskrnl\|win32k"
```

---

## MFT Scan (NTFS artifacts from memory)

```bash
# Find files via $MFT cached in memory (includes deleted)
python3 vol.py -f memory.raw windows.mftscan.MFTScan > mft.txt
grep -iE "flag|secret|password" mft.txt

# Alternate Data Streams via MFT
python3 vol.py -f memory.raw windows.mftscan.ADS
```

---

## Shimcache / Execution Evidence

```bash
# AppCompatCache — binaries that ran, even if deleted
python3 vol.py -f memory.raw windows.shimcachemem 2>/dev/null
python3 vol.py -f memory.raw windows.shimcachemem 2>/dev/null | grep -iE "temp|appdata|programdata|users"
```

---

## Memory Image Format Reference

| Format | Extension | Source |
|--------|-----------|--------|
| Raw dump | `.raw` `.mem` `.bin` | winpmem, avml, LiME |
| Windows crash dump | `.dmp` | WinDbg, Windows kernel |
| Hibernation | `hiberfil.sys` | Windows auto |
| VMware snapshot | `.vmem` + `.vmss` | VMware snapshot |
| VirtualBox | `.elf` | vboxmanage debugvm |
| LiME (Linux) | `.lime` | LiME kernel module |

```bash
# VMware: pair .vmem + .vmss
python3 vol.py -f vm.vmem --single-location vm.vmss windows.pslist

# Hibernation file (Windows handles natively)
python3 vol.py -f hiberfil.sys windows.pslist
```

---

## Batch Triage Script

```bash
#!/bin/bash
# Usage: ./vol_triage.sh memory.raw
MEM=$1; OUT="vol_out"; mkdir -p $OUT
V="python3 vol.py -f $MEM"

for plugin in windows.pslist windows.psscan windows.pstree windows.cmdline \
              windows.netscan windows.malfind windows.filescan windows.svcscan \
              windows.hashdump windows.ldrmodules windows.registry.hivelist; do
  echo "[*] $plugin"
  $V $plugin 2>/dev/null > "$OUT/${plugin//./_}.txt"
done

# Anomaly summary
echo "=== Hidden processes ===" > $OUT/anomalies.txt
diff <(awk '{print $2}' $OUT/windows_pslist.txt | sort) \
     <(awk '{print $2}' $OUT/windows_psscan.txt | sort) >> $OUT/anomalies.txt
echo "=== Suspicious cmdline ===" >> $OUT/anomalies.txt
grep -iE "bypass|encoded|downloadstring|temp|appdata" $OUT/windows_cmdline.txt >> $OUT/anomalies.txt
echo "=== Hidden DLLs ===" >> $OUT/anomalies.txt
grep "False.*False.*False" $OUT/windows_ldrmodules.txt >> $OUT/anomalies.txt
echo "[*] Anomaly summary: $OUT/anomalies.txt"
```
