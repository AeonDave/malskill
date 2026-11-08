---
name: dalfox
description: "Auth/lab ref: Dalfox XSS scanning, parameter discovery, and DOM analysis."
license: MIT
compatibility: "Dalfox v3.2.4 (Rust); Linux / macOS / Windows."
metadata:
  author: AeonDave
  version: "1.2"
---

# Dalfox

Install using upstream [releases or installation guide](https://github.com/hahwul/dalfox); check `dalfox --version` and `dalfox scan --help` because v2 and v3 differ.

```bash
dalfox scan 'https://example.com/search?q=test'
dalfox scan urls.txt --workers 10 --rate-limit 10 --format json -o results.json
cat urls.txt | dalfox scan -i pipe -S
dalfox scan 'https://example.com/search?q=test' --only-discovery
```

Use `--cookies`, `--headers`, `--data`, and `--method` for authenticated or captured requests; use `-i raw-http` or `-i har` for captured input. `--delay` is per worker; `--rate-limit` caps the aggregate request rate. Scope URLs before scanning.

`--skip-mining-dom` disables mining parameter names from HTML, not DOM analysis; `--skip-ast-analysis` disables that analysis. `--sxss --sxss-url <retrieval-url>` enables stored-XSS checks. `--blind <callback-url>` sends blind payloads to a listener you monitor; a callback alone requires contextual validation.

Treat reflected and AST findings as leads; verify them in context. Consult the [v3.2.4 CLI reference](https://github.com/hahwul/dalfox/blob/v3.2.4/docs/content/reference/cli.md) for finding types, configuration and flags.
