# Architecture Decisions

Use this reference when a design choice affects dependencies, data, deployment, reliability, security, cost, or the ability to change the system. Keep the decision proportional to its blast radius.

## Contents

- [Decision inputs](#decision-inputs)
- [Quality-attribute scenarios](#quality-attribute-scenarios)
- [Style selection](#style-selection)
- [ADR template](#adr-template)
- [Decision review](#decision-review)

## Decision inputs

Capture facts before naming a pattern:

| Input | Questions |
|---|---|
| Outcome | What user or business result must become true? How will it be observed? |
| Change | What is likely to change independently? Who owns those changes? |
| Scale | What volume, concurrency, payload size, and growth are evidenced? |
| Reliability | What must remain available, what may degrade, and what are RTO/RPO targets? |
| Data | Who owns each fact? Which invariants need one transaction? What may be eventually consistent? |
| Security | What are the trust boundaries, identities, privileges, secrets, and data classifications? |
| Operations | How will it be deployed, migrated, monitored, rolled back, and supported? |
| Team | Can the team build and operate the chosen topology? Does ownership match boundaries? |
| Constraints | Existing APIs, runtime, budget, latency, regulatory, compatibility, or migration constraints? |

Separate facts, assumptions, and decisions. An assumption that could change the topology is a risk to validate early.

## Quality-attribute scenarios

Avoid labels such as “scalable” or “secure” without a scenario. Use:

`When [stimulus] occurs in [context], [component] shall [response] within [measure], while preserving [constraint].`

Examples:

- When 500 concurrent clients submit valid requests, the API returns success or a documented rejection within the p95 latency target, without duplicate state changes.
- When the payment provider times out, the order remains recoverable, the client receives an unambiguous status, and no unsafe retry charges twice.
- When a non-breaking schema is deployed before an older consumer, both versions continue to process the contract during the rollout window.
- When a user lacks permission for a resource, the system denies access without exposing whether protected data exists.
- When a worker restarts after acknowledging a message, processing can be replayed or reconciled without corrupting the invariant.

For each important scenario, name the test, metric, log, trace, or operational exercise that will verify it.

## Style selection

| Option | Choose when | Costs and rejection signals |
|---|---|---|
| Simple module or layered monolith | One deployable unit and one model are sufficient; changes are cohesive. | Can become coupled if boundaries are not named and enforced. |
| Modular monolith | Capabilities need internal isolation, independent tests, or future extraction, but distributed deployment is not justified. | Requires explicit module APIs and ownership; shared database access can erode boundaries. |
| Hexagonal/Clean boundary | External technology changes, domain rules are valuable, and tests need to run without infrastructure. | More wiring and mapping; harmful when the domain is trivial or the ports are pass-through copies. |
| Microservices | A capability has independent deployment/scale/fault needs, clear ownership, and data autonomy. | Network failures, versioning, tracing, deployment, consistency, and operations become product work. |
| Event-driven | Work is naturally asynchronous, fan-out or replay is useful, or producers and consumers must be decoupled. | Ordering, retries, duplicates, poison messages, replay, schema evolution, and eventual consistency must be designed. |

Use the least powerful option that meets the scenarios. “We may scale later” is not evidence for a distributed boundary; a modular boundary can preserve that option at lower cost.

## ADR template

Copy this structure into the repository's established decision-record location. Use one record per consequential decision.

```markdown
# ADR: Decision title

- Status: proposed | accepted | superseded | rejected
- Date: YYYY-MM-DD
- Owners: team or role

## Context

State the problem, outcome, constraints, facts, assumptions, and quality-attribute scenarios.

## Decision

State the chosen structure or rule precisely, including its boundary and scope.

## Alternatives considered

For each serious alternative, record the benefit, cost, risk, and reason for rejection.

## Consequences

List positive consequences, new obligations, failure modes, migration work, and operational cost.

## Verification

Name tests, measurements, review gates, or experiments that can falsify the decision.

## Revisit trigger

State the evidence that would justify changing this decision.
```

Do not write an ADR for every implementation detail. Write one when reversing the choice would be costly, surprising, or cross-cutting.

## Decision review

Before accepting a design, ask:

- Does each component have one clear responsibility and one reason to change?
- Does each boundary reduce a demonstrated change, failure, security, or ownership risk?
- Can the riskiest quality attribute be measured before the design is fully built?
- Are data ownership, consistency, idempotency, and migration order explicit?
- Can the system be tested without unavailable external systems where the business rule is local?
- Is the operational burden compatible with the team and delivery model?
- What is the smallest design that would pass the same scenarios?
- Which assumption, if false, would invalidate the decision?

If the answer depends on an unmeasured claim, create a small spike or test with a stated expiry. Do not let a spike become production architecture by inertia.

## Source anchors

- [Architecture Decision Record — Martin Fowler](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html)
- [Architecture styles — Microsoft Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/)
- [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework)
