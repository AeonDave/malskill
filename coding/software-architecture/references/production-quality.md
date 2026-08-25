# Production Quality

Use this reference when architecture must survive real users, hostile inputs, failures, deployments, or long-term operation. Apply the relevant sections; do not add infrastructure because a checklist mentions it.

## Contents

- [Quality gates](#quality-gates)
- [Data and API contracts](#data-and-api-contracts)
- [Security](#security)
- [Reliability and failure handling](#reliability-and-failure-handling)
- [Observability](#observability)
- [Testing and delivery](#testing-and-delivery)

## Quality gates

Turn quality attributes into observable acceptance criteria:

| Attribute | Design question | Evidence |
|---|---|---|
| Correctness | Which invariants and state transitions must never be violated? | Domain tests, property tests, contract tests, audit records |
| Security | Where is input untrusted and what may each identity do? | Threat model, authorization tests, dependency/config checks |
| Reliability | How does the system behave during dependency, process, and data failure? | Failure tests, recovery drills, SLO/error-budget signals |
| Performance | Which workload and percentile matter? | Representative benchmark or load test; profile before optimizing |
| Operability | How will an operator detect, diagnose, deploy, rollback, and recover it? | Runbook, health signals, correlated telemetry, deployment checks |
| Changeability | Which changes should be local and independently verifiable? | Module/contract tests, dependency checks, small deployable slices |
| Cost and sustainability | Which resource use is material and what is the budget? | Usage metrics, capacity assumptions, cost review |

Do not use “production-ready” as a substitute for evidence. Mark unknowns and define the next verification step.

## Data and API contracts

### Ownership and consistency

- Assign one authoritative owner for each business fact.
- Keep invariants that must be atomic in one transaction and one consistency boundary where possible.
- Name the consistency model of every cross-boundary read: strong, read-your-writes, bounded staleness, or eventual.
- For eventual consistency, define acceptable staleness, user-visible intermediate states, reconciliation, and repair.
- Make writes idempotent with a natural key or idempotency key when retries, queues, or client replay are possible.

### Schema and migration safety

- Version public schemas deliberately; prefer additive changes before removals.
- For rolling deployments, use expand, migrate, contract: introduce compatible schema, deploy readers/writers, backfill or migrate, then remove old shape only after all consumers move.
- Keep migrations observable, restartable, and bounded. Test them against realistic data volume and rollback limits.
- Never let a convenience query bypass the data owner or silently create a second source of truth.

### API boundaries

- Validate syntax and size at the edge; validate domain invariants in the domain/application layer.
- Specify success, rejection, authentication, authorization, not-found, conflict, rate-limit, and dependency-failure semantics.
- Define timeouts, pagination, filtering, ordering, rate limits, idempotency, and compatibility behavior.
- Return stable application errors; do not expose stack traces, SQL, vendor errors, or sensitive existence information.
- Contract-test consumers and providers when they evolve independently. Keep wire models separate from domain models.

## Security

Integrate security into design and implementation, not just the final review:

- Map trust boundaries, identities, assets, entry points, and abuse cases.
- Authenticate at the appropriate boundary and authorize every protected operation using server-side policy. Do not trust client-provided roles or object ownership.
- Apply least privilege to users, services, databases, files, queues, and deployment identities.
- Validate untrusted input, constrain resource use, and encode output for its destination. Treat deserialization, templates, file paths, commands, and URLs as high-risk boundaries.
- Keep secrets out of source, logs, traces, errors, fixtures, and telemetry. Use managed secret storage and rotation appropriate to the environment.
- Pin and review dependencies, generate reproducible builds where practical, and define vulnerability response ownership.
- Record security-relevant events without logging credentials, tokens, full personal data, or raw sensitive payloads.

Pair with the repository's security and language-specific skills for threat modeling, secure coding, dependency analysis, and concrete commands.

## Reliability and failure handling

For every dependency or asynchronous boundary, specify:

- Timeout, cancellation, and resource limit.
- Retry eligibility, maximum attempts, exponential backoff, jitter, and idempotency condition.
- Behavior for partial success, duplicate delivery, out-of-order delivery, and permanent failure.
- Queue capacity, backpressure, poison-message handling, and dead-letter/replay process.
- Fallback or graceful degradation that does not violate a business invariant.
- Recovery, reconciliation, and operator action.

Use circuit breakers, bulkheads, caches, hedging, or queues only when a measured failure or load mode justifies their complexity. A retry storm or unbounded queue can turn a transient failure into an outage.

Define reliability from the user's outcome, not only process uptime. Where the system is important enough, choose SLIs and SLOs that expose correctness, latency, availability, and freshness; connect alerts to an action and a runbook.

## Observability

Instrument the critical user journeys and boundary crossings:

- **Metrics:** request rate, error rate, latency percentiles, saturation, queue depth, dependency health, and business outcomes.
- **Structured logs:** state transitions, rejections, failures, and operator-relevant context; use severity consistently and redact sensitive data.
- **Traces:** propagate correlation across process and network boundaries; record meaningful spans for external calls and asynchronous handoffs.
- **Health:** distinguish liveness from readiness and dependency health. Do not report healthy when the process is alive but cannot serve its contract.

Telemetry must answer what happened, for whom or which operation, where, and why without requiring a code change during an incident. Control cardinality, retention, sampling, and cost.

## Testing and delivery

Use a test portfolio that matches boundaries:

- Domain/unit tests for invariants and deterministic rules.
- Application tests for use-case orchestration and error decisions.
- Contract tests for APIs, messages, and module boundaries.
- Integration tests for real persistence, migrations, queues, and critical adapters.
- End-to-end tests for a few highest-value journeys, not every branch.
- Property, fuzz, load, failure, and recovery tests when their risk justifies them.

Keep tests deterministic and meaningful; coverage alone is not evidence. Run cheap checks continuously, isolate external dependencies deliberately, and verify that a test fails for the intended reason when it protects a bug.

Deliver in small reversible changes. Automate build, test, migration validation, deployment, telemetry checks, and rollback. Use feature flags or compatible dual-read/write only with an explicit removal condition; temporary mechanisms become architecture when nobody owns their deletion.

## Source anchors

- [AWS Well-Architected Framework pillars](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html)
- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- [OpenTelemetry observability primer](https://opentelemetry.io/docs/concepts/observability-primer/)
- [Google Cloud reliability pillar](https://docs.cloud.google.com/architecture/framework/reliability)
