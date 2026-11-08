---
name: amass
description: "Map an authorized external attack surface with OWASP Amass domain enumeration and asset intelligence."
license: Apache-2.0
compatibility: "Go binary; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# Amass

Use `amass enum -h`, `amass intel -h` and `amass db -h` for the installed version: flags and configuration differ between releases. See the [official documentation](https://owasp-amass.github.io/docs/) for installation, data-source configuration and database setup.

```bash
amass enum -passive -d example.com -o subdomains.txt
```

Passive collection queries external providers, which receive the domain. Check configured provider coverage and source errors; no result is not proof of absence. Review discovered names against scope before resolving or probing them.
