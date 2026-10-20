#!/usr/bin/env python3
"""Resolve System Service Numbers via the PE Exception Directory (.pdata).

Walks the RUNTIME_FUNCTION array in ntdll's .pdata section, matching each
entry's BeginAddress against Zw* exports.  Because .pdata is sorted by
address and SSNs are assigned in address order, counting Zw* matches
yields each function's SSN — without reading stub bytes or sorting exports.

Based on the technique described by MDSec (2022):
  https://www.mdsec.co.uk/2022/04/resolving-system-service-numbers-using-the-exception-directory/

Usage:
    python pdata_ssn_resolve.py                   # uses system ntdll
    python pdata_ssn_resolve.py --ntdll <path>    # explicit path
    python pdata_ssn_resolve.py --target NtAllocateVirtualMemory
    python pdata_ssn_resolve.py --json             # JSON output
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import struct
import sys
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# PE parsing helpers (minimal, no dependencies)
# ---------------------------------------------------------------------------

class ExportEntry(NamedTuple):
    name: str
    rva: int
    ordinal: int


class RuntimeFunction(NamedTuple):
    begin_address: int  # RVA
    end_address: int    # RVA
    unwind_info: int    # RVA


def _read_u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def _read_u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _read_cstring(buf: bytes, off: int, max_len: int = 256) -> str:
    end = buf.find(b"\x00", off, off + max_len)
    if end == -1:
        end = off + max_len
    return buf[off:end].decode("ascii", errors="replace")


def _rva_to_offset(sections: list[tuple[int, int, int, int]], rva: int) -> int | None:
    """Convert an RVA to a file offset using the section table."""
    for va, vs, raw_off, raw_sz in sections:
        if va <= rva < va + vs:
            delta = rva - va
            if delta < raw_sz:
                return raw_off + delta
            return None
    return None


def parse_sections(buf: bytes, pe_off: int, num_sections: int) -> list[tuple[int, int, int, int]]:
    """Return [(VirtualAddress, VirtualSize, PointerToRawData, SizeOfRawData), ...]."""
    # Optional header size is at PE + 4 (sig) + 16
    opt_hdr_size = _read_u16(buf, pe_off + 4 + 16)
    sec_start = pe_off + 4 + 20 + opt_hdr_size  # after NT_HEADERS
    secs = []
    for i in range(num_sections):
        off = sec_start + i * 40
        va = _read_u32(buf, off + 12)
        vs = _read_u32(buf, off + 8)
        raw_off = _read_u32(buf, off + 20)
        raw_sz = _read_u32(buf, off + 16)
        secs.append((va, vs, raw_off, raw_sz))
    return secs


def parse_exports(buf: bytes, sections: list, pe_off: int) -> list[ExportEntry]:
    """Parse the export directory and return named exports."""
    # DataDirectory[0] = Export Directory
    opt_off = pe_off + 4 + 20  # after Signature + FileHeader
    magic = _read_u16(buf, opt_off)
    if magic == 0x20B:  # PE32+
        dd_off = opt_off + 112  # DataDirectory starts at offset 112 in PE32+
    elif magic == 0x10B:  # PE32
        dd_off = opt_off + 96
    else:
        raise ValueError(f"Unknown optional header magic: 0x{magic:04X}")

    export_rva = _read_u32(buf, dd_off)
    export_size = _read_u32(buf, dd_off + 4)
    if export_rva == 0:
        return []

    exp_off = _rva_to_offset(sections, export_rva)
    if exp_off is None:
        return []

    num_functions = _read_u32(buf, exp_off + 20)
    num_names = _read_u32(buf, exp_off + 24)
    addr_table_rva = _read_u32(buf, exp_off + 28)
    name_ptr_rva = _read_u32(buf, exp_off + 32)
    ordinal_table_rva = _read_u32(buf, exp_off + 36)
    ordinal_base = _read_u32(buf, exp_off + 16)

    addr_off = _rva_to_offset(sections, addr_table_rva)
    name_off = _rva_to_offset(sections, name_ptr_rva)
    ord_off = _rva_to_offset(sections, ordinal_table_rva)
    if None in (addr_off, name_off, ord_off):
        return []

    exports = []
    for i in range(num_names):
        name_rva = _read_u32(buf, name_off + i * 4)
        name_file_off = _rva_to_offset(sections, name_rva)
        if name_file_off is None:
            continue
        name = _read_cstring(buf, name_file_off)
        ordinal_index = _read_u16(buf, ord_off + i * 2)
        func_rva = _read_u32(buf, addr_off + ordinal_index * 4)

        # Skip forwarded exports (RVA points inside export directory)
        if export_rva <= func_rva < export_rva + export_size:
            continue

        exports.append(ExportEntry(name, func_rva, ordinal_base + ordinal_index))

    return exports


def parse_pdata(buf: bytes, sections: list, pe_off: int) -> list[RuntimeFunction]:
    """Parse the exception directory (DataDirectory[3]) into RUNTIME_FUNCTION entries."""
    opt_off = pe_off + 4 + 20
    magic = _read_u16(buf, opt_off)
    if magic == 0x20B:
        dd_off = opt_off + 112 + 3 * 8  # DataDirectory[3]
    elif magic == 0x10B:
        dd_off = opt_off + 96 + 3 * 8
    else:
        raise ValueError(f"Unknown optional header magic: 0x{magic:04X}")

    pdata_rva = _read_u32(buf, dd_off)
    pdata_size = _read_u32(buf, dd_off + 4)
    if pdata_rva == 0:
        return []

    pdata_off = _rva_to_offset(sections, pdata_rva)
    if pdata_off is None:
        return []

    count = pdata_size // 12  # sizeof(RUNTIME_FUNCTION) = 12
    entries = []
    for i in range(count):
        off = pdata_off + i * 12
        begin = _read_u32(buf, off)
        end = _read_u32(buf, off + 4)
        unwind = _read_u32(buf, off + 8)
        entries.append(RuntimeFunction(begin, end, unwind))
    return entries


# ---------------------------------------------------------------------------
# SSN resolution via .pdata
# ---------------------------------------------------------------------------

def resolve_ssns_via_pdata(
    buf: bytes,
    sections: list,
    pe_off: int,
    target: str | None = None,
) -> list[tuple[str, int]] | int | None:
    """Walk .pdata entries, match against Zw* exports, count SSNs.

    If target is given, returns just the SSN (int) or None if not found.
    Otherwise returns the full [(name, ssn), ...] table.
    """
    exports = parse_exports(buf, sections, pe_off)
    pdata = parse_pdata(buf, sections, pe_off)

    # Build RVA → export-name lookup for Zw* exports
    rva_to_name: dict[int, str] = {}
    for exp in exports:
        if exp.name.startswith("Zw"):
            rva_to_name[exp.rva] = exp.name

    # Also build Nt→Zw alias map so we can resolve by either prefix
    nt_to_zw: dict[str, str] = {}
    for exp in exports:
        if exp.name.startswith("Zw"):
            nt_name = "Nt" + exp.name[2:]
            nt_to_zw[nt_name] = exp.name

    # Normalize target to Zw prefix for matching
    target_zw = None
    if target:
        if target.startswith("Nt"):
            target_zw = nt_to_zw.get(target, "Zw" + target[2:])
        elif target.startswith("Zw"):
            target_zw = target
        else:
            target_zw = "Zw" + target

    # Walk .pdata (already sorted by BeginAddress) and count Zw* matches
    ssn_counter = 0
    results: list[tuple[str, int]] = []

    for rf in pdata:
        zw_name = rva_to_name.get(rf.begin_address)
        if zw_name is not None:
            results.append((zw_name, ssn_counter))
            if target_zw and zw_name == target_zw:
                return ssn_counter
            ssn_counter += 1

    if target:
        return None  # not found
    return results


# ---------------------------------------------------------------------------
# Cross-validation: compare with FreshyCalls-style sorted-export method
# ---------------------------------------------------------------------------

def resolve_ssns_via_sorted_exports(
    buf: bytes, sections: list, pe_off: int
) -> list[tuple[str, int]]:
    """FreshyCalls/RecycledGate method: sort Zw* exports by RVA, index = SSN."""
    exports = parse_exports(buf, sections, pe_off)
    zw_exports = [(e.name, e.rva) for e in exports if e.name.startswith("Zw")]
    zw_exports.sort(key=lambda x: x[1])
    return [(name, i) for i, (name, _rva) in enumerate(zw_exports)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_ntdll() -> Path:
    """Locate ntdll.dll on the current system."""
    sys_dir = os.environ.get("SystemRoot", r"C:\Windows")
    candidates = [
        Path(sys_dir) / "System32" / "ntdll.dll",
        Path(sys_dir) / "SysWOW64" / "ntdll.dll",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Cannot find ntdll.dll")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve SSNs via the PE Exception Directory (.pdata)"
    )
    parser.add_argument("--ntdll", type=Path, help="Path to ntdll.dll (default: system)")
    parser.add_argument("--target", type=str, help="Resolve a single function (Nt* or Zw*)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--cross-validate", action="store_true",
        help="Compare .pdata results with sorted-export (FreshyCalls) method"
    )
    args = parser.parse_args()

    ntdll_path = args.ntdll or find_ntdll()
    print(f"[*] Reading {ntdll_path}", file=sys.stderr)

    buf = ntdll_path.read_bytes()

    # Validate DOS header
    if buf[:2] != b"MZ":
        print(f"[-] Not a valid PE: {ntdll_path}", file=sys.stderr)
        return 1

    pe_off = _read_u32(buf, 0x3C)
    if buf[pe_off:pe_off + 4] != b"PE\x00\x00":
        print(f"[-] Invalid PE signature at offset 0x{pe_off:X}", file=sys.stderr)
        return 1

    num_sections = _read_u16(buf, pe_off + 4 + 2)
    sections = parse_sections(buf, pe_off, num_sections)

    # Single target lookup
    if args.target:
        ssn = resolve_ssns_via_pdata(buf, sections, pe_off, target=args.target)
        if ssn is None:
            print(f"[-] {args.target}: not found in .pdata", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"function": args.target, "ssn": ssn}))
        else:
            print(f"{args.target}: SSN = 0x{ssn:04X} ({ssn})")
        return 0

    # Full table
    results = resolve_ssns_via_pdata(buf, sections, pe_off)
    if not isinstance(results, list):
        print("[-] Unexpected result type", file=sys.stderr)
        return 1

    if args.cross_validate:
        freshy = resolve_ssns_via_sorted_exports(buf, sections, pe_off)
        freshy_dict = {name: ssn for name, ssn in freshy}
        pdata_dict = {name: ssn for name, ssn in results}

        mismatches = []
        all_names = sorted(set(freshy_dict) | set(pdata_dict))
        for name in all_names:
            f_ssn = freshy_dict.get(name)
            p_ssn = pdata_dict.get(name)
            if f_ssn != p_ssn:
                mismatches.append((name, p_ssn, f_ssn))

        if mismatches:
            print(f"[!] {len(mismatches)} mismatches between .pdata and sorted-export:")
            for name, p, f in mismatches:
                print(f"    {name}: pdata={p} freshy={f}")
        else:
            print(f"[+] All {len(results)} SSNs match between .pdata and sorted-export methods")
        return 0

    if args.json:
        table = [{"function": name, "ssn": ssn} for name, ssn in results]
        print(json.dumps(table, indent=2))
    else:
        print(f"{'Function':<45} {'SSN (hex)':>10} {'SSN (dec)':>10}")
        print("-" * 67)
        for name, ssn in results:
            # Show both Zw and Nt name
            nt_name = "Nt" + name[2:]
            print(f"{name:<45} 0x{ssn:04X}     {ssn:>6}")
        print(f"\nTotal: {len(results)} system services resolved")

    return 0


if __name__ == "__main__":
    sys.exit(main())
