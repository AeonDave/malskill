# Tool Installation Guide

Per-platform install commands for malware analysis tools organized by tier.

## Linux / WSL (Debian/Ubuntu)

### Tier 1 — Core
```bash
sudo apt-get update
sudo apt-get install -y file binutils coreutils
# Python should already be present; if not:
sudo apt-get install -y python3 python3-pip
```

### Tier 2 — Standard
```bash
sudo apt-get install -y binutils yara libimage-exiftool-perl p7zip-full ripgrep xxd binwalk
python3 -m pip install --user pefile lief yara-python capstone oletools pycryptodome
# radare2 — use official install script for latest version
curl -Ls https://github.com/radareorg/radare2/releases/latest/download/radare2_amd64.deb -o /tmp/r2.deb && sudo dpkg -i /tmp/r2.deb
```

### Tier 3 — Advanced
```bash
# FLOSS
pip install flare-floss
# capa
pip install flare-capa
# Ghidra headless — download release, add support/ to PATH
# wget https://github.com/NationalSecurityAgency/ghidra/releases/download/<version>/ghidra_<version>.zip
# jadx
sudo apt-get install -y default-jre
# Download from https://github.com/skylot/jadx/releases
# apktool
sudo apt-get install -y apktool
# GDB + enhancements
sudo apt-get install -y gdb
# pwndbg:
git clone https://github.com/pwndbg/pwndbg ~/pwndbg && cd ~/pwndbg && ./setup.sh
# OR gef:
# bash -c "$(curl -fsSL https://gef.blah.cat/sh)"
# ilspycmd (.NET decompiler)
dotnet tool install --global ilspycmd
# UPX
sudo apt-get install -y upx-ucl
# Detect It Easy
# Download from https://github.com/horsicq/DIE-engine/releases
```

### Tier 4 — Dynamic (lab only)
```bash
sudo apt-get install -y strace ltrace tshark
pip install volatility3 scapy fakenet-ng
```

## Windows (native)

### Tier 1 — Core
```powershell
winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
# 'file' and 'strings' from Git for Windows or SysInternals
winget install --id Microsoft.Sysinternals --accept-source-agreements --accept-package-agreements
```

### Tier 2 — Standard
```powershell
winget install --id 7zip.7zip --accept-source-agreements --accept-package-agreements
winget install --id BurntSushi.ripgrep.MSVC --accept-source-agreements --accept-package-agreements
winget install --id VirusTotal.YARA --accept-source-agreements --accept-package-agreements
winget install --id OliverBetz.ExifTool --accept-source-agreements --accept-package-agreements
py -m pip install --user pefile lief yara-python capstone oletools pycryptodome
# radare2 — download installer from https://github.com/radareorg/radare2/releases
# binwalk — pip install binwalk (limited on Windows; prefer WSL)
```

### Tier 3 — Advanced
```powershell
py -m pip install --user flare-floss flare-capa
winget install --id Microsoft.DotNet.SDK.8 --accept-source-agreements --accept-package-agreements
dotnet tool install --global ilspycmd
# Ghidra — download from ghidra-sre.org, add support\ to PATH
# jadx — download from https://github.com/skylot/jadx/releases
# x64dbg — download from https://x64dbg.com (Windows only)
# UPX — download from https://github.com/upx/upx/releases
```

### Tier 4 — Dynamic (lab only)
```powershell
# Procmon — part of Sysinternals (already installed above)
# Wireshark
winget install --id WiresharkFoundation.Wireshark --accept-source-agreements --accept-package-agreements
py -m pip install --user scapy
# fakenet-ng — download from https://github.com/mandiant/flare-fakenet-ng/releases
```

## macOS

### Tier 2 — Standard
```bash
brew install binutils p7zip yara ripgrep exiftool binwalk
pip3 install --user pefile lief yara-python capstone oletools pycryptodome
brew install radare2
```

### Tier 3 — Advanced
```bash
pip3 install --user flare-floss flare-capa
brew install --cask ghidra
brew install jadx upx
```

## Python-only minimal setup (any platform)

When system package managers are unavailable — this gives basic capability:
```bash
pip install pefile lief yara-python capstone oletools pycryptodome
# Optional advanced:
pip install flare-floss flare-capa unicorn keystone-engine scapy
```
