---
name: ghunt
description: "Investigate Google account and Drive information with GHunt using an email address, Gaia ID, or file ID."
license: MIT
compatibility: "Python 3.10+; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# GHunt

Install and authenticate as described in [upstream](https://github.com/mxrch/GHunt); Google may change service availability. Use only accounts and data within the investigation scope.

```bash
pip install ghunt
ghunt login
ghunt email person@example.com --json result.json
ghunt gaia <gaia-id> --json gaia.json
ghunt drive <file-id> --json drive.json
```

`--json` takes an output filename; it does not produce JSON on stdout. Drive expects the file ID, not a URL. The available modules are `login`, `email`, `gaia`, `drive`, and `geolocate`; run the selected module with `-h` for current options. Returned information depends on access and service availability; corroborate attribution independently.
