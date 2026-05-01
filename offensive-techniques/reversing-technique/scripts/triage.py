#!/usr/bin/env python3
"""
triage.py — Quick binary triage before full reverse engineering.

Covers: type detection, entropy, section analysis, import flagging,
Go/Rust/C++ marker detection, and offensive string leak scan.

Requires only Python stdlib. Works on PE (Windows) and ELF (Linux) files.

Usage:
    python triage.py <binary> [binary ...]
    python triage.py sample.exe
    python triage.py --full sample.exe     # show all string matches, not just first 5
"""

import argparse
import math
import re
import struct
import sys
from pathlib import Path


# ─────────────────────────── entropy ───────────────────────────────────────────

def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    ent = 0.0
    for f in freq:
        if f > 0:
            p = f / n
            ent -= p * math.log2(p)
    return ent


def entropy_label(ent: float) -> str:
    if ent > 7.5:
        return "ENCRYPTED/COMPRESSED"
    if ent > 6.8:
        return "high"
    if ent > 5.5:
        return "medium (code)"
    if ent > 3.0:
        return "structured"
    return "low"


def byte_distribution_stats(data: bytes) -> dict:
    if not data:
        return {"unique_bytes": 0, "chi2": 0.0}
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    unique = sum(1 for f in freq if f > 0)
    expected = n / 256
    chi2 = sum((f - expected) ** 2 / expected for f in freq) if expected > 0 else 0
    return {"unique_bytes": unique, "chi2": round(chi2, 1)}


def classify_region(entropy: float, stats: dict) -> str:
    if entropy > 7.5 and stats["unique_bytes"] > 250:
        return "ENCRYPTED"
    if entropy > 6.8 and stats["chi2"] < 1000:
        return "ENCRYPTED"
    if entropy > 6.8:
        return "COMPRESSED"
    if entropy > 5.5:
        return "CODE/DATA"
    if entropy > 3.0:
        return "STRUCTURED"
    if entropy > 0.5:
        return "PADDING"
    return "EMPTY"


# ─────────────────────────── PE parsing ────────────────────────────────────────

def is_pe(data: bytes) -> bool:
    if len(data) < 0x40:
        return False
    if data[:2] != b"MZ":
        return False
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    return len(data) > e_lfanew + 4 and data[e_lfanew:e_lfanew + 4] == b"PE\x00\x00"


def is_elf(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == b"\x7fELF"


def parse_pe_headers(pe: bytes) -> dict:
    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    machine = struct.unpack_from("<H", pe, e_lfanew + 4)[0]
    num_sec = struct.unpack_from("<H", pe, e_lfanew + 6)[0]
    timestamp = struct.unpack_from("<I", pe, e_lfanew + 8)[0]
    opt_magic = struct.unpack_from("<H", pe, e_lfanew + 24)[0]
    is_64 = opt_magic == 0x20B

    machine_names = {
        0x014C: "x86", 0x8664: "x64", 0x01C4: "ARM", 0xAA64: "ARM64",
    }
    characteristics = struct.unpack_from("<H", pe, e_lfanew + 22)[0]
    is_dll = bool(characteristics & 0x2000)

    return {
        "e_lfanew": e_lfanew,
        "machine": machine_names.get(machine, f"0x{machine:04X}"),
        "is_64": is_64,
        "is_dll": is_dll,
        "num_sections": num_sec,
        "timestamp": timestamp,
        "opt_size": struct.unpack_from("<H", pe, e_lfanew + 20)[0],
    }


def parse_pe_sections(pe: bytes, hdr: dict) -> list:
    e_lfanew = hdr["e_lfanew"]
    sec_off = e_lfanew + 24 + hdr["opt_size"]
    sections = []
    for i in range(hdr["num_sections"]):
        s = sec_off + i * 40
        name = pe[s:s + 8].rstrip(b"\x00").decode("ascii", "ignore")
        vs = struct.unpack_from("<I", pe, s + 8)[0]
        va = struct.unpack_from("<I", pe, s + 12)[0]
        rs = struct.unpack_from("<I", pe, s + 16)[0]
        ro = struct.unpack_from("<I", pe, s + 20)[0]
        chars = struct.unpack_from("<I", pe, s + 36)[0]
        sections.append({"name": name, "va": va, "vs": vs, "ro": ro, "rs": rs, "chars": chars})
    return sections


def is_dotnet_pe(pe: bytes, hdr: dict) -> bool:
    """Detect managed .NET PE by checking CLR Runtime Header data directory (index 14)."""
    e_lfanew = hdr["e_lfanew"]
    opt_off = e_lfanew + 24
    dd_base = opt_off + (112 if hdr["is_64"] else 96)
    cli_dir_off = dd_base + (14 * 8)

    if len(pe) < cli_dir_off + 8:
        return False

    cli_rva, cli_size = struct.unpack_from("<II", pe, cli_dir_off)
    return cli_rva != 0 and cli_size != 0


def rva_to_offset(rva: int, sections: list) -> int:
    for sec in sections:
        if sec["va"] <= rva < sec["va"] + sec["vs"]:
            return rva - sec["va"] + sec["ro"]
    return rva  # best-effort for header data


def parse_imports(pe: bytes, hdr: dict, sections: list) -> list:
    """Parse import directory table. Returns list of (dll, [functions])."""
    e_lfanew = hdr["e_lfanew"]
    opt_off = e_lfanew + 24
    is_64 = hdr["is_64"]
    dd_base = opt_off + (112 if is_64 else 96)

    if len(pe) < dd_base + 16:
        return []
    import_rva = struct.unpack_from("<I", pe, dd_base + 8)[0]
    if import_rva == 0:
        return []

    import_off = rva_to_offset(import_rva, sections)
    if import_off <= 0 or import_off >= len(pe):
        return []

    result = []
    while import_off + 20 <= len(pe):
        name_rva = struct.unpack_from("<I", pe, import_off + 12)[0]
        ilt_rva = struct.unpack_from("<I", pe, import_off)[0]
        if name_rva == 0:
            break
        name_off = rva_to_offset(name_rva, sections)
        try:
            dll = pe[name_off:pe.index(b"\x00", name_off)].decode("ascii", "ignore")
        except (ValueError, UnicodeDecodeError):
            dll = "?"

        funcs = []
        if ilt_rva:
            ilt_off = rva_to_offset(ilt_rva, sections)
            stride = 8 if is_64 else 4
            max_iter = 300
            while ilt_off + stride <= len(pe) and max_iter > 0:
                max_iter -= 1
                entry = struct.unpack_from("<Q" if is_64 else "<I", pe, ilt_off)[0]
                if entry == 0:
                    break
                ordinal_flag = (1 << 63) if is_64 else (1 << 31)
                if not (entry & ordinal_flag):
                    hint_off = rva_to_offset(entry & 0x7FFFFFFF, sections)
                    if 0 < hint_off < len(pe) - 2:
                        try:
                            end = pe.index(b"\x00", hint_off + 2)
                            funcs.append(pe[hint_off + 2:end].decode("ascii", "ignore"))
                        except (ValueError, UnicodeDecodeError):
                            pass
                ilt_off += stride

        result.append((dll.lower(), funcs))
        import_off += 20
    return result


# ─────────────────────────── suspicious API detection ──────────────────────────

INJECTION_APIS = {
    "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "VirtualProtectEx",
    "WriteProcessMemory", "NtWriteVirtualMemory", "NtAllocateVirtualMemory",
    "CreateRemoteThread", "CreateRemoteThreadEx", "RtlCreateUserThread",
    "NtCreateThreadEx", "QueueUserAPC", "NtQueueApcThread",
    "SetThreadContext", "NtSetContextThread", "ResumeThread", "NtResumeThread",
}

EVASION_APIS = {
    "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
    "NtQueryInformationProcess", "GetTickCount", "GetTickCount64",
    "QueryPerformanceCounter", "OutputDebugStringA", "OutputDebugStringW",
    "SetUnhandledExceptionFilter", "NtSetInformationThread",
}

PROCESS_APIS = {
    "OpenProcess", "CreateProcessA", "CreateProcessW",
    "NtOpenProcess", "TerminateProcess", "CreateProcessInternalW",
}

NETWORK_APIS = {
    "InternetOpenA", "InternetOpenW", "InternetConnectA", "WinHttpOpen",
    "WinHttpConnect", "WSAStartup", "socket", "connect", "send", "recv",
    "HttpSendRequestA", "HttpSendRequestW",
}

CRYPTO_APIS = {
    "CryptAcquireContextA", "CryptEncrypt", "CryptDecrypt",
    "CryptGenRandom", "BCryptGenRandom", "BCryptEncrypt", "BCryptDecrypt",
}

CATEGORY_MAP = {
    "INJECTION": INJECTION_APIS,
    "EVASION":   EVASION_APIS,
    "PROCESS":   PROCESS_APIS,
    "NETWORK":   NETWORK_APIS,
    "CRYPTO":    CRYPTO_APIS,
}

DANGEROUS_COMBOS = [
    ({"VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread"},    "process injection"),
    ({"VirtualAlloc", "VirtualProtect", "CreateThread"},                "local shellcode exec"),
    ({"QueueUserAPC", "ResumeThread"},                                  "early-bird APC injection"),
    ({"SetThreadContext", "ResumeThread"},                              "thread hijacking"),
    ({"NtAllocateVirtualMemory", "NtWriteVirtualMemory", "NtCreateThreadEx"}, "direct syscall injection"),
]


def flag_imports(imports: list) -> dict:
    all_funcs = {f for _, fns in imports for f in fns}
    hits = {}
    for cat, api_set in CATEGORY_MAP.items():
        found = [f for f in all_funcs if f in api_set]
        if found:
            hits[cat] = found
    combos = []
    for combo, label in DANGEROUS_COMBOS:
        if combo.issubset(all_funcs):
            combos.append(label)
    return {"categories": hits, "combos": combos}


# ─────────────────────────── string scanning ───────────────────────────────────

OFFENSIVE_TERMS = [
    "beacon", "implant", "stager", "dropper", "shellcode", "c2server",
    "teamserver", "callback", "inject", "loader", "reflective", "hollowing",
    "stomping", "donut", "srdi", "evasion", "unhook", "amsi", "etw",
    "antidebug", "anti_debug", "sandbox", "sleep_obf", "cobalt", "sliver",
    "havoc", "metasploit", "meterpreter", "xor_decrypt", "rc4_crypt",
]

COMPILER_ARTIFACTS = [
    "GCC:", "mingw", "MinGW", "x86_64-w64-mingw32",
    "clang", "LLVM", "rustc", "/rustc/", "core::fmt", "core::panicking",
    "panicked at", "go.buildid", "runtime.main", "runtime.goexit",
    "GOROOT", "go:buildid", "/usr/local/go",
]

DEBUG_PATTERNS = [
    r"[A-Za-z]:\\[^\x00]{4,60}\.pdb",
    r"[A-Za-z]:\\[^\x00]{4,60}\\src\\",
    r"/home/[^\x00/]{2,40}/",
    r"[A-Za-z]:\\Users\\[^\x00]{2,30}\\",
]

RUNTIME_API_TARGETS = [
    "NtAllocateVirtualMemory", "NtProtectVirtualMemory", "NtWriteVirtualMemory",
    "NtCreateThreadEx", "NtQueryInformationProcess", "NtOpenProcess",
    "EtwEventWrite", "AmsiScanBuffer", "AmsiInitialize",
    "LdrLoadDll", "LdrGetProcedureAddress", "DbgUiRemoteBreakin",
]


def scan_strings_in_data(data: bytes, terms: list, label: str, limit: int = 5) -> list:
    """Scan raw bytes for plain-text string matches (ASCII decode, word boundaries for short patterns)."""
    text = data.decode("ascii", "ignore")
    findings = []
    seen = set()
    for term in terms:
        if term in seen:
            continue
        flags = re.IGNORECASE
        if len(term) <= 5:
            pat = r"(?<![a-zA-Z0-9_])" + re.escape(term) + r"(?![a-zA-Z0-9_])"
        else:
            pat = re.escape(term)
        if re.search(pat, text, flags):
            findings.append(term)
            seen.add(term)
            if len(findings) >= limit:
                break
    return findings


def scan_regex_in_data(data: bytes, patterns: list, label: str, limit: int = 5) -> list:
    text = data.decode("ascii", "ignore")
    findings = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            findings.append(m.group()[:80])
            if len(findings) >= limit:
                return findings
    return findings


# ─────────────────────────── Go / Rust / .NET / C++ markers ───────────────────────────

def detect_language_markers(data: bytes, is_dotnet: bool = False) -> dict:
    markers = {}

    # .NET
    dotnet_markers = {
        "mscoree.dll": data.count(b"mscoree.dll"),
        "_CorExeMain": data.count(b"_CorExeMain"),
        "mscorlib/System.Private.CoreLib": data.count(b"mscorlib") + data.count(b"System.Private.CoreLib"),
    }
    if is_dotnet or sum(dotnet_markers.values()) > 0:
        markers[".NET"] = dotnet_markers

    # Go
    go_runtime_count = len(re.findall(rb"runtime\.\w+", data))
    go_type_count = len(re.findall(rb"type:\.[a-z]", data))
    go_build = data.count(b"go.buildid") + data.count(b"go:buildid")
    if go_runtime_count > 5 or go_type_count > 0 or go_build > 0:
        markers["Go"] = {
            "runtime.*": go_runtime_count,
            "type:.": go_type_count,
            "go.buildid": go_build,
            "goroutine": data.count(b"goroutine"),
        }

    # Rust
    rust_count = (data.count(b"/rustc/") + data.count(b"core::fmt")
                  + data.count(b"core::panicking") + len(re.findall(rb"panicked at", data)))
    if rust_count > 0:
        markers["Rust"] = {"/rustc/ + core::*": rust_count}

    # MinGW/CGo
    mingw = data.count(b"mingw") + data.count(b"__mingw")
    cgo = data.count(b"_cgo_")
    if mingw + cgo > 0:
        markers["MinGW/CGo"] = {"mingw": mingw, "CGo (_cgo_)": cgo}

    # C++ (RTTI class names)
    rtti = len(re.findall(rb"\.?class [A-Za-z_]\w+", data))
    vtable = data.count(b"vtable for ")
    if rtti + vtable > 2:
        markers["C++"] = {"RTTI class refs": rtti, "vtable for": vtable}

    return markers


# ─────────────────────────── ELF parsing ───────────────────────────────────────

def parse_elf_info(data: bytes) -> dict:
    e_class = data[4]       # 1=32-bit, 2=64-bit
    e_machine = struct.unpack_from("<H", data, 18)[0]
    machines = {3: "x86", 62: "x64", 40: "ARM", 183: "ARM64", 8: "MIPS"}
    return {
        "bits": 64 if e_class == 2 else 32,
        "machine": machines.get(e_machine, f"0x{e_machine:04X}"),
        "is_stripped": b".symtab" not in data,
    }


# ─────────────────────────── main triage ───────────────────────────────────────

def triage(path: str, full: bool = False) -> None:
    limit = None if full else 5
    data = Path(path).read_bytes()
    name = Path(path).name
    size = len(data)

    print(f"\n{'='*70}")
    print(f"  TRIAGE: {name}  ({size:,} bytes)")
    print(f"{'='*70}")

    # ── 1. Binary type ─────────────────────────────────────────────────────────
    print("\n[1] Binary Type")
    file_entropy = shannon_entropy(data)

    if is_pe(data):
        hdr = parse_pe_headers(data)
        sections = parse_pe_sections(data, hdr)
        is_dotnet = is_dotnet_pe(data, hdr)
        btype = "PE DLL" if hdr["is_dll"] else "PE EXE"
        if is_dotnet:
            btype += " (.NET managed)"
        print(f"    Type       : {btype}")
        print(f"    Arch       : {hdr['machine']} ({'64-bit' if hdr['is_64'] else '32-bit'})")
        print(f"    Sections   : {hdr['num_sections']}")
        print(f"    Timestamp  : 0x{hdr['timestamp']:08X}")
        is_elf_file = False
    elif is_elf(data):
        elf_info = parse_elf_info(data)
        print(f"    Type       : ELF {elf_info['bits']}-bit")
        print(f"    Arch       : {elf_info['machine']}")
        print(f"    Stripped   : {'yes' if elf_info['is_stripped'] else 'no'}")
        sections = []
        is_elf_file = True
        hdr = None
        is_dotnet = False
    else:
        print(f"    Type       : unknown / raw blob")
        sections = []
        hdr = None
        is_elf_file = False
        is_dotnet = False

    print(f"    File entropy: {file_entropy:.4f}  [{entropy_label(file_entropy)}]")

    # ── 2. Section entropy map ─────────────────────────────────────────────────
    if sections:
        print("\n[2] Sections")
        encrypted_sections = []
        print(f"    {'Name':<12} {'RawSize':>10} {'Entropy':>8}  Classification")
        for sec in sections:
            if sec["rs"] == 0:
                continue
            sdata = data[sec["ro"]:sec["ro"] + sec["rs"]]
            ent = shannon_entropy(sdata)
            stats = byte_distribution_stats(sdata)
            cls = classify_region(ent, stats)
            marker = " ← !" if cls in ("ENCRYPTED", "COMPRESSED") else ""
            print(f"    {sec['name']:<12} {sec['rs']:>10,} {ent:>8.4f}  {cls}{marker}")
            if cls in ("ENCRYPTED", "COMPRESSED"):
                encrypted_sections.append(sec["name"])
        if encrypted_sections:
            print(f"\n    ⚠  High-entropy sections: {', '.join(encrypted_sections)}")
            print("       → likely packed/encrypted; dynamic unpacking required")
    else:
        print("\n[2] Sections: not parsed (non-PE or no section table)")

    # ── 3. Packer heuristics ───────────────────────────────────────────────────
    print("\n[3] Packer / Obfuscation Heuristics")
    hints = []

    # Low import count
    if hdr and is_pe(data):
        imports = parse_imports(data, hdr, sections)
        total_imports = sum(len(fns) for _, fns in imports)
        total_dlls = len(imports)
        if total_dlls < 3 and total_imports < 6:
            hints.append(f"very few imports ({total_dlls} DLLs, {total_imports} functions) → possibly packed")
    else:
        imports = []
        total_imports = 0
        total_dlls = 0

    # UPX
    if b"UPX" in data:
        hints.append("UPX signature found")
    # MPRESS / Themida markers
    for packer in [b"MPRESS", b"Themida", b"VMProtect", b"ASPack", b".nsp0", b".nsp1"]:
        if packer in data:
            hints.append(f"packer marker: {packer.decode()}")

    # High-entropy .text
    if sections:
        text_sec = next((s for s in sections if s["name"] in (".text", "CODE", ".code")), None)
        if text_sec and text_sec["rs"] > 0:
            t_ent = shannon_entropy(data[text_sec["ro"]:text_sec["ro"] + text_sec["rs"]])
            if t_ent > 7.0:
                hints.append(f".text entropy {t_ent:.2f} > 7.0 → encrypted code section")

    if hints:
        for h in hints:
            print(f"    ⚠  {h}")
    else:
        print("    No obvious packing indicators")

    # ── 4. Import analysis (PE only) ────────────────────────────────────────────
    if is_pe(data) and hdr:
        print(f"\n[4] Imports  ({total_dlls} DLLs, {total_imports} functions)")
        for dll, fns in imports[:8]:
            if fns:
                sample = ", ".join(fns[:5])
                more = f" (+{len(fns)-5} more)" if len(fns) > 5 else ""
                print(f"    {dll:<35} {sample}{more}")
            else:
                print(f"    {dll}")

        flagged = flag_imports(imports)
        if flagged["categories"]:
            print(f"\n    Suspicious API categories:")
            for cat, funcs in flagged["categories"].items():
                print(f"    [{cat}] {', '.join(funcs[:6])}")
        if flagged["combos"]:
            print(f"\n    ⚠⚠ Dangerous API combos: {', '.join(flagged['combos'])}")
    else:
        print("\n[4] Imports: N/A (not a PE)")

    # ── 5. Language markers ────────────────────────────────────────────────────
    print("\n[5] Language / Toolchain Markers")
    markers = detect_language_markers(data, is_dotnet=is_dotnet)
    if markers:
        for lang, info in markers.items():
            detail = "  ".join(f"{k}={v}" for k, v in info.items())
            print(f"    [{lang}] {detail}")
    else:
        print("    No recognized language markers (native C/C++ likely, or stripped)")

    # ── 6. String leak scan ────────────────────────────────────────────────────
    print("\n[6] String Leak Scan")

    off_hits = scan_strings_in_data(data, OFFENSIVE_TERMS, "OFFENSIVE", limit or 10)
    if off_hits:
        print(f"    [OFFENSIVE]   {', '.join(off_hits)}" + ("  (…)" if not full and len(off_hits) >= 5 else ""))
    else:
        print("    [OFFENSIVE]   clean")

    comp_hits = scan_strings_in_data(data, COMPILER_ARTIFACTS, "COMPILER", limit or 10)
    if comp_hits:
        print(f"    [COMPILER]    {', '.join(comp_hits)}" + ("  (…)" if not full and len(comp_hits) >= 5 else ""))
    else:
        print("    [COMPILER]    clean")

    dbg_hits = scan_regex_in_data(data, DEBUG_PATTERNS, "DEBUG_PATH", limit or 5)
    if dbg_hits:
        for h in dbg_hits:
            print(f"    [DEBUG_PATH]  {h}")
    else:
        print("    [DEBUG_PATH]  clean")

    rt_api_hits = scan_strings_in_data(data, RUNTIME_API_TARGETS, "RT_API", limit or 10)
    if rt_api_hits:
        print(f"    [RT_API]      {', '.join(rt_api_hits)}" + ("  (…)" if not full and len(rt_api_hits) >= 5 else ""))
    else:
        print("    [RT_API]      clean")

    # ── 7. Summary and next-step recommendation ────────────────────────────────
    print("\n[7] Triage Summary")
    concerns = []

    if any(classify_region(shannon_entropy(data[s["ro"]:s["ro"] + s["rs"]]),
                           byte_distribution_stats(data[s["ro"]:s["ro"] + s["rs"]]))
           in ("ENCRYPTED", "COMPRESSED") for s in sections if s["rs"] > 0):
        concerns.append("packed/encrypted sections → unpack first (x64dbg + Scylla or dump)")

    if flagged.get("combos") if is_pe(data) and hdr else False:
        concerns.append(f"injection combo detected: {', '.join(flagged['combos'])}")

    if markers.get("Go"):
        concerns.append("Go binary → use radare2/ghidra for pclntab function recovery")
    if markers.get("Rust"):
        concerns.append("Rust binary → symbols may be stripped; use ghidra demangler")
    if markers.get(".NET"):
        concerns.append(".NET managed assembly → switch to dnSpy/dnSpyEx + de4dot + ilspycmd workflow")
    if off_hits:
        concerns.append(f"offensive strings: {', '.join(off_hits[:3])}")
    if dbg_hits:
        concerns.append(f"debug/path leaks found")

    if concerns:
        print("    Action items:")
        for c in concerns:
            print(f"    → {c}")
    else:
        print("    No critical concerns — proceed to static analysis")

    print()


def main():
    parser = argparse.ArgumentParser(description="Quick binary triage")
    parser.add_argument("binaries", nargs="+", help="Binary files to triage")
    parser.add_argument("--full", action="store_true", help="Show all string matches")
    args = parser.parse_args()

    for path in args.binaries:
        if not Path(path).is_file():
            print(f"ERROR: not a file: {path}", file=sys.stderr)
            continue
        try:
            triage(path, full=args.full)
        except Exception as e:
            print(f"ERROR triaging {path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
