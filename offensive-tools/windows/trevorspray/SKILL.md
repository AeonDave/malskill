---
name: trevorspray
description: "Review TREVORspray's installed CLI, module compatibility, and authentication-test results; distinguish failures, lockouts, and inconclusive responses."
license: GPL-3.0
compatibility: "Python; the upstream trevorspray-v2 branch has a modular CLI. Check the installed revision and module help."
metadata:
  author: AeonDave
  version: "1.1"
---

# TREVORspray

Match documentation to the installed revision before interpreting a run. [Upstream v2](https://github.com/blacklanternsecurity/TREVORspray/tree/trevorspray-v2) retains modules; it does not replace them with endpoint auto-detection.

```bash
trevorspray --help
```

## CLI and result checks

- Confirm the actual module and its supported authentication flow. Changing the URL does not make one module suitable for another protocol or identity provider.
- Do not reuse examples that label `-e` as an email-list argument or `-u` as a URL: they contradict the upstream v2 CLI.
- Verify the input, module, and installed-version contract before interpreting output; do not infer success from an HTTP status alone.
- Separate valid authentication, MFA or conditional-access requirements, lockouts, invalid credentials, rate limiting, and transport errors.
- A delay or jitter setting does not guarantee lockout avoidance or invisibility. Account policy, concurrent attempts, and provider controls affect the result.
- Preserve the revision, module, timestamps, and redacted raw responses. Report inconclusive cases separately from valid and invalid authentication results.

Source: [upstream usage and module definitions](https://github.com/blacklanternsecurity/TREVORspray).
