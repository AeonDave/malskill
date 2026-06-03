# Offsec supervisor role model

## Purpose

Use this reference when an offensive-security task needs a supervisor/operator model rather than one broad agent doing everything. The model is framework-neutral: if no multi-agent runtime exists, run the same gates serially and keep the packet as working notes.

## Role taxonomy

| Role | Owns | Does not own |
|---|---|---|
| Supervisor | mission, scope, threat model, attack-chain choice, task packets, review, synthesis | unreviewed exploit execution, speculative scope expansion, final proof without artifact inspection |
| Specialist operator | one bounded decision or workstream with exact artifacts and limits | redefining mission, expanding targets, changing ROE, merging final claims |
| Scope reviewer | target boundaries, permissions, timing, noise/destructive limits, data-handling rules | technical polish before scope is correct |
| Evidence reviewer | claim quality, primary artifacts, confidence downgrades, contradictions | accepting tool reputation as proof |
| Technical reviewer | correctness, reproducibility, minimality, maintainability | overriding scope or evidence gates |

A supervisor should normally need read/context tools and orchestration tools. Give write, shell, cloud, credential, or network tools to workers only when the task packet requires them and the environment supports hard restrictions.

## Operator squad

Route to the narrowest available role skill, domain skill, or serial workstream:

| Role skill | Use for |
|---|---|
| `offensive-recon-role` | attack-surface mapping, host/service inventory, target-package creation |
| `offensive-osint-role` | passive public-source research, leaks, identity patterns, supplier and pretext-safe pivots |
| `offensive-web-role` | web app, API, auth flow, browser, upload, SSRF, XSS, SQLi, SSTI, deserialization |
| `offensive-cloud-role` | cloud identity, metadata, storage, workloads, SaaS, cross-account or hybrid identity paths |
| `offensive-windows-role` | Windows hosts, accounts, services, SMB shares, WinRM/RDP, Active Directory, Kerberos, AD CS |
| `offensive-linux-role` | Linux hosts, sessions, users, services, packages, logs, containers, SSH, network paths |
| `offensive-mobile-role` | Android APK/device or iOS IPA/device assessment, mobile APIs, instrumentation |
| `offensive-reverse-role` | binaries, firmware, PCAPs, dumps, config extraction, protocol analysis, patch deltas |
| `offensive-crypto-role` | cryptanalysis, hashes, tokens, oracle interaction, key recovery, protocol math |
| `offensive-exploit-role` | CVE adaptation, native memory corruption, fuzzing reproducers, exploit reliability |

If the starting state spans lanes, delegate only the first question that changes the decision tree. Do not parallelize speculative branches.

## Mission modes

Choose one primary mode before building the chain:

- **Capability assessment**: answer whether a control, asset class, or surface is exploitable; stop once evidence answers the question.
- **Adversary emulation**: preserve threat-profile fidelity and ATT&CK-coherent cross-phase behavior.
- **Objective-led operation**: shortest validated path to the stated objective, such as data-access proof, lateral movement, or impact demonstration.
- **Artifact triage**: answer the decisive question about a binary, APK, IPA, PCAP, firmware, dump, crypto material, or leaked dataset first, then route onward.
- **Skill/tool curation**: compare local repo content with external evidence, remove overlap, patch guidance, and validate changed skills.

If mission is unclear, decide whether the user needs a vulnerability list, a full attack chain, or a single objective proof before assigning work.

## Starting-state classifier

| Starting state | First route |
|---|---|
| External scope, no foothold, no credentials | `offensive-recon-role` first; promote to web, exploit, cloud, or OSINT only after validation |
| Valid credential or token, no host control | `offensive-cloud-role`, `offensive-windows-role`, `offensive-linux-role`, or `offensive-web-role` based on where the credential applies |
| Shell or session on a host | `offensive-windows-role` or `offensive-linux-role`; add `offensive-cloud-role` if the host is a cloud workload |
| Offline artifact | `offensive-reverse-role`, `offensive-mobile-role`, `offensive-crypto-role`, or `offensive-osint-role` based on artifact type |
| Objective-led with multiple possible paths | Score candidate chains; pick the path with fewest unvalidated dependencies |

## Task packet template

Write or attach a packet for each delegated task. Use absolute paths for local artifacts.

```markdown
# Task packet: task-name

## Scope and ROE
- Authorized targets/artifacts:
- Out of scope:
- Allowed actions:
- Prohibited actions:
- Time/noise/destructive limits:
- Kill-switch or stop condition:
- Data-handling rules:

## Mission
- Mode:
- Objective:
- Success signal:
- Starting state:
- Threat-model notes: assets, identities, trust boundaries, likely attacker profile, required access, impact target

## Inputs
- Files/URLs/artifacts:
- Known facts:
- Assumptions to verify:

## Work requested
- Smallest decisive question:
- Expected evidence:
- Verification command/artifact, if safe:

## Deliverable
- Status: done | done with concerns | blocked | needs context
- Findings with evidence citations:
- Contradictions or uncertainty:
- Next safest action:
```

## Review and synthesis

Inspect worker artifacts before accepting conclusions. Use this synthesis shape:

| Field | Required content |
|---|---|
| Fact | Evidence-backed observation |
| Evidence | file, command output, transcript, hash, screenshot, packet capture, citation, or reproducible step |
| Confidence | confirmed, likely, plausible, unknown |
| Risk | scope, noise, destructiveness, false-positive, data-handling, or detection risk |
| Next action | smallest safe verification or implementation step |

Downgrade any claim based only on scanner output, public reputation, memory, stale notes, or a worker summary with no primary artifact.

## Stop conditions

Stop and reassess when:

- scope, third-party authorization, or ROE is unclear for the next step;
- kill-switch, availability, safety, or data-handling limit is triggered;
- next step requires access, credentials, tool privileges, or techniques not approved;
- noise budget or timing window is exhausted;
- foundational threat-model assumption is disproven;
- two pivots fail and the team is thrashing;
- objective has already been demonstrated with sufficient proof.

When stopping, state one of: **complete**, **blocked by scope**, **blocked by missing evidence**, **blocked by capability**, or **needs a different chain**.
