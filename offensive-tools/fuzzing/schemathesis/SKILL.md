---
name: schemathesis
description: "OpenAPI/GraphQL property-based API fuzzer. Use to auto-generate API tests, catch schema violations, triage failures systematically, and run high-coverage stateful campaigns in REST/GraphQL services."
license: MIT
compatibility: "Python CLI/library; CI-friendly."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# schemathesis

Schema-driven API fuzzing for developer and AppSec workflows.

## Quick Start

```bash
# CLI
uvx schemathesis run https://example.schemathesis.io/openapi.json

# Installed CLI
schemathesis run https://your-api/openapi.json
```

```python
import schemathesis
schema = schemathesis.openapi.from_url("https://your-api/openapi.json")

@schema.parametrize()
def test_api(case):
    case.call_and_validate()
```

## Operator Flow

1. First run with defaults to map baseline failure landscape.
2. Triage in this order: undocumented status codes -> schema conformance -> server errors.
3. Narrow scope by tag/path to fix incrementally.
4. Run longer optimization profile for release/security gates.
5. Keep CI smoke + nightly deep profiles separated.

## Strengths

- Generates large input space from API schema automatically.
- Detects 500s, contract/schema drift, validation bypasses.
- Supports stateful API workflows (operation sequences).

## Optimization Profile (Deep Runs)

```bash
schemathesis run <schema_url> \
  --max-examples 1000 \
  --continue-on-failure
```

Often paired with targeted generation and health-check suppression on complex schemas.

## Practical Tricks

- Use include-path/include-tag scope to eliminate triage noise.
- Keep one strict schema-conformance pass and one exploratory bug-hunting pass.
- Export machine-readable artifacts (JUnit/Allure) for team triage.
- Re-run minimal reproducer from failing example before opening defect ticket.

## Common Pitfalls

- Trying to fix every first-run failure globally at once.
- Ignoring repetitive undocumented status patterns that should be schema-level fixes.
- Treating long-run health-check warnings as always ignorable.

## CI Pattern

- Run fast smoke profile on PRs.
- Run longer stateful/negative campaigns nightly.
- Publish JUnit/Allure artifacts for triage.

## Resources

- https://github.com/schemathesis/schemathesis
- https://schemathesis.readthedocs.io/
- https://schemathesis.readthedocs.io/en/stable/guides/triage/
- https://schemathesis.readthedocs.io/en/stable/guides/config-optimization/
