#!/usr/bin/env python3
"""Detect OS, enumerate available analysis tools, and install missing packages
after user confirmation. Zero external dependencies.

Usage:
    python setup_env.py [--install] [--tier 1|2|3|4]

Without --install, only reports tool availability.
With --install, prompts before each install action.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys

# ── Tool definitions ─────────────────────────────────────────────────────────

TOOLS = {
    1: {  # Core
        "cli": ["file", "strings", "python3", "py", "pip3", "pip"],
        "python_pkgs": [],
    },
    2: {  # Standard
        "cli": [
            "objdump", "dumpbin", "readelf", "nm", "yara", "exiftool",
            "7z", "r2", "rabin2", "rg", "xxd", "binwalk",
        ],
        "python_pkgs": ["pefile", "lief", "yara-python", "capstone", "oletools", "pycryptodome"],
    },
    3: {  # Advanced
        "cli": [
            "floss", "capa", "analyzeHeadless", "jadx", "apktool",
            "ilspycmd", "gdb", "upx", "diec",
        ],
        "python_pkgs": ["unicorn", "keystone-engine"],
    },
    4: {  # Dynamic (lab only)
        "cli": ["strace", "ltrace", "tshark", "procmon"],
        "python_pkgs": ["volatility3", "scapy"],
    },
}

# ── Install commands per platform ────────────────────────────────────────────

APT_PACKAGES = {
    "file": "file", "strings": "binutils", "objdump": "binutils",
    "readelf": "binutils", "nm": "binutils", "xxd": "xxd",
    "yara": "yara", "exiftool": "libimage-exiftool-perl",
    "7z": "p7zip-full", "rg": "ripgrep", "binwalk": "binwalk",
    "gdb": "gdb", "strace": "strace", "ltrace": "ltrace",
    "tshark": "tshark", "upx": "upx-ucl",
}

WINGET_PACKAGES = {
    "python3": "Python.Python.3.12", "py": "Python.Python.3.12",
    "7z": "7zip.7zip", "rg": "BurntSushi.ripgrep.MSVC",
    "yara": "VirusTotal.YARA",
    "exiftool": "OliverBetz.ExifTool",
}

PIP_INSTALL = "pip install --user"

# ── Detection ────────────────────────────────────────────────────────────────

def detect_platform() -> dict:
    system = platform.system()
    is_wsl = False
    if system == "Linux":
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    is_wsl = True
        except FileNotFoundError:
            pass

    return {
        "system": system,
        "is_wsl": is_wsl,
        "machine": platform.machine(),
        "python": sys.version,
        "label": f"{system} (WSL)" if is_wsl else system,
    }

def check_cli_tool(name: str) -> bool:
    return shutil.which(name) is not None

def check_python_pkg(name: str) -> bool:
    pkg_import = name.replace("-", "_").replace("yara_python", "yara")
    try:
        __import__(pkg_import)
        return True
    except ImportError:
        return False

def enumerate_tools(max_tier: int) -> dict:
    results = {"available": [], "missing": []}
    for tier in range(1, max_tier + 1):
        for tool in TOOLS[tier]["cli"]:
            entry = {"name": tool, "tier": tier, "type": "cli"}
            if check_cli_tool(tool):
                entry["status"] = "OK"
                results["available"].append(entry)
            else:
                entry["status"] = "MISSING"
                results["missing"].append(entry)
        for pkg in TOOLS[tier]["python_pkgs"]:
            entry = {"name": pkg, "tier": tier, "type": "python"}
            if check_python_pkg(pkg):
                entry["status"] = "OK"
                results["available"].append(entry)
            else:
                entry["status"] = "MISSING"
                results["missing"].append(entry)
    return results

# ── Installation ─────────────────────────────────────────────────────────────

def install_tool(tool: dict, info: dict) -> bool:
    name = tool["name"]

    if tool["type"] == "python":
        cmd = f"{sys.executable} -m pip install --user {name}"
        print(f"  $ {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0

    if tool["type"] == "cli":
        if info["system"] == "Linux" or info["is_wsl"]:
            apt_pkg = APT_PACKAGES.get(name)
            if apt_pkg:
                cmd = f"sudo apt-get install -y {apt_pkg}"
                print(f"  $ {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.returncode == 0
        elif info["system"] == "Windows":
            winget_id = WINGET_PACKAGES.get(name)
            if winget_id:
                cmd = f"winget install --id {winget_id} --accept-source-agreements --accept-package-agreements"
                print(f"  $ {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.returncode == 0

    print(f"  [SKIP] No automated install for '{name}' on {info['label']}")
    return False

# ── Output ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Malware analysis environment setup")
    parser.add_argument("--install", action="store_true", help="Attempt to install missing tools (prompts first)")
    parser.add_argument("--tier", type=int, default=3, choices=[1, 2, 3, 4],
                        help="Maximum tool tier to check (default: 3)")
    args = parser.parse_args()

    info = detect_platform()
    print("=" * 64)
    print("  Malware Analysis Environment Check")
    print("=" * 64)
    print(f"  Platform:  {info['label']}")
    print(f"  Arch:      {info['machine']}")
    print(f"  Python:    {info['python'].split()[0]}")

    results = enumerate_tools(args.tier)

    print(f"\n{'─' * 56}")
    print(f"  Available ({len(results['available'])})")
    print(f"{'─' * 56}")
    for t in results["available"]:
        print(f"  [OK]    T{t['tier']}  {t['name']:<24s}  ({t['type']})")

    print(f"\n{'─' * 56}")
    print(f"  Missing ({len(results['missing'])})")
    print(f"{'─' * 56}")
    for t in results["missing"]:
        print(f"  [MISS]  T{t['tier']}  {t['name']:<24s}  ({t['type']})")

    if not results["missing"]:
        print("\n  All tools available. Environment is ready.")
        print(f"{'=' * 64}")
        return

    # Coverage report
    total = len(results["available"]) + len(results["missing"])
    pct = len(results["available"]) / total * 100 if total > 0 else 0
    print(f"\n  Coverage: {len(results['available'])}/{total} ({pct:.0f}%)")

    if args.install:
        print(f"\n{'─' * 56}")
        print("  Installation")
        print(f"{'─' * 56}")
        for t in results["missing"]:
            answer = input(f"  Install {t['name']}? [y/N] ").strip().lower()
            if answer == "y":
                ok = install_tool(t, info)
                status = "[OK]" if ok else "[FAIL]"
                print(f"  {status} {t['name']}")
            else:
                print(f"  [SKIP] {t['name']}")

    print(f"\n{'=' * 64}")

if __name__ == "__main__":
    main()
