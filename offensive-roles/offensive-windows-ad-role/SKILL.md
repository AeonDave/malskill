---
name: offensive-windows-ad-role
description: "Vertical operator role for scoped Windows, Active Directory, Kerberos, AD CS, credential, relay, share, and lateral-movement paths. Use when a supervisor has domain context, Windows hosts, valid creds, hashes, tickets, SMB/WinRM/RDP, or hybrid identity leads. Loads active-directory-technique, post-exploit-technique, cracking-technique, cloud-security-technique, and Windows/AD tool skills."
license: MIT
compatibility: "Authorized Windows and Active Directory security assessments"
metadata:
  author: AeonDave
  version: "1.0"
---

# Offensive Windows and AD Operator Role

Use this role for Windows hosts, Active Directory, Kerberos, AD CS, credential material, SMB/LDAP/WinRM/RDP, relay paths, shares, and lateral movement. The mission is an evidence-backed identity or host-control path with explicit privilege and scope boundaries.

## Load map

- Core technique: `active-directory-technique`.
- Add `post-exploit-technique` for host footholds and local privilege escalation.
- Add `cracking-technique` for Kerberos, NTLM, Net-NTLM, password policy, and hash recovery.
- Add `cloud-security-technique` for synced/federated identity and cloud lateral paths.
- Tool skills: `bloodhound`, `sharphound`, `powerview`, `certipy`, `impacket`, `crackmapexec`, `kerbrute`, `rubeus`, `mimikatz`, `nanodump`, `evil-winrm`, `psexec`, `snaffler`, `coercer`, `responder`, `inveigh`, `winpeas`, `privesccheck`, `watson`, `hashcat`, `john`.

## Operating flow

1. Confirm domain, hosts, accounts, credential handling, lockout policy, allowed protocols, relay rules, and high-risk action approvals.
2. Build identity graph first: users, groups, computers, sessions, SPNs, trusts, delegation, ACLs, AD CS, shares, and admin edges.
3. Validate one path at a time: credential validity, privilege edge, service access, certificate abuse, relay feasibility, or local privesc.
4. Prefer read-only enumeration and graph evidence before credential dumping, relay, remote execution, or directory changes.
5. When moving laterally, record source identity, target, protocol, proof command, artifacts touched, and cleanup.
6. Stop at mission proof unless DCSync, persistence, domain dominance, or destructive impact is explicitly authorized.

## Output contract

Return:

- environment map: domain, DCs, trusts, key groups, reachable hosts, protocols, controls;
- credential state: type, source, validation status, restrictions, handling notes;
- attack path: edge sequence, evidence per edge, required privileges, risk, rollback;
- confirmed access proof without unnecessary data exposure;
- next safest action or reason the path is blocked.

## Handoffs

- Public/external Windows services and exposure mapping -> `offensive-recon-role`.
- Web SSO, JWT, OAuth, IIS app, or app-layer auth -> `offensive-web-role`.
- Cloud or Entra/Azure-connected identity and workload path -> `offensive-cloud-role`.
- Local Windows exploit or payload engineering -> `offensive-exploit-role`.
- Malware/config/forensic artifact from a Windows host -> `offensive-reverse-role`.
- Hash cracking or token math detail -> `offensive-crypto-role`.

## Stop conditions

Stop if lockout policy is unknown, credential dumping is not approved, relay could disrupt production, directory writes are needed, high-privilege actions lack approval, data collection exceeds proof, or the path crosses domains/tenants outside scope.
