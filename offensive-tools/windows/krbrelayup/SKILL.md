---
name: krbrelayup
description: "Assess KrbRelayUp prerequisites and interpret existing Kerberos-relay test results, separating individual stages and directory-policy findings."
license: MIT
compatibility: "Windows domain environments; behavior depends on the selected source revision, method, directory protections, and account rights."
metadata:
  author: AeonDave
  version: "1.0"
---

# KrbRelayUp

Use the [upstream method documentation](https://github.com/Dec0ne/KrbRelayUp) for the exact revision. Kerberos authentication does not make directory-service protections irrelevant.

## Assessment workflow

1. Record OS build, domain/controller, tool revision, selected method, and observed policy configuration.
2. Keep stage outcomes separate: authentication, relay, directory modification, ticket handling, and local process/service creation. Success at one stage does not establish the next.
3. Preserve the original values of any directory attributes or service state changed by a test; compare before and after rather than blindly clearing attributes.
4. Report the demonstrated result and remaining failed or untested stages.

## Correct interpretation

- The upstream LDAP-relay description depends on signing not being enforced. Upstream explicitly recommends LDAP signing and channel binding as mitigations; claiming they do not block Kerberos relay is incorrect.
- SMB signing and LDAP/LDAPS protections govern different endpoints. One finding does not establish another protocol's viability.
- Machine-account creation, control of an existing account, and permission to modify the target object are distinct conditions.
- RBCD, shadow-credential, and AD CS methods have different prerequisites and artifacts. Do not apply a single cleanup or compatibility claim to all of them.
- An absence of credential dumping does not establish invisibility or success on every Windows version.

For per-controller LDAP protection checks, load [LdapRelayScan](../ldaprelayscan/SKILL.md).
