---
name: wafw00f
description: "WAF detection tool. Fingerprints Web Application Firewalls by analyzing HTTP responses to crafted requests. Identifies vendor and product (Cloudflare, AWS WAF, ModSecurity, Akamai, F5, Imperva, etc.) to inform bypass strategy selection."
license: MIT
compatibility: "Linux/macOS/Windows; Python 3; targets any HTTP/HTTPS service"
metadata:
  author: AeonDave
  version: "1.0"
  category: recon
  language: python
---

# wafw00f

WAF fingerprinting via crafted HTTP probes. Use before content discovery, injection testing, or active scanning to know what protection is in place.

## Quick start

```bash
# Detect WAF on single target
wafw00f https://target.com

# Try all fingerprints (not just first match)
wafw00f -a https://target.com

# Multiple targets from file
wafw00f -i targets.txt

# Output formats
wafw00f https://target.com -o json -f output.json
wafw00f https://target.com -o csv -f output.csv

# Verbose (show probe details)
wafw00f -v https://target.com
```

## Output interpretation

```
[+] The site https://target.com is behind Cloudflare (Cloudflare Inc.) WAF.
[+] The site https://target.com is behind ModSecurity (SpiderLabs/Trustwave)
[-] No WAF detected by the generic detection
```

No detection does not mean no WAF — some WAFs are passive (log-only) or use custom signatures not in wafw00f's database.

## Integration in workflow

Run after initial HTTP fingerprinting and before:
- Content discovery / directory brute-force
- Active injection testing (SQLi, XSS)
- Nuclei scanning

Result informs bypass strategy — see `offensive-techniques/web-exploit-technique/references/waf-bypass.md`.
