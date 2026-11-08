---
name: osv-scanner
description: "Scan dependency manifests, lockfiles, SBOMs, and container images with OSV-Scanner; interpret package findings and call-analysis coverage."
license: Apache-2.0
compatibility: "OSV-Scanner v2.7.0; Linux / macOS / Windows. Go call analysis requires go on PATH."
metadata:
  author: AeonDave
  version: "1.1"
---

# OSV-Scanner

Record the scanner version, inputs, database mode, and analysis failures. A package vulnerability match is not proof that vulnerable code is reachable.

## Scan and review

```bash
osv-scanner --version
osv-scanner scan source --help

# Directory discovery, or an explicitly selected lockfile
osv-scanner scan source -r . --format json -o scan.json
osv-scanner scan source --lockfile package-lock.json

# Container image
osv-scanner scan image myapp:version --format json -o image.json

# CI artifact; interpret the exit status separately
osv-scanner scan source -r . --format sarif -o results.sarif
```

- In v2, source scanning uses `scan source`. Lockfile shorthand is uppercase `-L`; prefer `--lockfile` in shared instructions.
- Exit 0 means no issues found, 1 means issues found, 127 an error, and 128 no packages found. Do not report an errored or empty scan as clean.
- Go call analysis is enabled by default when supported and requires `go` on PATH. Check whether analysis completed before interpreting a function as uncalled.
- Match results to the resolved package version and ecosystem. Manifests, lockfiles, installed artifacts, and deployed images may represent different dependency sets.
- Offline vulnerability lookup does not establish that the entire workflow is network-free; dependency tooling and other analysis modes have separate requirements.

## Parse without losing package context

```bash
jq '.results[].packages[] | .package as $pkg |
    .vulnerabilities[]? |
    {id, package: $pkg.name, version: $pkg.version, ecosystem: $pkg.ecosystem}' scan.json
```

Retain raw JSON alongside projections so grouping, aliases, source locations, and analysis details remain available.

Load [references/config-ignore.md](references/config-ignore.md) when configuring ignores, offline lookup, or call-analysis limitations. For CI integration, use the matching [official action](https://github.com/google/osv-scanner-action) rather than assuming reusable-workflow inputs.

Sources: [v2.7.0 usage](https://github.com/google/osv-scanner/blob/v2.7.0/docs/usage.md), [output contract](https://github.com/google/osv-scanner/blob/v2.7.0/docs/output.md).
