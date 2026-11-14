---
name: waymore
description: "Collect historical URLs and archived response bodies for authorized web surface discovery with waymore."
license: MIT
compatibility: "Python 3; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# waymore

Collect historical URLs from archive and index providers; retrieve archived response bodies when content is needed. Install with `pip install waymore` or follow the [upstream instructions](https://github.com/xnl-h4ck3r/waymore).

```bash
# URLs only; write to an explicit path
waymore -i example.com -mode U -oU urls.txt

# Download up to 500 archived responses
waymore -i example.com -mode R -l 500

# Retrieve URLs and responses; include all URLs in the URL output
waymore -i example.com -mode B -f -l 500
```

For domain input, mode defaults to `B` and includes subdomains; `-n` excludes subdomains except `www`. A domain with a path defaults to response mode. `-f` applies filters only to downloaded responses, and `-l` limits saved responses, not requests or URL results. Review `waymore -h` and `config.yml` for provider credentials and filters.

Default results are under the configuration directory, typically `~/.config/waymore/results/<domain>/`. Response files can consume substantial disk; an interrupted response download can be resumed. Providers may throttle or return incomplete results. Treat historical URLs as leads, not evidence of a currently live endpoint or authorization to contact it.
