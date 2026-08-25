# Boundaries and Patterns

Use this reference when a project needs explicit dependency direction, domain boundaries, or a choice among monolith, modular monolith, service, and event-driven designs. Patterns describe constraints and trade-offs; they do not prescribe identical folders in every language.

## Contents

- [A common boundary model](#a-common-boundary-model)
- [Clean and Hexagonal Architecture](#clean-and-hexagonal-architecture)
- [DDD where it earns its cost](#ddd-where-it-earns-its-cost)
- [Modular monoliths](#modular-monoliths)
- [Microservices and events](#microservices-and-events)
- [Boundary checks and anti-patterns](#boundary-checks-and-anti-patterns)

## A common boundary model

Use names that fit the codebase. A useful conceptual model is:

| Area | Owns | Must not know about |
|---|---|---|
| Domain | Invariants, domain behavior, value semantics, domain events | HTTP, ORM, queues, vendor SDKs, framework lifecycle |
| Application | Use-case orchestration, transaction intent, authorization policy coordination, ports | Transport serialization and vendor implementation details |
| Adapters | Mapping between ports and external protocols or persistence | Other adapter internals and hidden domain rules |
| Infrastructure/composition | Framework startup, configuration, concrete wiring, migrations, telemetry setup | Business decisions that belong in domain/application |

This is a dependency rule, not a mandatory four-layer folder tree. A small component may combine areas until a real change or test boundary appears.

Prefer vertical slices by capability when they make ownership and change flow clearer. Keep shared code narrow, stable, and domain-neutral; duplicated mapping at a boundary is often cheaper than a shared abstraction that couples unrelated modules.

## Clean and Hexagonal Architecture

Clean Architecture emphasizes dependency flow toward stable business rules. Hexagonal Architecture emphasizes a domain core surrounded by ports and adapters. They can express the same useful constraint:

1. The core exposes behavior and ports needed by the application.
2. Inbound adapters translate commands or requests into application inputs.
3. The application coordinates work and invokes outbound ports.
4. Outbound adapters implement persistence, network, filesystem, messaging, or vendor integrations.
5. A composition root wires concrete adapters to ports.

Use a port when at least one is true:

- The implementation is volatile, external, expensive, or unavailable in unit tests.
- The boundary has a contract that several adapters must satisfy.
- The business flow needs a stable seam for a meaningful test or migration.

Do not add a port merely because a class exists. A pass-through interface that mirrors one concrete method increases indirection without protecting a decision.

Keep mapping explicit at boundaries. An ORM entity, HTTP DTO, queue envelope, and domain object may share fields but have different lifecycle, validation, and compatibility concerns.

## DDD where it earns its cost

Use DDD language to clarify a difficult domain, not as a ceremony for every feature.

- **Ubiquitous language:** use terms that stakeholders and code share; resolve synonyms before they become separate models accidentally.
- **Bounded context:** isolate a model when rules, vocabulary, ownership, or change cadence differ. The same word may legitimately mean different things in different contexts.
- **Entity:** use identity when continuity matters despite attribute changes.
- **Value object:** use immutable value semantics when validation and equality belong together, such as a money amount with currency or a normalized identifier.
- **Aggregate:** define the smallest consistency boundary that can enforce its invariants. Do not load or lock an entire graph for convenience.
- **Repository:** persist and reconstitute an aggregate or meaningful domain collection; do not expose query mechanics as domain behavior.
- **Domain event:** record a fact that occurred when consumers need it. Define publication timing, durability, ordering, retries, and duplicate handling.
- **Application service:** coordinate a use case; do not turn it into a dumping ground for rules that belong in the model.

Reject an anemic model when invariants and state transitions are scattered across controllers or handlers. Reject an over-rich model when it becomes a transaction script with infrastructure concerns or when the domain has no meaningful behavior.

## Modular monoliths

Treat a modular monolith as a real architecture, not an unstructured monolith with folders:

- Each module owns its domain rules and persistence access.
- Cross-module calls use explicit APIs or events, not direct table access or internal imports.
- Shared kernel code is small, stable, and governed; copy local code when coupling costs more than duplication.
- Tests verify public module contracts and important dependency rules.
- The composition root is the only place that assembles modules and infrastructure.

Design modules so an eventual extraction is possible, but do not pay the network and operations cost before extraction is justified. A module that cannot be tested or deployed safely may still be the right boundary if it reduces cognitive and change coupling.

## Microservices and events

Split a service around a business capability with a clear owner, data autonomy, and independently meaningful deployment or scaling. “Small” is not a sufficient criterion.

Before creating a service, answer:

- What can it deploy, scale, fail, and be secured independently?
- Who owns its data and contract?
- What happens when a dependency is slow, unavailable, duplicated, reordered, or on an incompatible version?
- How are traces, logs, alerts, local development, integration tests, and rollback handled?
- What is the migration path from the current boundary?

For asynchronous flows, specify the message contract, schema evolution, delivery guarantee, ordering key, deduplication key, retry/backoff policy, dead-letter handling, replay behavior, and observability. Use an outbox or equivalent when a state change and its event must be made durable together. Use sagas or explicit compensating actions when a business process spans independent transaction boundaries; do not pretend a distributed transaction is atomic when it is not.

## Boundary checks and anti-patterns

| Smell | Risk | Better response |
|---|---|---|
| Controller handles business rules and SQL | Transport and storage changes break policy | Move policy to domain/application; keep controller translation-only |
| Domain imports framework or vendor types | Core cannot be tested or reused independently | Map at the adapter boundary |
| Generic `shared` or `utils` package | Unclear ownership and accidental coupling | Move code to the capability that owns the rule |
| Repository returns ORM records | Persistence leaks into callers | Return domain or application models; map explicitly |
| One giant aggregate or transaction | Locking, performance, and change coupling | Split by invariant and consistency requirement |
| Service per table or noun | Network and operational cost without capability ownership | Split by business capability and independent lifecycle |
| Event for every method call | Hidden control flow and hard replay semantics | Publish durable business facts only when consumers need them |
| Interface for every concrete class | Indirection with no substitution value | Introduce seams at volatility or test boundaries |
| Shared database across services | Schema changes require coordinated deployment | Give one owner per fact; integrate through contracts |

Use architecture tests, import rules, module contract tests, or dependency analysis only when they protect a boundary that matters. A failing architecture rule should explain the risk it prevents.

## Source anchors

- [Microservices architecture style — Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices)
- [Data considerations for microservices — Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations)
