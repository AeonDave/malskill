# Web and API fuzzing methodology

## Objective

Find correctness, security, and reliability bugs by combining schema-aware generation with stateful sequencing.

## Choose approach by API maturity

1. **Good OpenAPI/GraphQL schema exists**
	- Use schema-driven generation first.
	- Add stateful linking so producer IDs feed consumer requests.

2. **Partial/weak schema**
	- Combine traffic capture + manual parameter dictionaries.
	- Prioritize fixing schema gaps that block stateful depth.

3. **No schema**
	- Start with endpoint discovery and traffic-based corpus.
	- Build a minimal contract over time to reduce random-noise failures.

## Campaign sequence

1. **Smoke run**
	- Establish baseline failure classes and auth/session viability.

2. **Failure triage order**
	- First: undocumented status noise (contract mismatch).
	- Second: schema conformance mismatches.
	- Third: server errors / crash-like behavior (highest severity).

3. **Stateful depth enablement**
	- Fix producer operations that fail frequently (POST/PUT that create resources).
	- Add links/dependency hints where automatic inference misses relations.

4. **Coverage tuning**
	- Increase example budget for release/security runs.
	- Continue after failures to map broader defect surface.

## Authentication and session strategy

- Keep token/session refresh deterministic and observable in logs.
- Separate auth failures from business-logic failures in buckets.
- For quota/rate-limited APIs, use throttle only as needed and document impact.

## Reproducibility and replay

- Preserve request/response traces with sequence IDs.
- Replay minimal failing sequence after each fix candidate.
- Keep a regression pack of representative failures by class.

## Common pitfalls

- Staying in stateless mode and only testing invalid IDs (404-heavy noise).
- Fixing generated grammars directly before correcting spec/examples/annotations.
- Running high-aggression fuzzing in production-like environments without health monitoring.