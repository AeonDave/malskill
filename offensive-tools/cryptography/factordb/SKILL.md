---
name: factordb
description: "FactorDB: public factorization database and simple JSON API for checking whether integers are prime, composite, or already factored. Use when triaging RSA moduli, large composites, or challenge numbers before spending local compute on factoring."
compatibility: "Web service with browser and JSON API access; internet required"
metadata:
  author: AeonDave
  version: "1.0"
---

# FactorDB

The fastest factorization step is the one somebody else already paid for.

## When to use FactorDB

Use FactorDB when you need to:

- check whether a modulus or large integer is already known and factored
- retrieve small-to-medium factors quickly before deeper math work
- decide whether RSA triage should move to `sagemath`, `rsactftool`, or a different line of attack

## Quick Start

```bash
# Browser/API query
curl "https://factordb.com/api?query=5959"

# Example response shape
{"id":"5959","status":"FF","factors":[["59",1],["101",1]]}
```

## Practical Workflow

1. Query the target integer through the API or site.
2. Inspect `status` before trusting the result.
3. If factors are returned, convert them into your local math workflow.
4. If the number is still composite or partially factored, escalate to `sagemath`, ECM, or a problem-specific attack.

## Common Uses

- RSA modulus triage
- `p - 1` or `q - 1` structure checks after recovering factors
- sanity-checking challenge integers before local brute force

## Practical Notes

- `FF` means fully factored in the typical workflow; partially solved composites need follow-up.
- FactorDB is a lookup service first, not a guaranteed live factorization oracle.
- Preserve source numbers exactly; dropped digits or formatting mistakes waste time and give false confidence.

## Caveats

- Large unfactored composites may return incomplete results.
- Internet dependence makes it unsuitable for isolated environments.
- Treat it as a reconnaissance accelerator, not as the whole cryptanalysis plan.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the public API endpoint and site UI for current status and factor-list formatting.
