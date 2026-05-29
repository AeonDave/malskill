# Attack chain scoring and prioritization

## Purpose

Correlate findings from multiple sources into prioritized multi-step attack chains with confidence levels, scoring, detection-aware path selection, and clear handoffs when evidence is missing.

## Chain link types

Every attack chain is a sequence of these link types:

1. **Initial Access** — How you get in (phishing, public exploit, default creds, VPN creds)
2. **Execution** — How you run code (web shell, command injection, macro, script)
3. **Persistence** — How you stay in (scheduled task, service, registry, cron)
4. **Privilege Escalation** — How you go up (kernel exploit, misconfig, token impersonation)
5. **Defense Evasion** — How you avoid detection (living off the land, log clearing, timestomping)
6. **Credential Access** — How you get more creds (Mimikatz, Kerberoast, LSASS dump)
7. **Discovery** — How you map the environment (AD enum, network scanning, file shares)
8. **Lateral Movement** — How you move across (PSExec, WinRM, RDP, SSH, SMB)
9. **Collection** — How you gather data (file access, database queries, email access)
10. **Exfiltration** — How you get data out (HTTP, DNS, cloud storage)
11. **Impact** — What business impact you demonstrate (domain admin, data access, ransomware simulation)

## Path scoring

| Factor | Weight | Description |
|--------|--------|-------------|
| Objective alignment | 25% | Does the path answer the mission without expanding scope? |
| Evidence quality | 25% | Are prerequisites confirmed by artifact, replay, source path, log, capture, hash, or transcript? |
| Operational cost | 20% | Noise, state change, reversibility, detection, cleanup, and approval burden |
| Probability of success | 20% | How likely is each step to work based on confirmed findings and environment fit? |
| Dependency count | 10% | How many assumptions, tools, credentials, or prior steps must hold? |

## Confidence levels

- **Confirmed**: Every material link is validated by direct artifact, replay, source path, log, capture, hash, or transcript.
- **High confidence**: Most links are confirmed and remaining links have strong primary-source or environment-specific evidence.
- **Moderate confidence**: Some links fit known behavior or versions, but reachability, config, or privilege is not proven.
- **Speculative**: Chain depends on assumptions; use only as a candidate path with a resolving test.

## Chain comparison matrix

When multiple paths exist, present them side by side:

| Metric | Chain 1 | Chain 2 | Chain 3 |
|--------|---------|---------|---------|
| Score | 85/100 | 72/100 | 65/100 |
| Steps | 4 | 6 | 3 |
| Confidence | Confirmed | High | Moderate |
| Time | 2 hours | 4 hours | 1 hour |
| Detection Risk | Medium | Low | High |
| Impact | Domain Admin | Database Access | Web Shell |
| Requires | Network access | Valid creds | Public exploit |

## Orchestration cost matrix

When deciding whether to add, keep, or retire agents, score worker branches separately from attack chains:

| Factor | Prefer more agents when... | Prefer fewer agents when... |
|---|---|---|
| Independence | branches have separate inputs, oracles, and merge points | branches share target state, files, or prerequisite evidence |
| Signal rate | workers can return decisive evidence in parallel | outputs duplicate each other or require heavy synthesis |
| Target noise | branches are read-only, offline, or isolated labs | branches touch live target, mutate state, or risk throttling |
| Model fit | cheap/standard workers can handle bounded tasks | premium/rescue would idle behind weak context |
| Merge cost | output format is predefined and comparable | contradictions require manual reconstruction |

Use this matrix dynamically. Expand for independent evidence, shrink after convergence, and suspend branches that no longer answer the next cheapest test.

## Model tier selection

| Tier | Use for | Avoid when |
|---|---|---|
| Cheap | triage, inventory, route map, negative filtering, source skim | nuanced exploit chain or ambiguous contradiction |
| Standard | default worker, researcher, reviewer, lab-builder | stuck branch with repeated failed pivots |
| Diverse standard | useful second opinion with different context/method | same prompt would produce duplicate reasoning |
| Premium | bounded synthesis after concrete dead end and sharp question | uncertainty without cheap validation |
| Rescue | one critical stuck branch with exact evidence and failed attempts | multiple broad branches or missing primary evidence |

One premium or rescue branch at a time unless the engagement explicitly budgets for more.

## Local replica scoring

Treat local reproduction as strong evidence only when:

- version/config/runtime matches target evidence;
- test answers one narrow disputed behavior;
- oracle is explicit before execution;
- setup and output are reproducible;
- divergence from target behavior is recorded.

If local tooling differs from the target stack, target-version behavior wins. Parser/filter bugs, framework defaults, middleware order, sandbox behavior, race timing, and serialization quirks must be validated against the target or a faithful replica before chain confidence rises.

## Chain output format

```
## Attack Chain Analysis

### Environment Summary
- {X} hosts enumerated
- {Y} vulnerabilities identified
- {Z} credentials obtained
- {N} potential attack chains identified

### Chain 1: {Descriptive Name} (Score: {X}/100)
**Confidence**: {Confirmed/High/Moderate/Speculative}
**Estimated Time**: {hours/days}
**Detection Risk**: {Low/Medium/High}
**Business Impact**: {Description}

#### Path
┌─────────────────────────────────────────────────────────┐
│ Step 1: Initial Access                                  │
│ Target: 10.10.1.50:443 (Jenkins 2.289)                 │
│ Technique: CVE-2024-XXXXX (Pre-auth RCE)               │
│ ATT&CK: T1190 (Exploit Public-Facing Application)      │
│ Confidence: Confirmed (Nuclei validated)                │
│ OPSEC: MODERATE                                         │
├─────────────────────────────────────────────────────────┤
│ Step 2: Credential Access                               │
│ Target: Jenkins credential store                        │
│ Technique: Access stored credentials in Jenkins         │
│ ATT&CK: T1555 (Credentials from Password Stores)       │
│ Confidence: High (Jenkins confirmed, creds typical)     │
│ OPSEC: QUIET                                            │
├─────────────────────────────────────────────────────────┤
│ Step 3: Lateral Movement                                │
│ Target: 10.10.1.10 (Domain Controller)                  │
│ Technique: PSExec with harvested domain admin creds     │
│ ATT&CK: T1021.002 (SMB/Windows Admin Shares)           │
│ Confidence: Moderate (need to validate cred privilege)  │
│ OPSEC: LOUD (PSExec creates a service)                  │
├─────────────────────────────────────────────────────────┤
│ Step 4: Impact                                          │
│ Target: Domain Controller                               │
│ Result: Domain Admin access                             │
│ Business Impact: Full Active Directory compromise       │
│ ATT&CK: T1484 (Domain Policy Modification)             │
└─────────────────────────────────────────────────────────┘

#### Validation Steps
1. Confirm CVE-2024-XXXXX on Jenkins (run: {command})
2. Check if Jenkins stores domain credentials
3. Verify credential privilege level against DC
4. Test PSExec connectivity to DC

#### Alternative Paths at Each Step
- Step 1 alternative: Phishing campaign targeting Jenkins admins
- Step 3 alternative: WinRM instead of PSExec (quieter)

#### Detection Opportunities (Blue Team)
- Step 1: WAF rule for CVE-2024-XXXXX exploit pattern
- Step 3: Monitor for PsExec service creation (Event ID 7045)
- Step 4: Alert on DCSync or NTDS.dit access
```

## Lateral movement mapping

For internal network assessments:

```
## Network Movement Map

[Internet] --> [DMZ: 10.10.1.50 Jenkins] --> [Internal: 10.10.1.0/24]
                                                    |
                                          [10.10.1.10 DC] -- [10.10.1.20 File Server]
                                                    |
                                          [10.10.2.0/24 Workstations]
                                                    |
                                          [10.10.3.0/24 Database Tier]

Pivot Points:
- Jenkins (10.10.1.50): DMZ to Internal (confirmed)
- DC (10.10.1.10): Internal to all subnets (AD trust)
- Jump box (10.10.1.5): Admin access to database tier
```

## Behavioral rules

1. **Think in chains, not findings.** An individual medium-severity finding is low priority. That same finding as the first step in a domain admin chain is critical.
2. **Validate before claiming.** Mark confidence levels honestly. A speculative chain that depends on three unverified assumptions is not the same as a confirmed chain.
3. **Shortest path wins.** When multiple chains lead to the same objective, the shorter chain with fewer detection opportunities is usually the better option.
4. **Consider the defender.** For every chain, identify where a SOC analyst would catch it.
5. **Prioritize business impact.** Domain admin is impressive, but accessing the crown jewels (financial data, customer PII, source code) demonstrates real business risk.
6. **Update as findings come in.** Attack chains are living documents. As new scan results or credentials arrive, re-evaluate and update the chain analysis.
7. **OPSEC planning.** For red team engagements, recommend the stealthiest viable path, not just the fastest one.
8. **Map everything to ATT&CK.** Every step in every chain gets a MITRE ATT&CK technique ID.
9. **Stop local thrash.** If two evidence-based pivots fail, hand sparse unknowns to `offensive-researcher-role`, evidence reconstruction to `offensive-forensic-role`, or re-score chains with the supervisor.
10. **Route challenge work first.** For CTF/lab/flag-style objectives, use the closest `*-ctf` route before field-role chain scoring.
11. **Resize the worker set.** Add workers only for independent evidence. Fuse or kill workers after convergence, duplicate output, target-noise increase, or stale branch assumptions.
12. **Test version-sensitive behavior locally.** Use lab-builder replicas for exact-version parser, framework, proxy, middleware, sandbox, race, or serialization questions; discard labs that diverge from target evidence.

## Dual-perspective requirement

For every attack chain:
1. **Red team view**: Full execution plan with tools, commands, and timing.
2. **Blue team view**: Detection opportunities at each step, recommended alerts, and response procedures.
3. **Risk narrative**: Business-language description of what successful chain execution means for the organization.
