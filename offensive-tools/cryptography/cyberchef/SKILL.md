---
name: cyberchef
description: "Auth/lab ref: Web-based data transformation and crypto analysis workbench. For rapidly decoding layered encodings, transforming binary/text formats, prototyping crypto/decode pipelines, or sharing reproducible recipes."
license: Apache-2.0
compatibility: "Authorized/lab use only; see body for platform and setup constraints."
metadata:
  author: AeonDave
  version: "1.0"
---

# CyberChef

CyberChef is ideal for **rapid transformation pipelines**: decode, inspect, branch, and iterate without writing throwaway scripts first.

## Core use in crypto/reversing

- Unwrap nested encodings (Base64/Hex/URL/gzip/rot/XOR).
- Test candidate keys/IVs quickly for block/stream ciphers.
- Analyze unknown blobs via `Magic` before custom code.
- Export reproducible recipes through URL hash or saved JSON.

## High-value workflow

1. Load input (text, hex dump, file).
2. Start with `Magic` and inspect suggestions.
3. Build explicit recipe chain (avoid blind overfitting).
4. Add breakpoints and step through each operation.
5. Export URL/recipe JSON for reproducibility and script handoff.

## Deep-link format

CyberChef supports URL recipes:

```text
https://gchq.github.io/CyberChef/#recipe=<Ops>&input=<Base64Input>
```

This is useful for teammate handoff and agent reproducibility.

## Local/offline options

- Browser app is client-side by design.
- For isolated environments, run local Docker image and use local browser access.

## Automation bridge

When recipe stabilizes and must be automated at scale:
- Move from web recipe to CyberChef Node API (`chef.bake`) or to Python equivalents.
- Keep operation order and arguments identical.

## Browser interaction note

CyberChef is a web-first tool. If interactive browser steps are required and cannot be executed automatically in the current environment, request user-assisted interaction (e.g., upload input blob, verify candidate recipe output).

## Resources

- `references/web-workflows.md` — practical browser workflow, Magic usage, breakpoints, recipe sharing, and validation strategy.
- `references/node-api-handoff.md` — converting web recipes into programmatic Node API (`chef`, `Dish`, `bake`) for agentic automation.
