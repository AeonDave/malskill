#!/usr/bin/env python3
"""IOC-focused string extraction, classification, and threat-indicator scoring.
Extracts ASCII and UTF-16 strings, classifies by IOC type, detects suspicious
API resolution targets, anti-analysis indicators, credential material, C2
framework artifacts, crypto wallet addresses, encoded payloads, persistence
mechanisms, and high-entropy blobs. Zero external dependencies.

Usage:
    python string_scanner.py sample.bin [--min-len 6] [--iocs-only] [--json]
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

# ── String extraction ────────────────────────────────────────────────────────

def extract_strings(data: bytes, min_len: int = 6) -> tuple[list[str], list[str]]:
    ascii_pat = re.compile(rb"[\x20-\x7e]{" + str(min_len).encode() + rb",}")
    utf16_pat = re.compile(rb"(?:[\x20-\x7e]\x00){" + str(min_len).encode() + rb",}")
    ascii_strs = [m.group().decode("ascii") for m in ascii_pat.finditer(data)]
    utf16_strs = [m.group().decode("utf-16-le", errors="ignore") for m in utf16_pat.finditer(data)]
    return ascii_strs, utf16_strs

# ── IOC patterns ─────────────────────────────────────────────────────────────

IOC_PATTERNS = {
    # Network indicators
    "URL": re.compile(r"https?://[^\s\"'<>]{4,}"),
    "IP_Address": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
    "IP_Port": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?):\d{1,5}\b"),
    "Domain": re.compile(
        r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|io|ru|cn|xyz|top|info|biz|cc|tk|pw|me|"
        r"online|site|club|dev|app|co|uk|de|fr|jp|br|in|au|ca|onion|i2p|bit|lib|emc)\b",
        re.IGNORECASE,
    ),
    "Onion_Address": re.compile(r"\b[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
    "Email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    "IRC_Channel": re.compile(r"#[a-zA-Z][\w.-]{3,49}\b"),

    # Filesystem / build artifacts
    "Registry_Key": re.compile(
        r"\\?(HKLM|HKCU|HKCR|HKU|HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|HKEY_CLASSES_ROOT|"
        r"HKEY_USERS|HKEY_CURRENT_CONFIG)\\[\w\\-]+",
        re.IGNORECASE,
    ),
    "Windows_Path": re.compile(r"[A-Z]:\\(?:[\w. -]+\\)+[\w. -]+", re.IGNORECASE),
    "Unix_Path": re.compile(r"/(?:usr|etc|tmp|var|home|opt|bin|sbin|dev|proc|sys|lib|root|run)/[\w/.-]+"),
    "PDB_Path": re.compile(r"[A-Z]:\\[\w\\. -]+\.pdb", re.IGNORECASE),
    "UNC_Path": re.compile(r"\\\\[\w.-]+\\[\w$\\.-]+"),

    # Communication / C2 channels
    "Telegram": re.compile(r"api\.telegram\.org/bot[0-9]+:[A-Za-z0-9_-]+|chat_id=\d+", re.IGNORECASE),
    "Discord_Webhook": re.compile(r"discord(?:app)?\.com/api/webhooks/\d+/[\w-]+"),
    "Slack_Webhook": re.compile(r"hooks\.slack\.com/services/T[\w]+/B[\w]+/[\w]+"),
    "Pastebin": re.compile(r"pastebin\.com/(?:raw/)?[A-Za-z0-9]{8}"),
    "UserAgent": re.compile(r"Mozilla/\d\.\d\s*\([^)]+\)", re.IGNORECASE),

    # Crypto wallets
    "Bitcoin_Addr": re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),
    "Bitcoin_Bech32": re.compile(r"\bbc1[ac-hj-np-zAC-HJ-NP-Z02-9]{11,71}\b"),
    "Ethereum_Addr": re.compile(r"\b0x[0-9a-fA-F]{40}\b"),
    "Monero_Addr": re.compile(r"\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b"),

    # Credentials and secrets
    "AWS_Key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "AWS_Secret": re.compile(r"\b[A-Za-z0-9/+=]{40}\b(?=.*aws)", re.IGNORECASE),
    "Private_Key_Header": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    "JWT_Token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "Generic_API_Key": re.compile(r"(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|secret[_-]?key)\s*[:=]\s*['\"]?[\w-]{16,}",
                                  re.IGNORECASE),

    # Hashes (may indicate drop targets, config checksums, known-hash comparison)
    "MD5_Hash": re.compile(r"\b[a-fA-F0-9]{32}\b"),
    "SHA1_Hash": re.compile(r"\b[a-fA-F0-9]{40}\b"),
    "SHA256_Hash": re.compile(r"\b[a-fA-F0-9]{64}\b"),

    # Encoded payloads
    "Base64_Blob": re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    "Hex_Blob": re.compile(r"\b(?:0x)?(?:[0-9a-fA-F]{2}){20,}\b"),
    "PowerShell_EncodedCmd": re.compile(
        r"-(?:enc|encodedcommand)\s+[A-Za-z0-9+/=]{20,}",
        re.IGNORECASE,
    ),

    # Synchronization / named objects
    "Mutex": re.compile(r"(?:Global\\|Local\\)[A-Za-z0-9_-]{4,}"),
    "Named_Pipe": re.compile(r"\\\\.\\pipe\\[\w.-]+"),
    "Mailslot": re.compile(r"\\\\.\\mailslot\\[\w./]+"),
}

# ── Suspicious runtime APIs (grouped by technique) ──────────────────────────

SUSPICIOUS_RUNTIME_APIS: dict[str, set[str]] = {
    "INJECTION": {
        "CreateRemoteThread", "CreateRemoteThreadEx", "NtCreateThreadEx",
        "RtlCreateUserThread", "QueueUserAPC", "NtQueueApcThread",
        "NtQueueApcThreadEx", "NtMapViewOfSection", "NtUnmapViewOfSection",
        "WriteProcessMemory", "NtWriteVirtualMemory",
        "SetThreadContext", "NtSetContextThread", "ResumeThread",
        "SuspendThread", "CreateThread",
    },
    "MEMORY": {
        "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "VirtualProtectEx",
        "VirtualFree", "VirtualQuery", "VirtualQueryEx",
        "NtAllocateVirtualMemory", "NtProtectVirtualMemory",
        "NtReadVirtualMemory", "HeapCreate", "RtlAllocateHeap",
        "MapViewOfFile", "UnmapViewOfFile", "CreateFileMappingA", "CreateFileMappingW",
    },
    "EVASION": {
        "IsDebuggerPresent", "CheckRemoteDebuggerPresent", "OutputDebugStringA",
        "NtQueryInformationProcess", "NtQuerySystemInformation",
        "NtSetInformationThread", "NtClose",
        "GetTickCount", "GetTickCount64", "QueryPerformanceCounter",
        "SetUnhandledExceptionFilter", "AddVectoredExceptionHandler",
        "NtQueryObject", "NtQueryVirtualMemory",
    },
    "PROCESS": {
        "CreateProcessA", "CreateProcessW", "CreateProcessInternalW",
        "ShellExecuteA", "ShellExecuteW", "ShellExecuteExW",
        "WinExec", "NtCreateProcess", "NtCreateProcessEx",
        "OpenProcess", "NtOpenProcess", "TerminateProcess",
        "CreateProcessAsUserA", "CreateProcessAsUserW",
        "CreateProcessWithLogonW", "CreateProcessWithTokenW",
    },
    "LOADER": {
        "GetProcAddress", "GetModuleHandleA", "GetModuleHandleW",
        "LoadLibraryA", "LoadLibraryW", "LoadLibraryExA", "LoadLibraryExW",
        "LdrLoadDll", "LdrGetProcedureAddress",
        "NtCreateSection", "NtOpenSection",
    },
    "CRYPTO": {
        "CryptEncrypt", "CryptDecrypt", "CryptCreateHash", "CryptHashData",
        "CryptDeriveKey", "CryptGenKey", "CryptAcquireContextA",
        "BCryptEncrypt", "BCryptDecrypt", "BCryptGenerateSymmetricKey",
        "BCryptOpenAlgorithmProvider", "BCryptCreateHash",
        "NCryptEncrypt", "NCryptDecrypt",
    },
    "NETWORK": {
        "InternetOpenA", "InternetOpenW",
        "InternetOpenUrlA", "InternetOpenUrlW",
        "InternetConnectA", "InternetConnectW",
        "HttpOpenRequestA", "HttpOpenRequestW",
        "HttpSendRequestA", "HttpSendRequestW",
        "InternetReadFile", "InternetWriteFile",
        "URLDownloadToFileA", "URLDownloadToFileW",
        "WinHttpOpen", "WinHttpConnect", "WinHttpOpenRequest",
        "WinHttpSendRequest", "WinHttpReceiveResponse",
        "WSAStartup", "socket", "connect", "send", "recv",
        "bind", "listen", "accept", "getaddrinfo",
        "DnsQuery_A", "DnsQuery_W",
    },
    "PERSISTENCE": {
        "RegOpenKeyExA", "RegOpenKeyExW", "RegSetValueExA", "RegSetValueExW",
        "RegCreateKeyExA", "RegCreateKeyExW", "RegDeleteValueA", "RegDeleteValueW",
        "CreateServiceA", "CreateServiceW", "StartServiceA", "StartServiceW",
        "ChangeServiceConfigA", "ChangeServiceConfigW",
        "SHGetFolderPathA", "SHGetFolderPathW",
    },
    "TOKEN_PRIV": {
        "OpenProcessToken", "AdjustTokenPrivileges", "LookupPrivilegeValueA",
        "DuplicateTokenEx", "ImpersonateLoggedOnUser", "SetTokenInformation",
        "NtOpenProcessToken", "NtAdjustPrivilegesToken",
        "LogonUserA", "LogonUserW",
    },
    "DEFENSE_TAMPERING": {
        "AmsiScanBuffer", "AmsiInitialize", "AmsiOpenSession",
        "EtwEventWrite", "NtTraceEvent", "EtwNotificationRegister",
        "NtSetInformationProcess",
    },
    "CLIPBOARD_KEYLOG": {
        "SetWindowsHookExA", "SetWindowsHookExW",
        "GetAsyncKeyState", "GetKeyState", "GetKeyboardState",
        "OpenClipboard", "GetClipboardData", "SetClipboardData",
        "RegisterHotKey", "GetRawInputData",
    },
    "SCREENSHOT_CAPTURE": {
        "BitBlt", "GetDC", "GetWindowDC", "CreateCompatibleDC",
        "CreateCompatibleBitmap", "GetDIBits",
        "capCreateCaptureWindowA", "capGetDriverDescriptionA",
    },
    "FILE_OPS": {
        "DeleteFileA", "DeleteFileW", "MoveFileA", "MoveFileW",
        "CopyFileA", "CopyFileW", "CreateFileA", "CreateFileW",
        "ReadFile", "WriteFile", "NtCreateFile", "NtDeleteFile",
        "FindFirstFileA", "FindFirstFileW", "FindNextFileA", "FindNextFileW",
    },
    "WMI_COM": {
        "CoCreateInstance", "CoInitializeEx", "CoInitializeSecurity",
        "CLSIDFromString", "CoGetClassObject",
    },
}

# Flatten for fast membership lookup
_ALL_SUSPICIOUS_APIS: set[str] = set()
for _apis in SUSPICIOUS_RUNTIME_APIS.values():
    _ALL_SUSPICIOUS_APIS |= _apis

# ── Anti-analysis indicators ─────────────────────────────────────────────────

ANTI_ANALYSIS_STRINGS: dict[str, list[str]] = {
    "VM_Detection": [
        "VMware", "VirtualBox", "VBOX", "QEMU", "Xen", "Hyper-V",
        "Parallels", "vmsrvc", "vmtoolsd", "vmwaretray",
        "VBoxService", "VBoxTray", "vmware-vmx",
        "Red Hat VirtIO", "KVMKVMKVM",
        "sbiedll.dll",  # Sandboxie
    ],
    "Sandbox_Detection": [
        "SbieDll", "Sandboxie", "cuckoomon", "cuckoo",
        "joe sandbox", "anubis", "threatexpert",
        "wireshark", "fiddler", "charles",
        "procmon", "procexp", "filemon", "regmon",
        "ollydbg", "x64dbg", "x32dbg", "windbg", "ida ",
        "idaq", "idaq64", "immunity", "lordpe",
        "peid", "die.exe", "pestudio",
        "sample.exe", "malware", "virus", "sandbox",
        "triage", "analysis.exe",
        "john doe", "peter miller", "phil",  # common sandbox usernames
        "CurrentUser",  # sandbox user checks
    ],
    "Debugger_Detection": [
        "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
        "NtQueryInformationProcess", "ProcessDebugPort",
        "ProcessDebugObjectHandle", "ProcessDebugFlags",
        "OutputDebugString", "UnhandledExceptionFilter",
        "CloseHandle",  # used with invalid handle to detect debuggers
        "INT 2D", "INT 3", "RDTSC",
        "NtSetInformationThread", "ThreadHideFromDebugger",
    ],
    "Sleep_Evasion": [
        "GetTickCount", "GetTickCount64", "QueryPerformanceCounter",
        "NtDelayExecution", "timeGetTime",
        "GetSystemTimeAsFileTime", "NtQueryPerformanceCounter",
    ],
}

# ── C2 framework artifacts ───────────────────────────────────────────────────

C2_ARTIFACTS: dict[str, list[str]] = {
    "Cobalt_Strike": [
        "beacon.dll", "beacon.x64.dll",
        "%APPDATA%", "\\pipe\\msagent_",
        "ReflectiveLoader", "sleeptime",
        "%windir%\\sysnative", "BlockDLLs",
        "\\pipe\\status_", "\\pipe\\postex_",
        "Content-Type: application/octet-stream",
    ],
    "Metasploit": [
        "meterpreter", "metsrv", "stdapi",
        "reverse_tcp", "reverse_http", "reverse_https",
        "bind_tcp", "shell_reverse_tcp",
        "payload/", "exploit/", "auxiliary/",
        "metasploit", "LHOST", "LPORT", "RHOST",
    ],
    "Sliver": [
        "sliverpb", "sliver", "implant",
        "ghost.pb.go", "pivot.pb.go",
        "protobuf", "wg-key",
    ],
    "AsyncRAT": [
        "AsyncClient", "AsyncRAT", "StubConfig",
        "Pastebin", "HWID", "Anti_Process",
        "install_folder", "install_file",
    ],
    "QuasarRAT": [
        "Quasar.Client", "Quasar.Common",
        "GetSystemInfo", "DoUploadAndExecute",
        "DoDownloadAndExecute", "DoShellExecute",
    ],
    "PoshC2": [
        "poshc2", "dropper", "implant",
        "daisy", "fcomm",
    ],
    "Covenant": [
        "Grunt", "GruntHTTP", "GruntSMB",
        "Covenant", "Elite",
    ],
}

# ── Persistence indicators ───────────────────────────────────────────────────

PERSISTENCE_INDICATORS: list[str] = [
    # Registry run keys
    "CurrentVersion\\Run", "CurrentVersion\\RunOnce",
    "CurrentVersion\\RunServices", "CurrentVersion\\RunServicesOnce",
    "CurrentVersion\\Policies\\Explorer\\Run",
    "CurrentVersion\\Explorer\\Shell Folders",
    "CurrentVersion\\Explorer\\User Shell Folders",
    "Environment\\UserInitMprLogonScript",
    "CurrentVersion\\Winlogon",
    "CurrentVersion\\Windows\\load",
    "CurrentVersion\\Windows\\run",
    # Scheduled tasks / services
    "schtasks", "at.exe", "sc create", "sc config",
    "New-ScheduledTask", "Register-ScheduledTask",
    # Startup folders
    "\\Startup\\", "\\Start Menu\\Programs\\Startup",
    # COM hijack
    "InprocServer32", "LocalServer32",
    "TreatAs", "ProgID",
    # Image File Execution Options
    "Image File Execution Options",
    # WMI persistence
    "CommandLineEventConsumer", "ActiveScriptEventConsumer",
    "__EventFilter", "__FilterToConsumerBinding",
    # AppInit_DLLs
    "AppInit_DLLs", "LoadAppInit_DLLs",
    # DLL search order
    "KnownDLLs",
    # Boot/logon
    "BootExecute", "Userinit", "Shell",
    # Accessibility features (Image File Execution Options targets)
    "sethc.exe", "utilman.exe", "osk.exe", "narrator.exe", "magnify.exe",
]

# ── Suspicious keywords (expanded) ──────────────────────────────────────────

SUSPICIOUS_KEYWORDS: set[str] = {
    # Tools and frameworks
    "mimikatz", "metasploit", "cobalt", "beacon", "meterpreter",
    "powersploit", "bloodhound", "rubeus", "seatbelt",
    "lazagne", "kekeo", "empire", "crackmapexec",
    # Techniques
    "shellcode", "payload", "inject", "keylog", "screenshot",
    "password", "credential", "ransomware", "encrypt", "decrypt",
    "c2", "callback", "exfil", "persist", "elevat", "privilege",
    "dump", "harvest", "lateral", "pivot", "tunnel",
    "phishing", "dropper", "loader", "stager", "implant",
    # Evasion
    "unhook", "syscall", "ntdll", "amsi", "etw", "bypass",
    "obfuscat", "packer", "crypter", "stub", "hollow",
    "reflective", "process_ghost", "doppelgäng",
    # Data theft
    "wallet", "bitcoin", "crypto", "cookie", "autofill",
    "browser", "chrome", "firefox", "telegram", "discord",
    "steam", "token", "session",
    # Privilege / UAC
    "seimpersonate", "sedebug", "setcb", "uac",
    "getsystem", "hashdump", "lsass", "sam",
    # Destruction / ransom
    "vssadmin", "bcdedit", "wbadmin", "wmic shadowcopy",
    "delete shadows", ".onion", "tor2web",
    "readme.txt", "decrypt_files", "your files",
    "recovery_key", "ransom_note",
}

# ── Encoding / obfuscation markers ──────────────────────────────────────────

ENCODING_MARKERS: dict[str, re.Pattern] = {
    "PowerShell_Encoded": re.compile(
        r"powershell.*-(?:enc|encodedcommand)\s+[A-Za-z0-9+/=]{20,}",
        re.IGNORECASE,
    ),
    "PowerShell_Bypass": re.compile(
        r"(?:bypass|unrestricted|hidden|noprofile|noexit|noni|downloadstring|"
        r"invoke-expression|iex|downloadfile|webclient|net\.webclient)",
        re.IGNORECASE,
    ),
    "WScript_Shell": re.compile(
        r"WScript\.Shell|Shell\.Application|Scripting\.FileSystemObject",
        re.IGNORECASE,
    ),
    "CMD_Exec": re.compile(
        r"cmd(?:\.exe)?\s+/[ckq]\s+",
        re.IGNORECASE,
    ),
    "Certutil_Decode": re.compile(
        r"certutil.*-(?:decode|urlcache)",
        re.IGNORECASE,
    ),
    "BitsAdmin": re.compile(
        r"bitsadmin.*(?:transfer|create|addfile)",
        re.IGNORECASE,
    ),
    "MSHTA": re.compile(
        r"mshta\s+(?:vbscript|javascript|http)",
        re.IGNORECASE,
    ),
    "Rundll32_Exec": re.compile(
        r"rundll32(?:\.exe)?\s+[\w\\,.#]+",
        re.IGNORECASE,
    ),
    "Regsvr32_Exec": re.compile(
        r"regsvr32.*(?:/[suin]+|scrobj|http)",
        re.IGNORECASE,
    ),
}

# ── Classification ───────────────────────────────────────────────────────────

def _entropy(s: str) -> float:
    """Shannon entropy of a string."""
    if len(s) < 2:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((n / length) * math.log2(n / length) for n in freq.values())


def classify_strings(all_strings: list[str]) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    combined = "\n".join(all_strings)

    # IOC pattern matching
    for category, pattern in IOC_PATTERNS.items():
        matches = sorted(set(pattern.findall(combined)))
        if matches:
            results[category] = matches

    # Runtime API resolution targets (grouped by technique)
    for technique, api_set in SUSPICIOUS_RUNTIME_APIS.items():
        hits = sorted({s for s in all_strings if s in api_set})
        if hits:
            results[f"API_{technique}"] = hits

    # Anti-analysis indicators
    for category, indicators in ANTI_ANALYSIS_STRINGS.items():
        hits = sorted({
            ind for ind in indicators
            if any(ind.lower() in s.lower() for s in all_strings)
        })
        if hits:
            results[f"Anti_{category}"] = hits

    # C2 framework artifacts
    for framework, markers in C2_ARTIFACTS.items():
        hits = sorted({
            m for m in markers
            if any(m.lower() in s.lower() for s in all_strings)
        })
        if hits:
            results[f"C2_{framework}"] = hits

    # Persistence indicators
    pers_hits = sorted({
        p for p in PERSISTENCE_INDICATORS
        if any(p.lower() in s.lower() for s in all_strings)
    })
    if pers_hits:
        results["Persistence"] = pers_hits

    # Encoding / obfuscation markers
    for marker_name, pattern in ENCODING_MARKERS.items():
        hits = sorted(set(pattern.findall(combined)))
        if hits:
            results[f"Exec_{marker_name}"] = hits

    # Suspicious keywords
    kw_hits = sorted({
        kw for kw in SUSPICIOUS_KEYWORDS
        if any(kw.lower() in s.lower() for s in all_strings)
    })
    if kw_hits:
        results["Suspicious_Keyword"] = kw_hits

    # High-entropy strings (potential encrypted/encoded data)
    high_ent = sorted({
        s for s in all_strings
        if len(s) >= 20 and _entropy(s) > 4.5
        and not s.startswith("-----")  # skip PEM headers
    })
    if high_ent:
        results["High_Entropy_String"] = high_ent[:50]

    return results

# ── Risk scoring ─────────────────────────────────────────────────────────────

# Categories weighted by detection/threat significance
_CATEGORY_WEIGHTS: dict[str, int] = {
    "URL": 3, "IP_Port": 3, "Onion_Address": 5, "IP_Address": 2,
    "Domain": 2, "Email": 1, "IRC_Channel": 2,
    "Registry_Key": 1, "Windows_Path": 1, "Unix_Path": 1,
    "PDB_Path": 2, "UNC_Path": 2,
    "Telegram": 5, "Discord_Webhook": 5, "Slack_Webhook": 5,
    "Pastebin": 3, "UserAgent": 1,
    "Bitcoin_Addr": 4, "Bitcoin_Bech32": 4, "Ethereum_Addr": 4, "Monero_Addr": 4,
    "AWS_Key": 5, "AWS_Secret": 5, "Private_Key_Header": 5,
    "JWT_Token": 4, "Generic_API_Key": 4,
    "MD5_Hash": 1, "SHA1_Hash": 1, "SHA256_Hash": 1,
    "Base64_Blob": 2, "Hex_Blob": 2,
    "PowerShell_EncodedCmd": 5,
    "Mutex": 3, "Named_Pipe": 3, "Mailslot": 3,
    "Persistence": 4, "Suspicious_Keyword": 2,
    "High_Entropy_String": 1,
}

# Patterns for prefix-based weight lookup
_PREFIX_WEIGHTS: dict[str, int] = {
    "API_INJECTION": 5, "API_EVASION": 4, "API_DEFENSE_TAMPERING": 5,
    "API_TOKEN_PRIV": 4, "API_CLIPBOARD_KEYLOG": 4, "API_SCREENSHOT_CAPTURE": 3,
    "API_LOADER": 2, "API_MEMORY": 3, "API_PROCESS": 3,
    "API_CRYPTO": 3, "API_NETWORK": 3, "API_PERSISTENCE": 3,
    "API_FILE_OPS": 1, "API_WMI_COM": 3,
    "Anti_VM_Detection": 4, "Anti_Sandbox_Detection": 4,
    "Anti_Debugger_Detection": 4, "Anti_Sleep_Evasion": 3,
    "C2_": 5, "Exec_": 4,
}


def compute_risk_score(classified: dict[str, list[str]]) -> tuple[int, str]:
    """Return (score, severity) based on weighted IOC categories."""
    score = 0
    for category, values in classified.items():
        weight = _CATEGORY_WEIGHTS.get(category, 0)
        if weight == 0:
            # Try prefix match
            for prefix, w in _PREFIX_WEIGHTS.items():
                if category.startswith(prefix):
                    weight = w
                    break
            else:
                weight = 2  # default weight for unknown categories
        score += weight * min(len(values), 10)  # cap per-category contribution

    if score >= 80:
        return score, "CRITICAL"
    if score >= 40:
        return score, "HIGH"
    if score >= 15:
        return score, "MEDIUM"
    if score > 0:
        return score, "LOW"
    return 0, "CLEAN"

# ── Output ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IOC-focused string extraction and classification")
    parser.add_argument("file", help="Path to sample binary")
    parser.add_argument("--min-len", type=int, default=6, help="Minimum string length (default: 6)")
    parser.add_argument("--iocs-only", action="store_true", help="Show only classified IOCs, skip raw strings")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output as JSON")
    args = parser.parse_args()

    # Handle Windows console encoding
    if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    path = Path(args.file)
    if not path.is_file():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = path.read_bytes()
    ascii_strs, utf16_strs = extract_strings(data, args.min_len)
    all_strs = ascii_strs + utf16_strs
    classified = classify_strings(all_strs)
    risk_score, severity = compute_risk_score(classified)

    if args.json_out:
        output = {
            "file": str(path),
            "total_strings": len(all_strs),
            "ascii_count": len(ascii_strs),
            "utf16_count": len(utf16_strs),
            "risk_score": risk_score,
            "severity": severity,
            "iocs": classified,
        }
        print(json.dumps(output, indent=2))
        return

    print("=" * 64)
    print(f"  String Scanner — {path.name}")
    print(f"  ASCII: {len(ascii_strs)}  |  UTF-16: {len(utf16_strs)}  |  Total: {len(all_strs)}")
    print(f"  Risk Score: {risk_score} ({severity})")
    print("=" * 64)

    if not args.iocs_only:
        if len(all_strs) > 300:
            print(f"\n  (showing first 300 of {len(all_strs)} strings)")
            for s in all_strs[:300]:
                print(f"    {s}")
        else:
            for s in all_strs:
                print(f"    {s}")

    print(f"\n{'─' * 56}")
    print("  IOC Classification")
    print(f"{'─' * 56}")

    if not classified:
        print("  No IOC patterns detected.")
    else:
        for category, values in classified.items():
            print(f"\n  [{category}] ({len(values)} found)")
            for v in values[:30]:
                print(f"    {v}")
            if len(values) > 30:
                print(f"    ... and {len(values) - 30} more")

    total_iocs = sum(len(v) for v in classified.values())
    print(f"\n  Total IOCs: {total_iocs}")
    print(f"  Risk Score: {risk_score} ({severity})")
    print(f"{'=' * 64}")

    sys.exit(1 if total_iocs > 0 else 0)

if __name__ == "__main__":
    main()
