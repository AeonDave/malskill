---
name: hayabusa
description: "Analyze Windows EVTX logs with Hayabusa detection rules and export an alert timeline."
license: MIT
compatibility: "Hayabusa release package; Windows / Linux / macOS."
metadata:
  author: AeonDave
  version: "1.0"
---

# Hayabusa

Download the appropriate [release package](https://github.com/Yamato-Security/hayabusa/releases), including rules and configuration. For an offline collection:

```bash
hayabusa csv-timeline -d logs/ -m medium --no-wizard -o alerts.csv
hayabusa json-timeline -d logs/ --no-wizard -o timeline.json
```

For local Windows logs, use `csv-timeline -l`; it analyzes the local event log directory. Run `hayabusa csv-timeline --help` for the installed version's rule and output options. Record the rule version and selection with results, and inspect event context before treating a rule hit as an incident. A medium threshold omits lower-level detections; expand it when needed.
