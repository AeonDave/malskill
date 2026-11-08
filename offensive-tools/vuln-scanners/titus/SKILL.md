---
name: titus
description: "Scan local files and Git history for secrets with Titus and review its datastore."
license: Apache-2.0
compatibility: "Titus release binary; Linux / macOS / Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# Titus

Install the appropriate binary from [upstream releases](https://github.com/praetorian-inc/titus/releases); inspect `titus scan --help` for the installed version.

```bash
titus scan ./project
titus scan --git ./repo
titus report --format json
titus rules list
```

Results are stored in `titus.ds` by default. Review finding provenance and context, including historical or revoked secrets. Local scans use static scoring; `--validate` and `--score-scope` make external API calls and should be used only when explicitly authorized.
