---
name: donpapi
description: "Review DonPAPI version compatibility and collected DPAPI/application artifacts; interpret coverage, errors, and exported evidence."
license: MIT
compatibility: "The upstream 2.1.0 source declares Python 3.10+. Its command layout differs from the older V1.2.0 release."
metadata:
  author: AeonDave
  version: "1.0"
---

# DonPAPI

Keep the installed revision, collector configuration, and artifact provenance together. The latest GitHub release asset and the current source branch may describe different command layouts.

```bash
donpapi --help
donpapi gui --help
```

## Compatibility and evidence

1. Check the selected source's Python requirements and subcommand help. Do not combine 1.x examples with 2.x options.
2. Map each result to the host, user, application, collector, and collection time.
3. Separate collection success from successful decryption. Unsupported artifacts, access failures, missing key material, and empty stores are different outcomes.
4. Review existing results through the local GUI or documented exports. Keep the service bound to loopback unless a different deployment is explicitly configured.
5. Redact recovered values in reports; retain evidence locations and affected applications.

## Avoid false coverage claims

- DPAPI is one protection mechanism. Do not describe the tool as recovering every secret or as equivalent to an LSASS dump.
- Browser support depends on browser build, artifact type, protection scheme, and the selected collector/dependency versions. Do not infer universal App-Bound support.
- The absence of LSASS access is not absence of telemetry; network, service, registry, and filesystem activity can still be observable.
- Use the installed output/database layout. Do not assume per-host JSON/Markdown directories or that task XML contains account passwords.

Sources: [upstream documentation](https://github.com/login-securite/DonPAPI), [source requirements](https://github.com/login-securite/DonPAPI/blob/main/pyproject.toml), [published releases](https://github.com/login-securite/DonPAPI/releases).
