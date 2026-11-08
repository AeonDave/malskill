---
name: ldaprelayscan
description: "Assess effective LDAP signing and LDAPS channel-binding enforcement with LdapRelayScan; interpret per-controller results and inconclusive tests."
license: MIT
compatibility: "Unmodified upstream uses ssl.wrap_socket, removed in Python 3.12; use a compatible Python 3.11 environment and its pinned requirements."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-tools
---

# LdapRelayScan

Test directory-service authentication protections. A policy finding is evidence about that endpoint, not proof that an attack chain will succeed.

## Setup and checks

Use the [upstream repository](https://github.com/zyn3rgy/LdapRelayScan) and its dependency set; do not assume a PyPI package or executable named `ldaprelayscan`.

```bash
git clone https://github.com/zyn3rgy/LdapRelayScan.git
cd LdapRelayScan
python3.11 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements_exact.txt
python3 LdapRelayScan.py -h

# DNS/discovery seed; tests the domain controllers discovered through it
python3 LdapRelayScan.py -method LDAPS -dc-ip 192.0.2.10

# LDAP signing plus LDAPS channel binding; prompts for credentials
python3 LdapRelayScan.py -method BOTH -dc-ip 192.0.2.10 -u audit-user
```

- Methods are `LDAPS` (unauthenticated channel-binding checks) and `BOTH` (signing and channel binding with credentials); there is no SMB method.
- `-dc-ip` seeds DNS and LDAP discovery. The script enumerates DC SRV records and tests discovered controllers; it is not a single-controller target selector.
- Check DNS resolution and connectivity first. Capture actual discovered/tested controller names, addresses, timestamps, method, tool revision, and raw results.
- Compare tested controllers with an independent inventory. A discovery failure or an omitted DC leaves a coverage gap; changing the discovery seed does not guarantee a bounded target set.
- Bind failures, TLS errors, unreachable endpoints, and invalid credentials are inconclusive, not evidence of enforcement.
- Preserve the distinction between channel binding being absent, conditional, and required. Do not collapse these into a single pass/fail.
- Tests perform connection and authentication attempts and may produce logs. The tool does not verify SMB signing, HTTP protections, account privileges, or downstream exploitability.

Return a per-controller finding with observed enforcement, failed tests, and the smallest remaining validation step. Recheck after policy changes.
