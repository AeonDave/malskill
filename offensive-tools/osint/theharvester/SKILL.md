---
name: theharvester
description: "Collect emails, hostnames and other public-source evidence for a domain with theHarvester."
license: GPL-2.0
compatibility: "Python 3.14 and uv for the upstream development branch."
metadata:
  author: AeonDave
  version: "1.0"
---

# theHarvester

The [upstream development branch](https://github.com/laramies/theHarvester) uses Python 3.14 and uv. Release 4.11.1 documents Python 3.12+ and may differ in flags and outputs:

```bash
git clone https://github.com/laramies/theHarvester.git
cd theHarvester
uv sync
uv run theHarvester -d example.com -b crtsh,certspotter -f report
```

On the development branch, the output includes JSONL, JSON and XML; source outcomes can be complete, partial or failed. Passive providers receive the domain even when the target is not directly contacted. There, `-b all` selects P0 passive sources, not all active sources. Use `uv run theHarvester -h` and the matching source documentation for options, provider requirements and network behavior; opt into DNS or direct activity only within scope.
