"""Tests for pdata_ssn_resolve.py — validates PE parsing and SSN resolution."""

from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

import pytest

# Allow importing from the parent scripts directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdata_ssn_resolve as mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_ntdll() -> Path | None:
    """Return ntdll path or None if not on Windows."""
    if sys.platform != "win32":
        return None
    try:
        return mod.find_ntdll()
    except FileNotFoundError:
        return None


NTDLL = _find_ntdll()
NEED_NTDLL = pytest.mark.skipif(NTDLL is None, reason="ntdll.dll not available")


def _load_ntdll():
    """Load ntdll and return (buf, sections, pe_off)."""
    buf = NTDLL.read_bytes()
    pe_off = mod._read_u32(buf, 0x3C)
    num_sec = mod._read_u16(buf, pe_off + 4 + 2)
    sections = mod.parse_sections(buf, pe_off, num_sec)
    return buf, sections, pe_off


# ---------------------------------------------------------------------------
# Unit tests for PE parsing primitives
# ---------------------------------------------------------------------------

class TestParsePrimitives:
    def test_read_u16(self):
        buf = struct.pack("<HH", 0x1234, 0x5678)
        assert mod._read_u16(buf, 0) == 0x1234
        assert mod._read_u16(buf, 2) == 0x5678

    def test_read_u32(self):
        buf = struct.pack("<I", 0xDEADBEEF)
        assert mod._read_u32(buf, 0) == 0xDEADBEEF

    def test_read_cstring(self):
        buf = b"hello\x00world\x00"
        assert mod._read_cstring(buf, 0) == "hello"
        assert mod._read_cstring(buf, 6) == "world"

    def test_read_cstring_no_null(self):
        buf = b"ABCD"
        assert mod._read_cstring(buf, 0, max_len=4) == "ABCD"

    def test_rva_to_offset(self):
        # section at VA=0x1000, VSize=0x2000, RawOff=0x400, RawSize=0x2000
        sections = [(0x1000, 0x2000, 0x400, 0x2000)]
        assert mod._rva_to_offset(sections, 0x1000) == 0x400
        assert mod._rva_to_offset(sections, 0x1500) == 0x900
        assert mod._rva_to_offset(sections, 0x5000) is None  # outside

    def test_rva_to_offset_raw_smaller_than_virtual(self):
        # RawSize < VirtualSize: RVA inside virtual but beyond raw → None
        sections = [(0x1000, 0x2000, 0x400, 0x100)]
        assert mod._rva_to_offset(sections, 0x1000) == 0x400
        assert mod._rva_to_offset(sections, 0x1200) is None


# ---------------------------------------------------------------------------
# Integration tests (require ntdll.dll on Windows)
# ---------------------------------------------------------------------------

@NEED_NTDLL
class TestNtdllParsing:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.buf, self.sections, self.pe_off = _load_ntdll()

    def test_pe_signature(self):
        assert self.buf[:2] == b"MZ"
        assert self.buf[self.pe_off:self.pe_off + 4] == b"PE\x00\x00"

    def test_exports_not_empty(self):
        exports = mod.parse_exports(self.buf, self.sections, self.pe_off)
        assert len(exports) > 100

    def test_has_zw_exports(self):
        exports = mod.parse_exports(self.buf, self.sections, self.pe_off)
        zw = [e for e in exports if e.name.startswith("Zw")]
        assert len(zw) > 200  # ntdll has ~470+ Zw exports

    def test_pdata_not_empty(self):
        pdata = mod.parse_pdata(self.buf, self.sections, self.pe_off)
        assert len(pdata) > 100

    def test_pdata_sorted_by_begin(self):
        pdata = mod.parse_pdata(self.buf, self.sections, self.pe_off)
        begins = [rf.begin_address for rf in pdata]
        assert begins == sorted(begins), ".pdata not sorted by BeginAddress"

    def test_resolve_known_ssn(self):
        """NtAllocateVirtualMemory has been SSN 0x18 on every known x64 build."""
        ssn = mod.resolve_ssns_via_pdata(
            self.buf, self.sections, self.pe_off,
            target="NtAllocateVirtualMemory",
        )
        assert ssn == 0x18

    def test_resolve_zw_prefix(self):
        ssn = mod.resolve_ssns_via_pdata(
            self.buf, self.sections, self.pe_off,
            target="ZwAllocateVirtualMemory",
        )
        assert ssn == 0x18

    def test_resolve_nonexistent(self):
        ssn = mod.resolve_ssns_via_pdata(
            self.buf, self.sections, self.pe_off,
            target="NtCompletelyBogusFunction",
        )
        assert ssn is None

    def test_full_table_not_empty(self):
        results = mod.resolve_ssns_via_pdata(self.buf, self.sections, self.pe_off)
        assert isinstance(results, list)
        assert len(results) > 200

    def test_ssns_are_sequential(self):
        results = mod.resolve_ssns_via_pdata(self.buf, self.sections, self.pe_off)
        ssns = [ssn for _, ssn in results]
        assert ssns == list(range(len(ssns)))

    def test_cross_validation_all_match(self):
        """The .pdata method must produce identical SSNs to the sorted-export method."""
        pdata_results = mod.resolve_ssns_via_pdata(self.buf, self.sections, self.pe_off)
        freshy_results = mod.resolve_ssns_via_sorted_exports(
            self.buf, self.sections, self.pe_off
        )
        pdata_dict = {n: s for n, s in pdata_results}
        freshy_dict = {n: s for n, s in freshy_results}
        assert pdata_dict == freshy_dict


# ---------------------------------------------------------------------------
# CLI integration test
# ---------------------------------------------------------------------------

@NEED_NTDLL
class TestCLI:
    def test_json_single(self, tmp_path):
        import subprocess
        script = Path(__file__).resolve().parent.parent / "pdata_ssn_resolve.py"
        result = subprocess.run(
            [sys.executable, "-I", str(script), "--target", "NtClose", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["function"] == "NtClose"
        assert isinstance(data["ssn"], int)
        assert data["ssn"] >= 0

    def test_cross_validate_cli(self):
        import subprocess
        script = Path(__file__).resolve().parent.parent / "pdata_ssn_resolve.py"
        result = subprocess.run(
            [sys.executable, "-I", str(script), "--cross-validate"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "match" in result.stdout.lower() or "match" in result.stderr.lower()
