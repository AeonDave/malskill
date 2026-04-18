# Tokens & Privileges

Every thread runs under a security context represented by an access token. Tokens encode the identity (user SID, group SIDs), the set of privileges enabled/available, the integrity level, and auxiliary attributes (restricted SIDs, claims, AppContainer info). Every access check the kernel performs against a securable object uses the token of the caller. Offensive primitives — stealing another process's context, elevating through impersonation, enabling `SeDebugPrivilege` to open PROCESS_ALL_ACCESS handles — are all token operations. This reference covers the structure, the syscall surface, the privilege semantics, and the audit events generated.

## TOKEN structure (kernel)

Undocumented but stable layout (`nt!_TOKEN`). Offsets vary between builds — use symbols when precision matters.

| Field | Purpose |
|---|---|
| `TokenSource` | SOURCE_NAME and LUID tying token to logon session |
| `TokenType` | 1 = primary, 2 = impersonation |
| `ImpersonationLevel` | Anonymous/Identification/Impersonation/Delegation |
| `TokenFlags` | HAS_TRAVERSE_PRIVILEGE, HAS_BACKUP_PRIVILEGE, IS_FILTERED, IS_RESTRICTED, LOWBOX, etc. |
| `SessionId` | Terminal session |
| `UserAndGroupCount` / `UserAndGroups` | SID_AND_ATTRIBUTES[0] is the user; rest are groups |
| `PrivilegeCount` / `Privileges` | LUID_AND_ATTRIBUTES array |
| `AuthenticationId` (LUID) | Matches logon session LUID in `lsass` |
| `ParentTokenId` | Used for UAC filtered-token linking |
| `IntegrityLevelIndex` | Index into UserAndGroups pointing at the integrity SID |
| `MandatoryPolicy` | NO_WRITE_UP / NEW_PROCESS_MIN |
| `LogonSession` | Pointer to SEP_LOGON_SESSION_REFERENCES |
| `OriginatingLogonSession` | LUID of originating logon (different from Authentication for impersonation) |
| `SidHash` / `RestrictedSidHash` | Accelerator structures for access checks |
| `PackageSid` / `Capabilities` / `LowboxNumberEntry` | AppContainer state |
| `TrustLevelSid` | Protected process trust level (PPL encoding) |

Userland equivalents returned by `NtQueryInformationToken`:

| Class | Structure |
|---|---|
| `TokenUser` | `TOKEN_USER { SID_AND_ATTRIBUTES User }` |
| `TokenGroups` | `TOKEN_GROUPS { DWORD GroupCount; SID_AND_ATTRIBUTES Groups[] }` |
| `TokenPrivileges` | `TOKEN_PRIVILEGES { DWORD PrivilegeCount; LUID_AND_ATTRIBUTES Privileges[] }` |
| `TokenOwner` | `TOKEN_OWNER { PSID Owner }` (default DACL owner) |
| `TokenPrimaryGroup` | `TOKEN_PRIMARY_GROUP { PSID PrimaryGroup }` |
| `TokenDefaultDacl` | ACL applied to new objects |
| `TokenSource` | `TOKEN_SOURCE { CHAR SourceName[8]; LUID SourceIdentifier }` |
| `TokenType` | `TOKEN_TYPE` enum |
| `TokenImpersonationLevel` | `SECURITY_IMPERSONATION_LEVEL` |
| `TokenStatistics` | `TOKEN_STATISTICS` with AuthenticationId, ExpirationTime, DynamicCharged, etc. |
| `TokenRestrictedSids` | Restricted SID list (for restricted/sandboxed tokens) |
| `TokenSessionId` | DWORD |
| `TokenGroupsAndPrivileges` | Bulk query |
| `TokenSessionReference` | Private |
| `TokenSandBoxInert` | BOOL |
| `TokenOrigin` | `TOKEN_ORIGIN { LUID OriginatingLogonSession }` |
| `TokenElevationType` | `TokenElevationTypeDefault/Full/Limited` |
| `TokenLinkedToken` | `TOKEN_LINKED_TOKEN { HANDLE LinkedToken }` — the other half of a UAC split |
| `TokenElevation` | `TOKEN_ELEVATION { DWORD TokenIsElevated }` |
| `TokenHasRestrictions` | BOOL |
| `TokenAccessInformation` | Heavy composite |
| `TokenVirtualizationAllowed` / `TokenVirtualizationEnabled` | UAC file/registry virtualization |
| `TokenIntegrityLevel` | `TOKEN_MANDATORY_LABEL { SID_AND_ATTRIBUTES Label }` |
| `TokenUIAccess` | UIPI bypass bit |
| `TokenMandatoryPolicy` | `TOKEN_MANDATORY_POLICY { DWORD Policy }` |
| `TokenLogonSid` | Logon SID |
| `TokenIsAppContainer` | BOOL |
| `TokenCapabilities` | List |
| `TokenAppContainerSid` | Package SID |
| `TokenAppContainerNumber` | DWORD |
| `TokenUserClaimAttributes` / `TokenDeviceClaimAttributes` / `TokenDeviceGroups` | AD claims |
| `TokenProcessTrustLevel` | Protected process trust SID |
| `TokenPrivateNameSpace` | BOOL |
| `TokenSingletonAttributes` | Claims on the token itself |
| `TokenBnoIsolation` | Base named object isolation prefix |

## SID structure

```c
typedef struct _SID {
    BYTE  Revision;                  // 1
    BYTE  SubAuthorityCount;         // <= 15
    SID_IDENTIFIER_AUTHORITY IdentifierAuthority;  // 6-byte big-endian
    DWORD SubAuthority[SubAuthorityCount];
} SID;
```

Text form `S-R-IA-SA1-SA2-...`. Common authorities:

| Value | Authority | Notes |
|---|---|---|
| 0 | NULL | S-1-0-0 Nobody |
| 1 | WORLD | S-1-1-0 Everyone |
| 2 | LOCAL | S-1-2-0 local logon |
| 3 | CREATOR | S-1-3-0 CREATOR_OWNER |
| 5 | NT | S-1-5-* — logon sessions, well-knowns, machine/user SIDs |
| 16 | MANDATORY | integrity labels |
| 18 | AppContainer | package SIDs begin S-1-15-2-* |

Well-known NT authority SIDs:

| SID | Meaning |
|---|---|
| S-1-5-18 | LocalSystem |
| S-1-5-19 | LocalService |
| S-1-5-20 | NetworkService |
| S-1-5-32-544 | BUILTIN\\Administrators |
| S-1-5-32-545 | BUILTIN\\Users |
| S-1-5-32-555 | BUILTIN\\Remote Desktop Users |
| S-1-5-7 | Anonymous |
| S-1-5-11 | Authenticated Users |
| S-1-5-15 | This Organization |
| S-1-5-17 | IUSR |
| S-1-5-21-<domain>-500 | Built-in Administrator |
| S-1-5-21-<domain>-501 | Guest |
| S-1-5-21-<domain>-512 | Domain Admins |

Integrity levels (authority 16):

| SID | Level | RID | Value |
|---|---|---|---|
| S-1-16-0 | Untrusted | 0x0000 | 0 |
| S-1-16-4096 | Low | 0x1000 | 4096 |
| S-1-16-8192 | Medium | 0x2000 | 8192 |
| S-1-16-8448 | Medium-Plus | 0x2100 | 8448 |
| S-1-16-12288 | High | 0x3000 | 12288 |
| S-1-16-16384 | System | 0x4000 | 16384 |
| S-1-16-20480 | Protected Process | 0x5000 | 20480 |
| S-1-16-28672 | Secure Process | 0x7000 | 28672 |

## Mandatory integrity control (MIC)

Every token and every securable object carries an integrity label. A subject at IL=X can open an object whose label is L for:

- **Read**: requires subject IL >= L unless `NO_READ_UP` is clear (default allows read-up).
- **Write**: requires subject IL >= L (mandatory `NO_WRITE_UP`).
- **Execute**: requires subject IL >= L when `NO_EXECUTE_UP` is set.

UIPI (User Interface Privilege Isolation) layers on top: Medium-IL processes cannot send most window messages to High-IL processes (exceptions: `WM_NULL`, `WM_MOVE`, `WM_SIZE`, `WM_GETTEXT`, `WM_GETHOTKEY`, `WM_GETICON`, `WM_RENDERFORMAT`, etc., plus messages added via `ChangeWindowMessageFilter`). UAC elevation bumps IL from Medium to High. `UIAccess=1` binaries can bypass UIPI (accessibility tools).

## Privileges

Privileges are per-token LUIDs paired with attribute bits:

| Attribute | Meaning |
|---|---|
| `SE_PRIVILEGE_ENABLED_BY_DEFAULT` (0x1) | Initially enabled |
| `SE_PRIVILEGE_ENABLED` (0x2) | Currently enabled (checked at access time) |
| `SE_PRIVILEGE_REMOVED` (0x4) | Permanently stripped (cannot be re-added) |
| `SE_PRIVILEGE_USED_FOR_ACCESS` (0x80000000) | Set after use, audited |

High-value privileges for offensive work:

| Constant | What it grants |
|---|---|
| `SeDebugPrivilege` | `OpenProcess`/`OpenThread` with ALL_ACCESS on almost any non-PPL process; read/write `\Device\PhysicalMemory` indirectly via some APIs; attach debugger |
| `SeImpersonatePrivilege` | `SetThreadToken` / `ImpersonateLoggedOnUser` with tokens not derivable from current context — the core of Potato-family escalation |
| `SeAssignPrimaryTokenPrivilege` | `CreateProcessAsUser` / `CreateProcessWithTokenW` with an arbitrary token (usually paired with SeImpersonate) |
| `SeTcbPrivilege` | "Act as part of the OS" — required for `LogonUser` with arbitrary credentials into an interactive session, and some token-manipulation operations like `LsaLogonUser` with `MSV1_0_S4U_LOGON` into privileged packages |
| `SeLoadDriverPrivilege` | `NtLoadDriver` — load a kernel driver (BYOVD pivot) |
| `SeBackupPrivilege` | Read-any-file regardless of DACL (opens with `FILE_FLAG_BACKUP_SEMANTICS` and `READ_CONTROL|ACCESS_SYSTEM_SECURITY`) — dumps `SAM`/`SECURITY`/`SYSTEM` hives |
| `SeRestorePrivilege` | Write-any-file + set owner to any SID — file-system pivots |
| `SeTakeOwnershipPrivilege` | Change Owner in security descriptor |
| `SeSecurityPrivilege` | Read/write SACL, read security event log |
| `SeManageVolumePrivilege` | Needed for Volume Shadow operations, disk defrag |
| `SeCreateTokenPrivilege` | Only granted to LSA — lets caller construct arbitrary tokens via `NtCreateToken` |
| `SeSystemEnvironmentPrivilege` | Read/write firmware env variables |
| `SeShutdownPrivilege` / `SeRemoteShutdownPrivilege` | Shutdown/reboot |
| `SeChangeNotifyPrivilege` | Bypass traverse checking — default for all users, if removed makes the token brutally slow |
| `SeUndockPrivilege` / `SeTimeZonePrivilege` / `SeIncreaseWorkingSetPrivilege` | Low value |
| `SeIncreaseBasePriorityPrivilege` / `SeIncreaseQuotaPrivilege` | Useful for Tcb-adjacent chains |
| `SeProfileSingleProcessPrivilege` / `SeSystemProfilePrivilege` | Performance profiling — rarely offensively useful |
| `SeTrustedCredManAccessPrivilege` | Access credential manager programmatically |
| `SeRelabelPrivilege` | Change integrity label on an object to higher than own — virtually never granted |
| `SeDelegateSessionUserImpersonatePrivilege` | Impersonate across sessions — useful in RDP scenarios |
| `SeAuditPrivilege` | `ReportEvent` into Security log directly — SYSTEM-only |

LUID values are assigned at boot and are machine-local; never hardcode. Always resolve:

```c
LUID luid;
LookupPrivilegeValueW(NULL, L"SeDebugPrivilege", &luid);
```

Or parse `TokenPrivileges` once and cache.

## Token types and impersonation

A **primary** token is attached to a process (`EPROCESS->Token`). An **impersonation** token is attached to a thread (`ETHREAD->ClientSecurity`) and temporarily overrides the primary token for access checks made by that thread.

Impersonation levels:

| Level | Value | Behavior |
|---|---|---|
| `SecurityAnonymous` | 0 | Server cannot obtain user identity — access checks fail for most operations |
| `SecurityIdentification` | 1 | Server can query identity but cannot act as the user — no token operations on other objects |
| `SecurityImpersonation` | 2 | Server can act as user on the local machine — the useful level |
| `SecurityDelegation` | 3 | Server can act as user across network hops (Kerberos delegation) — requires `TRUSTED_FOR_DELEGATION` flag on the account |

The difference between impersonation and delegation matters for relay/coercion attacks: only delegation-level tokens let you pivot via SMB/RPC to remote systems under that identity.

A thread with an impersonation token is said to be "impersonating." `NtAccessCheck` and all security-relevant syscalls use the thread token when present, else fall back to the process primary token.

## Token-manipulation syscall surface

### Open

```c
NTSTATUS NtOpenProcessToken(
    HANDLE          ProcessHandle,
    ACCESS_MASK     DesiredAccess,   // TOKEN_QUERY | TOKEN_ADJUST_PRIVILEGES etc.
    PHANDLE         TokenHandle
);

NTSTATUS NtOpenProcessTokenEx(
    HANDLE          ProcessHandle,
    ACCESS_MASK     DesiredAccess,
    ULONG           HandleAttributes,
    PHANDLE         TokenHandle
);

NTSTATUS NtOpenThreadToken(
    HANDLE          ThreadHandle,
    ACCESS_MASK     DesiredAccess,
    BOOLEAN         OpenAsSelf,      // TRUE = use process primary for access check
    PHANDLE         TokenHandle
);
```

Access rights:

| Constant | Bit |
|---|---|
| `TOKEN_ASSIGN_PRIMARY` | 0x0001 |
| `TOKEN_DUPLICATE` | 0x0002 |
| `TOKEN_IMPERSONATE` | 0x0004 |
| `TOKEN_QUERY` | 0x0008 |
| `TOKEN_QUERY_SOURCE` | 0x0010 |
| `TOKEN_ADJUST_PRIVILEGES` | 0x0020 |
| `TOKEN_ADJUST_GROUPS` | 0x0040 |
| `TOKEN_ADJUST_DEFAULT` | 0x0080 |
| `TOKEN_ADJUST_SESSIONID` | 0x0100 |
| `TOKEN_ALL_ACCESS` | STANDARD_RIGHTS_REQUIRED \| 0x1FF |

### Duplicate

```c
NTSTATUS NtDuplicateToken(
    HANDLE                         ExistingTokenHandle,
    ACCESS_MASK                    DesiredAccess,
    POBJECT_ATTRIBUTES             ObjectAttributes,
    BOOLEAN                        EffectiveOnly,
    TOKEN_TYPE                     Type,             // 1=primary 2=impersonation
    PHANDLE                        NewTokenHandle
);
```

`ObjectAttributes->SecurityQualityOfService` carries the `SECURITY_IMPERSONATION_LEVEL` for impersonation-type duplicates. To turn an impersonation token into a primary usable with `CreateProcessAsUser`, duplicate with `Type=TokenPrimary`.

### Adjust privileges

```c
NTSTATUS NtAdjustPrivilegesToken(
    HANDLE              TokenHandle,
    BOOLEAN             DisableAllPrivileges,
    PTOKEN_PRIVILEGES   NewState,
    ULONG               BufferLength,
    PTOKEN_PRIVILEGES   PreviousState,
    PULONG              ReturnLength
);
```

Enabling `SeDebugPrivilege` on an Administrator token:

```c
HANDLE hTok;
NtOpenProcessTokenEx(NtCurrentProcess(),
    TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, 0, &hTok);

TOKEN_PRIVILEGES tp = { .PrivilegeCount = 1 };
LookupPrivilegeValueW(NULL, L"SeDebugPrivilege", &tp.Privileges[0].Luid);
tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

NtAdjustPrivilegesToken(hTok, FALSE, &tp, sizeof(tp), NULL, NULL);
// Must check GetLastError() == ERROR_NOT_ALL_ASSIGNED after success-status
// return: the syscall returns 0 (STATUS_SUCCESS) even when the privilege is
// not held, but PreviousState is empty. In NTSTATUS land check for
// STATUS_NOT_ALL_ASSIGNED (0x00000106 — note the success bit).
```

`STATUS_NOT_ALL_ASSIGNED` (`0x00000106`) has the informational bit set; `NT_SUCCESS(s)` is true for it. Always compare explicitly.

### Set thread impersonation

```c
NTSTATUS NtSetInformationThread(
    HANDLE           ThreadHandle,
    THREADINFOCLASS  ThreadInformationClass,   // ThreadImpersonationToken = 5
    PVOID            ThreadInformation,         // pointer to HANDLE
    ULONG            ThreadInformationLength    // sizeof(HANDLE)
);
```

Pass `NULL` token to revert to primary (`RevertToSelf` equivalent). The token handle must have `TOKEN_IMPERSONATE` and be an impersonation-type token at `SecurityImpersonation` level or higher.

### Query / set info

```c
NTSTATUS NtQueryInformationToken(HANDLE, TOKEN_INFORMATION_CLASS, PVOID, ULONG, PULONG);
NTSTATUS NtSetInformationToken  (HANDLE, TOKEN_INFORMATION_CLASS, PVOID, ULONG);
```

`NtSetInformationToken` with `TokenSessionId` requires `SeTcbPrivilege`. Setting `TokenIntegrityLevel` can only lower, never raise — attempted elevation returns `STATUS_PRIVILEGE_NOT_HELD`.

### Filter

```c
NTSTATUS NtFilterToken(
    HANDLE              ExistingTokenHandle,
    ULONG               Flags,            // DISABLE_MAX_PRIVILEGE, SANDBOX_INERT, LUA_TOKEN, WRITE_RESTRICTED
    PTOKEN_GROUPS       SidsToDisable,
    PTOKEN_PRIVILEGES   PrivilegesToDelete,
    PTOKEN_GROUPS       RestrictedSids,
    PHANDLE             NewTokenHandle
);
```

`SANDBOX_INERT` disables AppLocker, SRP, and some other security policies for the resulting token. `LUA_TOKEN` produces the Medium-IL "filtered" token UAC hands non-elevated processes.

## Process creation with alternate tokens

### CreateProcessWithTokenW (advapi32)

```c
BOOL CreateProcessWithTokenW(
    HANDLE               hToken,
    DWORD                dwLogonFlags,    // LOGON_WITH_PROFILE | LOGON_NETCREDENTIALS_ONLY
    LPCWSTR              lpApplicationName,
    LPWSTR               lpCommandLine,
    DWORD                dwCreationFlags,
    LPVOID               lpEnvironment,
    LPCWSTR              lpCurrentDirectory,
    LPSTARTUPINFOW       lpStartupInfo,
    LPPROCESS_INFORMATION lpProcessInfo
);
```

- Requires `SeImpersonatePrivilege`.
- Does RPC to `seclogon` (Secondary Logon Service) — creates an observable RPC call to SVCHOST. Secondary Logon is disabled on hardened hosts; check `sc query seclogon` first.
- Token must be primary type.

### CreateProcessAsUserW (advapi32)

```c
BOOL CreateProcessAsUserW(
    HANDLE               hToken,
    LPCWSTR              lpApplicationName,
    LPWSTR               lpCommandLine,
    LPSECURITY_ATTRIBUTES lpProcessAttributes,
    LPSECURITY_ATTRIBUTES lpThreadAttributes,
    BOOL                 bInheritHandles,
    DWORD                dwCreationFlags,
    LPVOID               lpEnvironment,
    LPCWSTR              lpCurrentDirectory,
    LPSTARTUPINFOW       lpStartupInfo,
    LPPROCESS_INFORMATION lpProcessInfo
);
```

- Requires `SeAssignPrimaryTokenPrivilege` AND `SeIncreaseQuotaPrivilege`.
- Token must be primary type; duplicate first if you have impersonation.
- Runs entirely in-process — no RPC to `seclogon` — quieter than `CreateProcessWithTokenW`.

### NtCreateUserProcess with token attribute

Use `PS_ATTRIBUTE_TOKEN` (`0x60002` = 2 from table with Input, Thread-allowed bit) in the `PS_ATTRIBUTE_LIST` to attach a token to the new process directly at creation. Same privilege requirements as `CreateProcessAsUser` but avoids the `advapi32` wrapper.

```c
PS_ATTRIBUTE_LIST attrList;
attrList.Attributes[0].Attribute = PS_ATTRIBUTE_TOKEN;   // 0x60002
attrList.Attributes[0].Size      = sizeof(HANDLE);
attrList.Attributes[0].ValuePtr  = hPrimaryToken;
```

## Stealing tokens

Classic sequence (requires `SeDebugPrivilege` on the target, or same-user ACLs):

```c
HANDLE hTarget = 0;
CLIENT_ID cid = { .UniqueProcess = (HANDLE)(ULONG_PTR)targetPid, .UniqueThread = 0 };
OBJECT_ATTRIBUTES oa; InitializeObjectAttributes(&oa, NULL, 0, NULL, NULL);

NtOpenProcess(&hTarget, PROCESS_QUERY_INFORMATION, &oa, &cid);

HANDLE hTok;
NtOpenProcessTokenEx(hTarget, TOKEN_DUPLICATE, 0, &hTok);

HANDLE hDup;
OBJECT_ATTRIBUTES oaTok; InitializeObjectAttributes(&oaTok, NULL, 0, NULL, NULL);
SECURITY_QUALITY_OF_SERVICE sqos = {
    sizeof(sqos), SecurityImpersonation, SECURITY_STATIC_TRACKING, FALSE
};
oaTok.SecurityQualityOfService = &sqos;

NtDuplicateToken(hTok, MAXIMUM_ALLOWED, &oaTok, FALSE, TokenImpersonation, &hDup);
NtSetInformationThread(NtCurrentThread(), ThreadImpersonationToken, &hDup, sizeof(hDup));
// Now this thread acts as the target user until RevertToSelf / set NULL.
```

For primary-token reuse (spawning a child as the target):

```c
NtDuplicateToken(hTok, MAXIMUM_ALLOWED, &oaTok, FALSE, TokenPrimary, &hDupPrimary);
CreateProcessAsUserW(hDupPrimary, ...);
```

## S4U and "Make Me Token"

`LsaLogonUser` with `MSV1_0_S4U_LOGON` fabricates a network-logon token for any local user without credentials — provided the caller has `SeTcbPrivilege` (i.e., runs as SYSTEM or a service). The resulting token is impersonation-level, good for local access checks and SMB-less pivoting through named pipes. Does NOT authenticate to remote hosts (no TGT).

`KERB_S4U_LOGON` requires domain membership and grants a Kerberos-backed identification token unless the source is trusted for constrained delegation.

## Potato-family coercion primitives

Pattern: an unprivileged service account holding `SeImpersonatePrivilege` coerces a higher-privileged principal (usually `NT AUTHORITY\SYSTEM`) into authenticating against an attacker-controlled endpoint, then relays/captures the resulting token.

| Variant | Coercion mechanism | State |
|---|---|---|
| Hot Potato | WPAD + NBNS spoofing + HTTP→SMB relay | Patched pre-2017 on modern builds |
| Rotten Potato | DCOM IStorage marshalled NTLM | Blocked by NTLM reflection fixes |
| Juicy Potato | Picks a COM server running as SYSTEM | Broken on 1809+ (COM IL checks) |
| Rogue Potato | Fake OXID resolver on port 135 | Usually blocked; works on misconfigured hosts |
| PrintSpoofer | Spooler RPC `IRemotePrintNotifyServer` → SYSTEM pipe | Works where spooler enabled |
| RoguePotato → Juicy2 / SweetPotato / GenericPotato | Various COM+ / DCOM angles | Hit or miss per build |
| EfsPotato | EFSRPC `EfsRpcEncryptFileSrv` → SYSTEM | Works when EFS RPC enabled |
| RemotePotato0 | Cross-session DCOM | Depends on RPC/DCOM hardening |
| GodPotato | RPCSS → any-user when SeImpersonate held | Current as of Win11 24H2 |

All require `SeImpersonatePrivilege` already. The primitive converts SeImpersonate + coercible service → SYSTEM primary token.

## Restricted and filtered tokens

UAC on a Medium-IL admin user splits the logon token in two:

- **Full token**: Admin group enabled, IL=High, full privileges. Used only by consented elevation.
- **Filtered (LUA) token**: Admin group set to `SE_GROUP_USE_FOR_DENY_ONLY`, IL=Medium, reduced privilege set (`SeChangeNotify`, `SeShutdown`, `SeUndock`, `SeIncreaseWorkingSet`, `SeTimeZone`). `TokenLinkedToken` query returns the full token.

AppContainer tokens carry:

- Package SID (S-1-15-2-...)
- Capability SIDs (e.g., `lpacCom`, `internetClient`, `capabilityProtectedApp`)
- `LOWBOX` flag
- Custom default DACL blocking access from outside the container

LPAC (Less Privileged AppContainer, Edge renderer) adds `S-1-15-3-1024-*` capability SIDs controlling which OS services are even reachable.

Restricted tokens (`SANDBOX_INERT` + restricted SIDs) are intersected at access-check time: the resulting access must be granted by both the primary SID list and the restricted list. Chromium / Edge browser sandbox relies on this.

## Process Protection Level (PPL / PP)

Not strictly a token property, but adjacent. `EPROCESS->Protection` encodes a `PS_PROTECTION` byte:

```c
typedef struct _PS_PROTECTION {
    UCHAR Type    : 3;   // 0=None, 1=Protected, 2=ProtectedLight
    UCHAR Audit   : 1;
    UCHAR Signer  : 4;   // 0=None 1=Authenticode 2=CodeGen 3=Antimalware
                         // 4=Lsa 5=Windows 6=WinTcb 7=WinSystem
                         // 8=App
} PS_PROTECTION;
```

Signer hierarchy (higher blocks lower):

1. None (0)
2. Authenticode (1)
3. Antimalware (3) — used by Defender, third-party AV vendors
4. Lsa (4)
5. Windows (5)
6. WinTcb (6)
7. WinSystem (7)

A PP-signed process blocks a PPL-signed one of equal/lower rank from opening handles with rights beyond `PROCESS_QUERY_LIMITED_INFORMATION`. Even `SeDebugPrivilege` does not override PP. Attacks: BYOVD to clear `Protection` via kernel write, or abuse `SeTcbPrivilege` workflows. LSASS runs as PPL (`Signer=Lsa, Type=1`) on default Win11 24H2, blocking classic `MiniDumpWriteDump` from userland SYSTEM.

## Trust levels (process trust SID)

Orthogonal to PPL. The `TokenProcessTrustLevel` encodes signer origin as a SID like `S-1-19-512-8192` (ProtectedLight-WinTcb). Used by some object-security DACLs to gate access. LSASS objects, for instance, carry ACEs referencing the Windows trust SID.

## Audit events

Tokens are the most-watched objects on a Windows host.

| Event ID | Source | Meaning |
|---|---|---|
| 4624 | Security | Logon success — includes logon type, package, token elevation type, process name |
| 4625 | Security | Logon failure |
| 4634 / 4647 | Security | Logoff |
| 4648 | Security | Explicit credentials used (e.g., `runas`) |
| 4672 | Security | **Special privileges assigned to new logon** — fires when a logon session includes Se*Debug/Tcb/Backup/Restore/etc. Noisy for admin logons but high-signal for lateral-movement tools that wake the token briefly |
| 4673 | Security | Privileged service was called — `SeDebugPrivilege`, `SeTcbPrivilege` use |
| 4674 | Security | Privileged object operation — process open, token open, etc. |
| 4688 | Security | Process creation — includes parent PID, process command line (if enabled), and since 1809, creator/target subject tokens |
| 4689 | Security | Process termination |
| 4697 | Security | Service installed (includes service file name + account) |
| 4698/4699/4700/4701/4702 | Security | Scheduled task created/deleted/enabled/disabled/updated |
| 4768/4769 | Security | Kerberos TGT/TGS request |
| 4770/4771 | Security | Kerberos TGT renewed / pre-auth failed |
| 4776 | Security | NTLM credential validation |

`SACL:UseSeInformation` auditing must be enabled via Group Policy (`Audit Sensitive Privilege Use`) for 4673/4674. `auditpol /get /category:*` reveals the current state.

Token-adjustment does not have its own event ID by default — observed indirectly as 4672/4673 when the enabled privilege is used. Sysmon fills the gap with Event 10 (ProcessAccess) showing token duplication handles and Event 1 (ProcessCreate) carrying the resultant process identity.

Kernel telemetry the user never sees:

- ETW-TI `EtwTiLogSetProcessTokenInfo` — fires on `NtSetInformationProcess(ProcessAccessToken)` (rare, but used by some sandbox escapes).
- ETW-TI `EtwTiLogImpersonateToken` — when a thread impersonation is established against a different primary user.
- Security Auditing provider raises 4672 via internal ETW as well.

## Identity-in-thread invariants

- `NtCurrentTeb()->CurrentLocale` is not security; `NtCurrentTeb()->RealClientId` and `NtCurrentTeb()->ClientId` are the logon LUIDs for the thread.
- Impersonation tokens persist across syscalls but do NOT propagate through thread creation. A child thread starts under the process primary token regardless of parent thread impersonation — must re-apply after `NtCreateThreadEx`.
- Handle inheritance: an inheritable token handle passes into child processes via `bInheritHandles=TRUE`, but the process primary token is NOT inherited — must be specified explicitly.
- `RevertToSelf` sets the thread impersonation token slot to NULL, dropping any stolen identity. Any API that spins a worker thread (RPC, most shell APIs) implicitly reverts on the worker. `CoInitializeSecurity(...EOAC_DYNAMIC_CLOAKING...)` changes DCOM marshalling to propagate the current thread's impersonation rather than process identity.

## Minimal token-theft primitive (hardened)

Combined pattern used in modern red-team tooling. Uses indirect syscalls, avoids `advapi32`:

```c
// 1. Enable SeDebugPrivilege on own token
HANDLE hSelfTok;
NtOpenProcessTokenEx(NtCurrentProcess(), TOKEN_ADJUST_PRIVILEGES, 0, &hSelfTok);
TOKEN_PRIVILEGES tp = { 1, { { { 20, 0 }, SE_PRIVILEGE_ENABLED } } };  // LUID(20,0) = SeDebug on current builds; prefer lookup
NtAdjustPrivilegesToken(hSelfTok, FALSE, &tp, sizeof(tp), NULL, NULL);

// 2. Enumerate via NtQuerySystemInformation(SystemProcessInformation)
//    pick winlogon.exe (or any SYSTEM process not PPL)
// 3. NtOpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)
// 4. NtOpenProcessTokenEx(TOKEN_DUPLICATE)
// 5. NtDuplicateToken -> primary token
// 6. NtCreateUserProcess with PS_ATTRIBUTE_TOKEN pointing at duped handle
//    and PS_ATTRIBUTE_PARENT_PROCESS pointing at a harmless parent for PPID spoofing
```

Noise profile vs `CreateProcessWithTokenW`:

- No RPC to `seclogon`.
- No `advapi32` load, no `userenv.dll` profile creation calls.
- Single `NtCreateUserProcess` call instead of the multi-API wrapper chain — reduces EDR hook surface.
- Still fires 4688 (new process), 4672 (special privileges on new logon if applicable), 4624 (if a new logon session is created — `CreateProcessAsUser` does NOT create a new session when reusing an existing token, which is why it's quieter than the `With*` variants that do spin up seclogon sessions).

## Common mistakes

- Forgetting to duplicate to primary before `CreateProcessAsUserW` — returns `ERROR_PRIVILEGE_NOT_HELD` with misleading message.
- Opening a token with only `TOKEN_QUERY` then trying to adjust privileges — `STATUS_ACCESS_DENIED`.
- Setting impersonation token on a thread that currently holds a handle opened with the old identity — the handle still works (access already granted), but newly-opened handles use the new context.
- Assuming `NT_SUCCESS` on `NtAdjustPrivilegesToken` means the privilege was granted — `STATUS_NOT_ALL_ASSIGNED` (0x00000106) is success-class.
- Leaving an impersonation token on a thread that then spawns a child via `CreateProcess` (primary only) — child does NOT inherit impersonation. Use `CreateProcessAsUser` explicitly.
- Using a handle with `MAXIMUM_ALLOWED` and being surprised when it gets different rights on different systems — base access-check on declared required rights.
- Forgetting that `NtSetInformationThread(ThreadImpersonationToken, NULL)` reverts, but passing a closed/invalid handle returns `STATUS_INVALID_HANDLE` — check.
- Duplicating LSASS token on a PPL system assuming SeDebugPrivilege suffices — it does not open LSASS with PROCESS_QUERY_INFORMATION (the minimum for `NtOpenProcessToken`) when LSASS is PPL.
- Treating integrity level as "privilege" — IL gates object access; privileges gate specific operations. You need both, and they are not substitutable.
