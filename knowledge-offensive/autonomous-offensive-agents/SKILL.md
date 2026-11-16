---
name: autonomous-offensive-agents
description: "Deploy and operate LLM-driven offensive orchestrators (ARTEX-class agents, graph-search harnesses like Cairn, kill-chain swarms) on authorized engagements: when they earn their cost, their architecture patterns, and their detection fingerprint — request pacing, retry shapes, LLM artifacts in traffic — that defender baselines now flag. Use when considering autonomous agents for an assessment or when your agent traffic must survive agentic detection."
license: MIT
compatibility: "Agent workflow guidance; harness-agnostic. The tool landscape churns in weeks (forks outlive takedowns) — verify any named framework's current state before relying on it."
metadata:
  author: AeonDave
  version: "1.0"
---

# Autonomous Offensive Agents

LLM-driven orchestrators now execute the kill chain autonomously: planner + parallel executors, goal graphs mapped to target assets, tools installed on demand, MCP integration, Kali containers. Defenders responded with agentic-specific detection — so operating one (or anything that behaves like one) without knowing its fingerprint burns the engagement. This skill covers both sides: when these agents earn their cost, and how they are seen.

## Landscape (pattern families, not tool manuals)

Per-tool skill rot is days-to-weeks here — the first mass-adopted orchestrator was taken down by its author within months and 12,000+ forks survived it. Select by pattern:

| Family | Shape | Strengths | Limits |
|---|---|---|---|
| **Planner + parallel executors** (ARTEX-class) | goal/lead/finding graph over a target asset graph; root container; installs tools as needed | speed-of-inference parallel scanning, systematic coverage | no built-in post-exploitation or stealth; loudest fingerprint |
| **Graph-state search harness** (Cairn-class) | facts/leads state graph; dispatches to existing coding-agent harnesses | reuses proven harnesses; clean state model | inherits harness tool limits |
| **Supervisor/executor kill-chain swarm** | specialized agents per phase (recon → exploit → privesc → exfil → evasion), ATT&CK-mapped, shared memory | long multi-step chains; role separation | coordination overhead; per-phase context loss |
| **Containerized tool-runner** (PentAGI-class) | agent directly orchestrates nmap/sqlmap/metasploit/etc. in a container | real tool coverage out of the box | heavy; tool telemetry unmodified |

Commercial autonomous platforms (continuous-attack surface testing) exist on the same patterns — the selection logic below applies to both.

## When they earn their cost

- **Breadth over depth**: wide attack-surface triage across many hosts/endpoints where each unit is low-value — autonomous coverage beats manual toil.
- **Known vuln classes at scale**: agents excel at re-running the standard checks (exposed panels, default creds, unauth RCE, JWT weaknesses, subdomain takeover) across thousands of targets.
- **Not** business logic, novel exploit chains, multi-party social engineering, or anything requiring engagement judgment — that stays human (hybrid model: agent for recon/triage/known-patterns, operator for logic/creativity/validation).
- **Benchmark reality**: frontier agents exploit ~87% of one-day CVEs *when handed the advisory*, but ~13% of unseen real CVEs and near-zero on hard targets — budget them for known gaps at scale, not novel work.

Deployment baseline: container per engagement, tool allowlist, no ambient credentials on the agent host — the agent installs what it needs; give it nothing it shouldn't spend.

## The detection fingerprint (what defender baselines flag)

These observables are deployed in production (CDN/WAF-scale) and were derived from real incident traffic — assume they watch your agent:

- **No think-time**: rapid sequential requests at machine cadence (~60-70 req/min sustained from one source is a named incident signature). Pace: human-scale delays, jittered.
- **Self-correcting retry shape**: same endpoint, varied parameters, consistent on-failure adaptation. A scanner retries blindly; an agent retries *differently* — that difference is the signature.
- **LLM artifacts in traffic**: verbose structured JSON, natural-language reasoning fragments, or tool output echoed in POST bodies and parameters. Scrub agent context from anything that crosses the wire.
- **Synthetic user agents / payload style**: generated UAs and templated payloads drift from population baselines. Use realistic UA strings and payload shapes from actual tool versions.
- **Resource-creation naming**: mass-created resources with correlated prefixes and alphanumeric suffixes. Randomize per-resource names independently.
- **Volume anomalies**: bulk database-dump request patterns (hundreds of dump requests per hour). Throttle and distribute.
- **Headless-browser behavior**: bot scoring flags headless browsers and synthetic interaction patterns.

Identity path (from real incidents): static non-expiring CI/CD tokens with broad cross-environment scope are the preferred first foothold — no IP restrictions, no rate limits, chained from cloud tenant to tenant. On defense-informed engagements, treat token hygiene as the primary target surface.

## Operating under agentic detection

1. **Pace like a human**: inject think-time proportional to response complexity; jitter every delay.
2. **Sanitize egress**: agent reasoning never crosses the wire — strip LLM context from payloads, parameters, and UA strings before any request leaves the operator side.
3. **Distribute origin and timing**: a single IP sustaining machine-rate requests is the loudest signal; distribute and throttle.
4. **Match population**: UA strings, header order, and payload formatting drawn from real-world distributions, not generated defaults.
5. **Stage loudly-scoped work**: mass scanning/dump phases belong to a deliberate noisy window (or are cut); precision work should not inherit the scanning fingerprint.
6. **Assume AI-scale scanning is expected**: defenders already run agentic-detection by default (cloud-scale deployment since 2026) — an agent that "passes" because nothing fired yet is not stealthy, just early.

## Gotchas

- Forks outlive takedowns: a framework's author deleting the repo does not reduce its prevalence — verify current fork state and known detections before deploying anything derived from it.
- Autonomous agents chain what they find — including things out of your authorization scope. Constrain targets at the harness level, not by instruction alone; an agent that discovers a reachable adjacent tenant will use it (see `rules-of-engagement`).
- Tool telemetry flows unmodified: the agent runs nmap/sqlmap/etc. with their default signatures; wrapper stealth does not propagate to wrapped tools.
- Offline "zero-refusal" offensive LLMs on local GPUs are their own observable on defense-side EDR — running them on the engagement VM is a choice, not a default.

## References

- Cloudflare, [Adapting to AI penetration testing orchestrators](https://blog.cloudflare.com/adapting-to-ai-penetration-testing-orchestrators/) (Nov 2026 — detection pillars, incident IOCs, ARTEX/forks traffic data) · Resecurity, [When AI Becomes the Attacker](https://www.resecurity.com/blog/article/when-ai-becomes-the-attacker-understanding-autonomous-offensive-security-agents) (2026 — tool profiles incl. T3MP3ST's 8-agent ATT&CK-mapped kill chain, defender behavioral detections) · AppSec Santa, [AI Pentesting Agents 2026: 39+ Tools Tested](https://appsecsanta.com/research/ai-pentesting-agents-2026) (Apr 2026 — 39+ projects across 6 architecture patterns; the lab-to-real benchmark gap)
- Related: [`offensive-orchestration`](../offensive-orchestration/SKILL.md) (coordinating your own subagent workers on investigations), [`adversary-emulation-planning`](../adversary-emulation-planning/SKILL.md) (the plan these agents execute), [`llm-technique`](../../offensive-techniques/llm-technique/SKILL.md) (attacking LLMs — the inverse problem), [`rules-of-engagement`](../../behaviours/rules-of-engagement/SKILL.md) (scope constraints for autonomous chaining)
