#!/usr/bin/env python3
"""Extract syscall gadgets from the vDSO and libc on a running Linux system.

Locates the vDSO via /proc/self/auxv (AT_SYSINFO_EHDR), parses its ELF
headers, and scans executable segments for SYSCALL;RET (0F 05 C3) gadgets.
Optionally scans libc's text segment as a fallback source.

This is the Linux analog of the Windows .pdata SSN resolver — but instead of
resolving syscall numbers (which are stable on Linux), it resolves gadget
addresses for indirect syscall dispatch.

Usage:
    python vdso_gadget_extract.py                  # vDSO gadgets only
    python vdso_gadget_extract.py --libc           # also scan libc
    python vdso_gadget_extract.py --json           # JSON output
    python vdso_gadget_extract.py --all-patterns   # include SVC #0 on aarch64
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import NamedTuple

if sys.platform != "linux":
    print("This script requires Linux.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# ELF constants
# ---------------------------------------------------------------------------

EI_CLASS = 4
ELFCLASS64 = 2
PT_LOAD = 1
PF_X = 0x1
AT_SYSINFO_EHDR = 33

# Gadget patterns
SYSCALL_RET_X64 = bytes([0x0F, 0x05, 0xC3])          # syscall; ret
SYSCALL_X64 = bytes([0x0F, 0x05])                      # syscall (no ret)
SVC_0_AARCH64 = bytes([0x01, 0x00, 0x00, 0xD4])       # svc #0 (little-endian)


class GadgetInfo(NamedTuple):
    address: int
    source: str       # "vdso" or "libc"
    pattern: str       # "syscall;ret" or "syscall" or "svc #0"
    offset: int        # offset within the mapped region


class MappedRegion(NamedTuple):
    start: int
    end: int
    perms: str
    name: str


# ---------------------------------------------------------------------------
# Auxiliary vector parsing
# ---------------------------------------------------------------------------

def read_auxv() -> dict[int, int]:
    """Read /proc/self/auxv and return {type: value} dict."""
    auxv = {}
    try:
        data = Path("/proc/self/auxv").read_bytes()
    except (FileNotFoundError, PermissionError):
        return auxv

    # Detect word size from ELF class of /proc/self/exe
    word_size = 8  # assume 64-bit
    try:
        exe_hdr = open("/proc/self/exe", "rb").read(5)
        if exe_hdr[EI_CLASS] != ELFCLASS64:
            word_size = 4
    except Exception:
        pass

    fmt = "<QQ" if word_size == 8 else "<II"
    entry_size = struct.calcsize(fmt)

    for i in range(0, len(data) - entry_size + 1, entry_size):
        a_type, a_val = struct.unpack_from(fmt, data, i)
        if a_type == 0:  # AT_NULL
            break
        auxv[a_type] = a_val

    return auxv


def get_vdso_base() -> int | None:
    """Return the vDSO base address from the auxiliary vector."""
    auxv = read_auxv()
    return auxv.get(AT_SYSINFO_EHDR)


# ---------------------------------------------------------------------------
# Memory mapping parsing
# ---------------------------------------------------------------------------

def parse_proc_maps() -> list[MappedRegion]:
    """Parse /proc/self/maps into MappedRegion list."""
    regions = []
    try:
        for line in Path("/proc/self/maps").read_text().splitlines():
            parts = line.split(None, 5)
            if len(parts) < 5:
                continue
            addr_range, perms = parts[0], parts[1]
            name = parts[5].strip() if len(parts) > 5 else ""
            start_s, end_s = addr_range.split("-")
            start = int(start_s, 16)
            end = int(end_s, 16)
            regions.append(MappedRegion(start, end, perms, name))
    except (FileNotFoundError, PermissionError):
        pass
    return regions


def find_vdso_region() -> MappedRegion | None:
    """Find the [vdso] mapping."""
    for r in parse_proc_maps():
        if r.name == "[vdso]":
            return r
    return None


def find_libc_text_regions() -> list[MappedRegion]:
    """Find executable libc mappings."""
    results = []
    for r in parse_proc_maps():
        if "x" in r.perms and ("libc" in r.name or "libc.so" in r.name):
            results.append(r)
    return results


# ---------------------------------------------------------------------------
# ELF parsing (minimal, from memory)
# ---------------------------------------------------------------------------

def read_process_memory(addr: int, size: int) -> bytes | None:
    """Read `size` bytes from the current process at `addr`."""
    try:
        with open("/proc/self/mem", "rb") as f:
            f.seek(addr)
            return f.read(size)
    except (OSError, ValueError):
        return None


def validate_elf_header(base: int) -> bool:
    """Check if base points to a valid ELF header."""
    hdr = read_process_memory(base, 16)
    if hdr is None:
        return False
    return hdr[:4] == b"\x7fELF"


def get_elf_phdr_info(base: int) -> tuple[int, int, int] | None:
    """Return (phoff, phentsize, phnum) from a 64-bit ELF header at base."""
    hdr = read_process_memory(base, 64)
    if hdr is None or hdr[:4] != b"\x7fELF":
        return None
    if hdr[EI_CLASS] != ELFCLASS64:
        return None  # only handle 64-bit
    phoff = struct.unpack_from("<Q", hdr, 32)[0]
    phentsize = struct.unpack_from("<H", hdr, 54)[0]
    phnum = struct.unpack_from("<H", hdr, 56)[0]
    return (phoff, phentsize, phnum)


def find_executable_segments(base: int) -> list[tuple[int, int]]:
    """Return [(vaddr, memsz)] of executable PT_LOAD segments."""
    info = get_elf_phdr_info(base)
    if info is None:
        return []

    phoff, phentsize, phnum = info
    segments = []

    for i in range(phnum):
        phdr_data = read_process_memory(base + phoff + i * phentsize, phentsize)
        if phdr_data is None or len(phdr_data) < 56:
            continue
        p_type = struct.unpack_from("<I", phdr_data, 0)[0]
        p_flags = struct.unpack_from("<I", phdr_data, 4)[0]
        p_vaddr = struct.unpack_from("<Q", phdr_data, 16)[0]
        p_memsz = struct.unpack_from("<Q", phdr_data, 40)[0]

        if p_type == PT_LOAD and (p_flags & PF_X):
            # p_vaddr is relative to base for shared objects
            segments.append((base + p_vaddr, p_memsz))

    return segments


# ---------------------------------------------------------------------------
# Gadget scanning
# ---------------------------------------------------------------------------

def scan_for_gadgets(
    base: int,
    segments: list[tuple[int, int]],
    source_name: str,
    include_all: bool = False,
) -> list[GadgetInfo]:
    """Scan executable segments for syscall gadgets."""
    gadgets = []

    for seg_addr, seg_size in segments:
        data = read_process_memory(seg_addr, seg_size)
        if data is None:
            continue

        # SYSCALL;RET (0F 05 C3)
        offset = 0
        while True:
            idx = data.find(SYSCALL_RET_X64, offset)
            if idx == -1:
                break
            gadgets.append(GadgetInfo(
                address=seg_addr + idx,
                source=source_name,
                pattern="syscall;ret",
                offset=idx,
            ))
            offset = idx + 1

        # Bare SYSCALL without RET (include only with --all-patterns)
        if include_all:
            offset = 0
            while True:
                idx = data.find(SYSCALL_X64, offset)
                if idx == -1:
                    break
                # Skip if this is already part of a syscall;ret
                if idx + 2 < len(data) and data[idx + 2] == 0xC3:
                    offset = idx + 1
                    continue
                gadgets.append(GadgetInfo(
                    address=seg_addr + idx,
                    source=source_name,
                    pattern="syscall",
                    offset=idx,
                ))
                offset = idx + 1

    return gadgets


def scan_region_raw(
    region: MappedRegion,
    source_name: str,
    include_all: bool = False,
) -> list[GadgetInfo]:
    """Scan a mapped region directly (without ELF parsing)."""
    size = region.end - region.start
    return scan_for_gadgets(
        region.start,
        [(region.start, size)],
        source_name,
        include_all,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract syscall gadgets from vDSO and libc"
    )
    parser.add_argument("--libc", action="store_true", help="Also scan libc text segments")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--all-patterns", action="store_true",
        help="Include bare SYSCALL (no RET) and SVC #0 patterns"
    )
    args = parser.parse_args()

    all_gadgets: list[GadgetInfo] = []

    # --- vDSO ---
    vdso_base = get_vdso_base()
    if vdso_base is not None:
        print(f"[*] vDSO base: 0x{vdso_base:x}", file=sys.stderr)
        if validate_elf_header(vdso_base):
            segments = find_executable_segments(vdso_base)
            gadgets = scan_for_gadgets(vdso_base, segments, "vdso", args.all_patterns)
            all_gadgets.extend(gadgets)
            print(f"[+] vDSO: {len(gadgets)} gadget(s) found", file=sys.stderr)
        else:
            # Fallback: scan from /proc/self/maps
            region = find_vdso_region()
            if region:
                gadgets = scan_region_raw(region, "vdso", args.all_patterns)
                all_gadgets.extend(gadgets)
                print(f"[+] vDSO (maps fallback): {len(gadgets)} gadget(s)", file=sys.stderr)
            else:
                print("[-] vDSO: ELF validation failed and no [vdso] in maps", file=sys.stderr)
    else:
        print("[-] vDSO: AT_SYSINFO_EHDR not found in auxv", file=sys.stderr)
        region = find_vdso_region()
        if region:
            gadgets = scan_region_raw(region, "vdso", args.all_patterns)
            all_gadgets.extend(gadgets)
            print(f"[+] vDSO (maps fallback): {len(gadgets)} gadget(s)", file=sys.stderr)

    # --- libc ---
    if args.libc:
        libc_regions = find_libc_text_regions()
        if libc_regions:
            for region in libc_regions:
                gadgets = scan_region_raw(region, "libc", args.all_patterns)
                all_gadgets.extend(gadgets)
            print(f"[+] libc: {len([g for g in all_gadgets if g.source == 'libc'])} gadget(s) from {len(libc_regions)} text region(s)", file=sys.stderr)
        else:
            print("[-] libc: no executable libc regions found", file=sys.stderr)

    # --- Output ---
    if not all_gadgets:
        print("[-] No gadgets found", file=sys.stderr)
        return 1

    if args.json:
        table = [{
            "address": f"0x{g.address:x}",
            "source": g.source,
            "pattern": g.pattern,
            "offset": g.offset,
        } for g in all_gadgets]
        print(json.dumps(table, indent=2))
    else:
        print(f"\n{'Address':<20} {'Source':<8} {'Pattern':<14} {'Offset':<10}")
        print("-" * 54)
        for g in all_gadgets:
            print(f"0x{g.address:<18x} {g.source:<8} {g.pattern:<14} 0x{g.offset:<8x}")
        print(f"\nTotal: {len(all_gadgets)} gadgets")

        # Summary
        vdso_count = len([g for g in all_gadgets if g.source == "vdso"])
        libc_count = len([g for g in all_gadgets if g.source == "libc"])
        print(f"  vDSO: {vdso_count}  |  libc: {libc_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
