---
name: software-architecture
description: "Design and evolve high-quality software systems from concept through implementation: clarify outcomes and constraints, choose the simplest fitting architecture, define boundaries and contracts, address data, security, reliability, observability, testing, and delivery, then simplify and verify the result. Use when creating, refactoring, reviewing, or simplifying cross-language software, modules, APIs, services, or system architecture."
license: MIT
compatibility: "Language-agnostic. Pair with the relevant language, testing, debugging, security, and performance skills for concrete implementation and verification."
metadata:
  author: AeonDave
  version: "1.0"
---

# Software Architecture

Use this skill to turn an intended outcome into a design that is understandable, testable, operable, secure, and changeable. Architecture is a set of consequential decisions and constraints, not a mandatory folder layout or a collection of patterns.

## Activate when

- Designing a new application, library, service, API, worker, or subsystem.
- Refactoring a coupled, fragile, or hard-to-test codebase.
- Choosing between a simple module, layered design, modular monolith, event-driven design, or services.
- Defining domain boundaries, public contracts, data ownership, or integration seams.
- Reviewing architecture or recently changed code for quality and unnecessary complexity.
- Simplifying code while preserving behavior.

For a small, local change, use the smallest applicable parts of the workflow. Do not impose a full architecture exercise on a one-function fix.

## Operating rules

- Inspect the repository, build system, tests, runtime, deployment model, and existing conventions before proposing structure.
- State assumptions and unknowns. Do not invent requirements, scale, availability targets, or domain boundaries.
- Start with the simplest design that satisfies current requirements and has a credible path for known change. Add complexity only for a named constraint.
- Treat every boundary as a cost: serialization, network failure, deployment, versioning, monitoring, and cognitive load must have a reason.
- Prefer domain-specific names and cohesive modules. Avoid dumping grounds such as `utils`, `helpers`, `common`, or `shared`.
- Keep business rules independent from frameworks and infrastructure when that isolation buys testability or protects a volatile dependency; do not create interfaces and layers mechanically.
- Preserve existing behavior during refactors. Separate behavior changes from structural changes when possible.
- Use established libraries and managed services after checking fit, maintenance, security, license, and operational cost. Do not rebuild commodity capabilities without a concrete reason.
- Do not claim an architecture or refactor is complete until focused tests, relevant broader checks, static checks, and the final diff have been reviewed.

## Workflow

### 1. Frame the problem

Write a short design brief before coding:

- User and system outcome; primary use cases and important failure cases.
- In scope, out of scope, assumptions, constraints, and existing assets to preserve.
- Actors, trust boundaries, external dependencies, data sensitivity, and ownership.
- Quality attributes expressed as scenarios with a target and a measurement: for example p95 latency, throughput, availability, RTO/RPO, consistency, deployability, cost, or auditability.
- Risks and unknowns that could change the design.

If the outcome or a material constraint is unknowable, stop at the ambiguity and ask; do not compensate with speculative architecture.

### 2. Model behavior and boundaries

Identify commands, queries, state transitions, invariants, domain vocabulary, and integration events. Group code by business capability and change ownership, not by nouns alone.

- Keep a rule in the domain when it protects an invariant or expresses domain behavior.
- Keep orchestration in an application/use-case layer when it coordinates domain work and ports.
- Keep transport, persistence, serialization, framework, and vendor code at the edges.
- Use a bounded context only when a model or language genuinely differs. Do not split a simple CRUD flow merely to imitate DDD.
- Define who owns each piece of data and which component is the source of truth.

Load [references/boundaries-and-patterns.md](references/boundaries-and-patterns.md) when selecting or reviewing Clean, Hexagonal, DDD, modular-monolith, microservice, or event-driven boundaries.

### 3. Select the smallest fitting topology

Compare at least the current simplest option with the proposed alternative. Record the driver, rejected alternatives, trade-offs, and a verification plan.

- **Simple module or layered monolith:** default for a small or cohesive problem.
- **Modular monolith:** default when multiple business capabilities need isolation but independent deployment is not yet a proven requirement.
- **Hexagonal/Clean boundary:** use when framework, storage, transport, or vendor volatility and test isolation justify explicit ports and adapters.
- **Microservices:** use only when independent deployment, scaling, fault isolation, team ownership, or data autonomy outweigh distributed-system cost.
- **Event-driven design:** use when asynchronous work, fan-out, temporal decoupling, or independent consumers is a real requirement; define delivery, ordering, replay, and idempotency semantics.

Do not select a pattern because it is fashionable. A pattern is useful only when its constraints produce a required property.

Load [references/architecture-decisions.md](references/architecture-decisions.md) for the decision matrix, quality-attribute scenarios, and ADR template.

### 4. Make dependencies and contracts explicit

- Keep the dependency direction deliberate: stable business policy should not depend on delivery or infrastructure details.
- Put interfaces at a boundary where an implementation can vary or where a test needs a stable seam; avoid an interface for every class.
- Translate external DTOs, ORM records, vendor errors, and wire formats at the edge. Do not leak them into the domain.
- Define API contracts, validation ownership, error semantics, idempotency, timeouts, pagination, compatibility, and authentication/authorization at the boundary.
- Keep the composition root responsible for wiring implementations. Avoid hidden service locators and global mutable state.

### 5. Design data and failure behavior

Decide transaction boundaries, consistency guarantees, concurrency rules, retention, migration strategy, and recovery behavior before implementation. Strong consistency belongs where an invariant requires it; eventual consistency is a deliberate contract, not an accidental side effect.

For remote calls, define timeout and cancellation behavior first. Retry only failures that are transient and operations that are safe or idempotent; use bounded exponential backoff with jitter. Define duplicate delivery, partial failure, degraded behavior, and recovery for every asynchronous or distributed flow.

Load [references/production-quality.md](references/production-quality.md) for data, API, security, resilience, observability, testing, and delivery gates.

### 6. Implement in verifiable slices

- Build a thin vertical slice that proves the riskiest boundary or quality attribute early.
- Keep modules cohesive and APIs small. Use early returns and explicit control flow when they improve readability; do not chase arbitrary line-count limits.
- For persistent code, write a test, reproducer, contract, or other verification gate before implementation when practical. Pair with `test-driven-development` and the language-specific testing skill.
- Run formatter, compiler/type checker, linter, focused tests, and integration/contract checks at the smallest useful cadence.
- Make migrations backward-compatible where rolling deployment or rollback requires it. Release schema, code, and consumers in a safe order.

### 7. Simplify before handing off

Review only the requested or recently changed scope unless a wider review is explicit. Preserve outputs, side effects, error behavior, timing contracts, and public compatibility.

- Remove speculative configuration, dead code, duplicate logic, and indirection that has no boundary value.
- Flatten unnecessary nesting and pass-through layers; prefer clear named steps over clever one-liners or dense nested conditionals.
- Merge abstractions used only once when they obscure the behavior; keep abstractions that protect a real volatility boundary or invariant.
- Replace generic names with names from the domain. Do not turn simplification into an unrelated cleanup.

Load [references/simplification-and-review.md](references/simplification-and-review.md) for the behavior-preserving simplification loop and review checklist.

### 8. Verify and document

Before completion, verify:

- Requirements and quality-attribute targets are mapped to implementation and tests.
- Dependency and data ownership rules are enforced or explicitly accepted.
- Error, security, migration, observability, and recovery behavior are covered at relevant boundaries.
- Focused tests pass, then relevant broader tests, static checks, builds, and architecture/contract checks pass.
- The diff contains no speculative or orthogonal edits, and documentation matches the implementation.
- Each consequential decision has a short ADR or equivalent record. Supersede changed decisions; do not silently rewrite history.

## Resources

Load only the reference needed for the current subtask:

| Reference | Load when |
|---|---|
| [references/architecture-decisions.md](references/architecture-decisions.md) | Choosing an architecture, comparing alternatives, defining quality attributes, or writing an ADR. |
| [references/boundaries-and-patterns.md](references/boundaries-and-patterns.md) | Applying or reviewing Clean Architecture, Hexagonal Architecture, DDD, modular monoliths, microservices, or event-driven boundaries. |
| [references/production-quality.md](references/production-quality.md) | Designing data/API contracts, security, failure handling, reliability, observability, testing, or delivery. |
| [references/simplification-and-review.md](references/simplification-and-review.md) | Simplifying or reviewing changed code while preserving behavior and scope. |

Pair this skill with `code-guidelines` for agent discipline, `test-driven-development` for persistent changes, `testing-reliability` for test trustworthiness, and the relevant language-specific pattern/testing skill for syntax and tooling.
