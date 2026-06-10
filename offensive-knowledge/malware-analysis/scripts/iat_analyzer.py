#!/usr/bin/env python3
"""PE Import Address Table analyzer with suspicious API categorization.
Zero external dependencies — parses PE headers with struct.

Usage:
    python iat_analyzer.py sample.exe [--suspicious-only] [--verbose]

Categories:
  INJECTION — remote thread/code injection APIs
  EVASION   — anti-debug, anti-VM, anti-sandbox APIs
  PROCESS   — process creation and manipulation
  MEMORY    — virtual memory allocation and protection
  CRYPTO    — cryptographic APIs
  NETWORK   — networking and HTTP APIs
"""

import argparse
import struct
import sys
from pathlib import Path

# ── Suspicious API database ──────────────────────────────────────────────────

SUSPICIOUS_APIS = {
    "INJECTION": {
        "CreateRemoteThread", "CreateRemoteThreadEx", "NtCreateThreadEx",
        "RtlCreateUserThread", "QueueUserAPC", "NtQueueApcThread",
        "NtMapViewOfSection", "NtUnmapViewOfSection",
        "WriteProcessMemory", "NtWriteVirtualMemory",
        "SetThreadContext", "NtSetContextThread",
        "ResumeThread", "NtResumeThread", "NtSuspendThread",
    },
    "EVASION": {
        "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
        "NtQueryInformationProcess", "NtQuerySystemInformation",
        "NtSetInformationThread", "OutputDebugStringA", "OutputDebugStringW",
        "GetTickCount", "QueryPerformanceCounter",
        "NtDelayExecution", "SleepEx",
        "NtQueryVirtualMemory", "NtQueryObject",
    },
    "PROCESS": {
        "CreateProcessA", "CreateProcessW", "CreateProcessInternalW",
        "OpenProcess", "NtOpenProcess",
        "TerminateProcess", "NtTerminateProcess",
        "ShellExecuteA", "ShellExecuteW", "ShellExecuteExA", "ShellExecuteExW",
        "WinExec", "CreateProcessAsUserA", "CreateProcessAsUserW",
    },
    "MEMORY": {
        "VirtualAlloc", "VirtualAllocEx", "NtAllocateVirtualMemory",
        "VirtualProtect", "VirtualProtectEx", "NtProtectVirtualMemory",
        "VirtualFree", "VirtualFreeEx",
        "HeapCreate", "RtlAllocateHeap",
    },
    "CRYPTO": {
        "CryptEncrypt", "CryptDecrypt", "CryptCreateHash",
        "CryptHashData", "CryptDeriveKey", "CryptGenKey",
        "CryptAcquireContextA", "CryptAcquireContextW",
        "BCryptEncrypt", "BCryptDecrypt", "BCryptGenerateSymmetricKey",
        "BCryptOpenAlgorithmProvider",
    },
    "NETWORK": {
        "InternetOpenA", "InternetOpenW",
        "InternetOpenUrlA", "InternetOpenUrlW",
        "InternetConnectA", "InternetConnectW",
        "HttpOpenRequestA", "HttpOpenRequestW",
        "HttpSendRequestA", "HttpSendRequestW",
        "InternetReadFile", "URLDownloadToFileA", "URLDownloadToFileW",
        "WSAStartup", "socket", "connect", "send", "recv",
        "getaddrinfo", "gethostbyname",
        "WinHttpOpen", "WinHttpConnect", "WinHttpOpenRequest", "WinHttpSendRequest",
    },
}

# Dangerous combinations that indicate specific attack patterns
DANGEROUS_COMBOS = [
    ({"MEMORY", "INJECTION", "PROCESS"}, "Remote code injection pattern"),
    ({"MEMORY", "INJECTION"}, "Process injection capability"),
    ({"NETWORK", "CRYPTO"}, "Encrypted C2 communication"),
    ({"NETWORK", "PROCESS"}, "Download-and-execute capability"),
    ({"EVASION", "INJECTION"}, "Evasive injection (anti-debug + inject)"),
    ({"CRYPTO", "MEMORY"}, "In-memory decryption (possible payload unpacking)"),
]

# ── Linux suspicious API database ──────────────────────────────────────────

SUSPICIOUS_APIS_LINUX = {
    "INJECTION": {
        "ptrace", "process_vm_writev", "process_vm_readv",
        "__libc_dlopen_mode", "dlopen", "dlsym", "dlclose",
    },
    "EVASION": {
        "ptrace", "prctl", "sysctl",
        "access", "getenv", "uname",
    },
    "PROCESS": {
        "execve", "execvp", "execvpe", "execlp", "execl",
        "system", "popen", "pclose",
        "fork", "vfork", "clone", "clone3",
        "kill", "waitpid", "wait4",
        "posix_spawn", "posix_spawnp",
    },
    "MEMORY": {
        "mmap", "mmap64", "mprotect", "munmap", "mremap", "madvise",
        "brk", "sbrk",
        "shm_open", "shmget", "shmat",
    },
    "CRYPTO": {
        "EVP_EncryptInit_ex", "EVP_DecryptInit_ex",
        "EVP_EncryptUpdate", "EVP_DecryptUpdate",
        "EVP_EncryptFinal_ex", "EVP_DecryptFinal_ex",
        "EVP_CipherInit_ex", "EVP_CIPHER_CTX_new",
        "AES_encrypt", "AES_decrypt", "AES_set_encrypt_key",
        "RSA_public_encrypt", "RSA_private_decrypt",
        "gcry_cipher_encrypt", "gcry_cipher_decrypt",
    },
    "NETWORK": {
        "socket", "connect", "bind", "listen", "accept", "accept4",
        "send", "sendto", "sendmsg", "recv", "recvfrom", "recvmsg",
        "getaddrinfo", "gethostbyname", "gethostbyname_r",
        "inet_aton", "inet_ntoa", "inet_pton", "inet_ntop",
        "curl_easy_init", "curl_easy_perform", "curl_easy_setopt",
        "SSL_connect", "SSL_read", "SSL_write",
    },
}

DANGEROUS_COMBOS_LINUX = [
    ({"MEMORY", "INJECTION"}, "Code injection via ptrace/dlopen + mmap/mprotect"),
    ({"NETWORK", "PROCESS"}, "Download-and-execute or reverse shell capability"),
    ({"NETWORK", "CRYPTO"}, "Encrypted network communication"),
    ({"MEMORY", "PROCESS"}, "Process memory manipulation"),
    ({"EVASION", "NETWORK"}, "Evasive network activity (anti-debug + network)"),
    ({"CRYPTO", "MEMORY"}, "In-memory decryption (possible payload unpacking)"),
]

# ── PE IAT parsing ───────────────────────────────────────────────────────────

def rva_to_offset(rva: int, sections: list[dict]) -> int | None:
    for s in sections:
        if s["rva"] <= rva < s["rva"] + max(s["vsize"], s["raw_size"]):
            return rva - s["rva"] + s["raw_ptr"]
    return None

def read_cstring(data: bytes, offset: int, max_len: int = 256) -> str:
    end = data.find(b"\x00", offset, offset + max_len)
    if end < 0:
        end = offset + max_len
    return data[offset:end].decode("ascii", errors="replace")

def parse_imports(data: bytes) -> tuple[list[dict], list[dict]] | None:
    if data[:2] != b"MZ":
        return None
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
            return None

        coff_off = e_lfanew + 4
        _, num_sections, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, coff_off)
        opt_off = coff_off + 20
        opt_magic = struct.unpack_from("<H", data, opt_off)[0]
        is_64 = opt_magic == 0x20B

        # Parse sections for RVA translation
        sect_off = opt_off + opt_size
        sections = []
        for i in range(num_sections):
            s = sect_off + i * 40
            vsize, rva, raw_size, raw_ptr = struct.unpack_from("<IIII", data, s + 8)
            sections.append({"rva": rva, "vsize": vsize, "raw_size": raw_size, "raw_ptr": raw_ptr})

        # Import directory RVA (data directory index 1)
        if is_64:
            dd_off = opt_off + 120  # PE32+ offset of data directories
        else:
            dd_off = opt_off + 96   # PE32 offset
        import_rva = struct.unpack_from("<I", data, dd_off)[0]
        import_size = struct.unpack_from("<I", data, dd_off + 4)[0]

        if import_rva == 0:
            return [], sections

        import_off = rva_to_offset(import_rva, sections)
        if import_off is None:
            return [], sections

        # Parse import descriptors
        imports = []
        pos = import_off
        while True:
            ilt_rva, _, _, name_rva, _ = struct.unpack_from("<IIIII", data, pos)
            if ilt_rva == 0 and name_rva == 0:
                break
            pos += 20

            dll_offset = rva_to_offset(name_rva, sections)
            dll_name = read_cstring(data, dll_offset) if dll_offset else "unknown"

            # Parse ILT for function names
            ilt_offset = rva_to_offset(ilt_rva, sections)
            if ilt_offset is None:
                imports.append({"dll": dll_name, "functions": []})
                continue

            functions = []
            fpos = ilt_offset
            while True:
                if is_64:
                    entry = struct.unpack_from("<Q", data, fpos)[0]
                    fpos += 8
                    ordinal_flag = 1 << 63
                else:
                    entry = struct.unpack_from("<I", data, fpos)[0]
                    fpos += 4
                    ordinal_flag = 1 << 31

                if entry == 0:
                    break
                if entry & ordinal_flag:
                    functions.append(f"Ordinal_{entry & 0xFFFF}")
                else:
                    hint_off = rva_to_offset(entry & 0x7FFFFFFF, sections)
                    if hint_off:
                        func_name = read_cstring(data, hint_off + 2)
                        functions.append(func_name)
            imports.append({"dll": dll_name, "functions": functions})

        return imports, sections
    except (struct.error, IndexError):
        return None

# ── ELF dynamic symbol parsing ────────────────────────────────────────────

def parse_elf_imports(data: bytes) -> tuple[list[str], list[str]] | None:
    """Parse ELF .dynsym for imported symbols and .dynamic for DT_NEEDED.
    Returns (imported_symbols, needed_libraries) or None if not ELF."""
    if data[:4] != b"\x7fELF":
        return None
    try:
        is_64 = data[4] == 2
        endian = "<" if data[5] == 1 else ">"

        if is_64:
            e_shoff = struct.unpack_from(f"{endian}Q", data, 40)[0]
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(f"{endian}HHH", data, 58)
        else:
            e_shoff = struct.unpack_from(f"{endian}I", data, 32)[0]
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(f"{endian}HHH", data, 46)

        if e_shnum == 0 or e_shoff == 0:
            return [], []

        def read_shdr(idx):
            off = e_shoff + idx * e_shentsize
            sh_name_idx = struct.unpack_from(f"{endian}I", data, off)[0]
            sh_type = struct.unpack_from(f"{endian}I", data, off + 4)[0]
            if is_64:
                sh_offset = struct.unpack_from(f"{endian}Q", data, off + 24)[0]
                sh_size = struct.unpack_from(f"{endian}Q", data, off + 32)[0]
                sh_link = struct.unpack_from(f"{endian}I", data, off + 40)[0]
                sh_entsize = struct.unpack_from(f"{endian}Q", data, off + 56)[0]
            else:
                sh_offset = struct.unpack_from(f"{endian}I", data, off + 16)[0]
                sh_size = struct.unpack_from(f"{endian}I", data, off + 20)[0]
                sh_link = struct.unpack_from(f"{endian}I", data, off + 24)[0]
                sh_entsize = struct.unpack_from(f"{endian}I", data, off + 36)[0]
            return sh_name_idx, sh_type, sh_offset, sh_size, sh_link, sh_entsize

        # Get section name string table
        strtab_hdr = read_shdr(e_shstrndx)
        shstrtab_off = strtab_hdr[2]  # sh_offset

        # Find .dynsym, its linked strtab (.dynstr), and .dynamic
        dynsym_off = dynsym_size = dynsym_entsize = 0
        dynstr_off = 0
        dynamic_off = dynamic_size = dynamic_entsize = 0

        for i in range(e_shnum):
            _, sh_type, sh_offset, sh_size, sh_link, sh_entsize = read_shdr(i)
            if sh_type == 11:  # SHT_DYNSYM
                dynsym_off = sh_offset
                dynsym_size = sh_size
                dynsym_entsize = sh_entsize if sh_entsize else (24 if is_64 else 16)
                # sh_link points to the associated string table (.dynstr)
                _, _, linked_off, _, _, _ = read_shdr(sh_link)
                dynstr_off = linked_off
            elif sh_type == 6:  # SHT_DYNAMIC
                dynamic_off = sh_offset
                dynamic_size = sh_size
                dynamic_entsize = sh_entsize if sh_entsize else (16 if is_64 else 8)

        # Parse imported symbols (st_shndx == SHN_UNDEF and st_name != 0)
        imported = []
        if dynsym_off and dynstr_off:
            pos = dynsym_off
            end = dynsym_off + dynsym_size
            while pos + dynsym_entsize <= end:
                if is_64:
                    st_name = struct.unpack_from(f"{endian}I", data, pos)[0]
                    st_info = data[pos + 4]
                    st_shndx = struct.unpack_from(f"{endian}H", data, pos + 6)[0]
                else:
                    st_name = struct.unpack_from(f"{endian}I", data, pos)[0]
                    st_info = data[pos + 12]
                    st_shndx = struct.unpack_from(f"{endian}H", data, pos + 14)[0]
                pos += dynsym_entsize
                if st_shndx == 0 and st_name != 0:  # SHN_UNDEF = imported
                    func = read_cstring(data, dynstr_off + st_name)
                    if func:
                        imported.append(func)

        # Parse DT_NEEDED from .dynamic
        libraries = []
        if dynamic_off and dynstr_off:
            pos = dynamic_off
            end = dynamic_off + dynamic_size
            while pos + dynamic_entsize <= end:
                if is_64:
                    d_tag = struct.unpack_from(f"{endian}q", data, pos)[0]
                    d_val = struct.unpack_from(f"{endian}Q", data, pos + 8)[0]
                else:
                    d_tag = struct.unpack_from(f"{endian}i", data, pos)[0]
                    d_val = struct.unpack_from(f"{endian}I", data, pos + 4)[0]
                pos += dynamic_entsize
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 1:  # DT_NEEDED
                    lib = read_cstring(data, dynstr_off + d_val)
                    if lib:
                        libraries.append(lib)

        return imported, libraries
    except (struct.error, IndexError):
        return None

# ── Analysis ─────────────────────────────────────────────────────────────────

def categorize_imports(imports: list[dict]) -> dict:
    """Categorize PE imported functions by suspiciousness."""
    findings = {cat: [] for cat in SUSPICIOUS_APIS}
    for entry in imports:
        for func in entry["functions"]:
            for cat, apis in SUSPICIOUS_APIS.items():
                if func in apis:
                    findings[cat].append(f"{entry['dll']}!{func}")
    return {k: v for k, v in findings.items() if v}

def categorize_elf_symbols(symbols: list[str]) -> dict:
    """Categorize ELF imported symbols by suspiciousness."""
    findings = {cat: [] for cat in SUSPICIOUS_APIS_LINUX}
    for func in symbols:
        for cat, apis in SUSPICIOUS_APIS_LINUX.items():
            if func in apis:
                findings[cat].append(func)
    return {k: v for k, v in findings.items() if v}

def check_combos(findings: dict, combos_list: list | None = None) -> list[str]:
    if combos_list is None:
        combos_list = DANGEROUS_COMBOS
    active_cats = set(findings.keys())
    alerts = []
    for required, desc in combos_list:
        if required.issubset(active_cats):
            alerts.append(desc)
    return alerts

# ── Output ───────────────────────────────────────────────────────────────────

def _print_findings(findings: dict, combos: list[str]):
    """Shared display logic for suspicious API findings and risk score."""
    print(f"\n{'─' * 56}")
    print("  Suspicious API Analysis")
    print(f"{'─' * 56}")

    if not findings:
        print("  [CLEAN] No suspicious API imports detected.")
    else:
        total_suspicious = sum(len(v) for v in findings.values())
        print(f"  Suspicious imports: {total_suspicious}")
        for cat, funcs in findings.items():
            print(f"\n  [{cat}] ({len(funcs)} APIs)")
            for f in funcs:
                print(f"    {f}")

    if combos:
        print(f"\n{'─' * 56}")
        print("  Dangerous Combinations Detected")
        print(f"{'─' * 56}")
        for c in combos:
            print(f"  [CRIT] {c}")

    score = sum(len(v) for v in findings.values()) + len(combos) * 5
    if score == 0:
        level = "LOW"
    elif score < 10:
        level = "MODERATE"
    elif score < 20:
        level = "HIGH"
    else:
        level = "CRITICAL"
    print(f"\n  Risk level: {level} (score: {score})")
    print(f"{'=' * 64}")
    return score

def main():
    parser = argparse.ArgumentParser(description="PE/ELF import analyzer with suspicious API detection")
    parser.add_argument("file", help="Path to the PE or ELF binary")
    parser.add_argument("--suspicious-only", action="store_true", help="Show only suspicious imports")
    parser.add_argument("--verbose", action="store_true", help="Show all imports")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = path.read_bytes()

    # Try PE first
    pe_result = parse_imports(data)
    if pe_result is not None:
        imports, _ = pe_result
        total_funcs = sum(len(e["functions"]) for e in imports)

        print("=" * 64)
        print(f"  IAT Analysis — {path.name} [PE]")
        print(f"  DLLs: {len(imports)}  |  Functions: {total_funcs}")
        print("=" * 64)

        if args.verbose:
            for entry in imports:
                print(f"\n  {entry['dll']} ({len(entry['functions'])} imports)")
                for f in entry["functions"]:
                    print(f"    {f}")

        findings = categorize_imports(imports)
        combos = check_combos(findings, DANGEROUS_COMBOS)
        score = _print_findings(findings, combos)
        sys.exit(1 if score >= 10 else 0)

    # Try ELF
    elf_result = parse_elf_imports(data)
    if elf_result is not None:
        symbols, libraries = elf_result

        print("=" * 64)
        print(f"  Import Analysis — {path.name} [ELF]")
        print(f"  Libraries: {len(libraries)}  |  Imported symbols: {len(symbols)}")
        print("=" * 64)

        if libraries:
            print(f"\n  Linked libraries:")
            for lib in libraries:
                print(f"    {lib}")

        if args.verbose:
            print(f"\n  Imported symbols ({len(symbols)}):")
            for s in sorted(symbols):
                print(f"    {s}")

        findings = categorize_elf_symbols(symbols)
        combos = check_combos(findings, DANGEROUS_COMBOS_LINUX)
        score = _print_findings(findings, combos)
        sys.exit(1 if score >= 10 else 0)

    print("[ERROR] Not a valid PE or ELF file.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
