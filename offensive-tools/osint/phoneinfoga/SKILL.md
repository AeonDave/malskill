---
name: phoneinfoga
description: "Investigate phone number metadata and public search leads using PhoneInfoga."
license: MIT
compatibility: "Go binary; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.1"
---

# PhoneInfoga

Install a binary from [upstream releases](https://github.com/sundowndev/phoneinfoga/releases), or use its container. Provide an international-format number and inspect the individual scanner outcomes:

```bash
phoneinfoga scan -n +14151234567
phoneinfoga serve
```

The scan command prints human-readable output; redirecting it does not make JSON. Consult `phoneinfoga scan --help` and [upstream documentation](https://sundowndev.github.io/phoneinfoga/) for scanner configuration. Metadata and search results are leads, not proof of current ownership or location.
