# Red Team Operations

## Purpose

Plan and execute long-running adversary emulation engagements with realistic threat-actor TTPs, C2 infrastructure, and strict OPSEC discipline.

## When to load this reference

- Full-scope red team engagement requiring C2 infrastructure, phased operations, and cleanup.
- Need to design an engagement plan with threat-actor profile emulation.
- Coordinating multiple operators and workstreams.

---

## Authorization gate

Before any operational activity:
1. Require a signed Statement of Work or Rules of Engagement document reference.
2. Capture: authorized targets, time windows, prohibited actions, trusted-agent contacts, abort signals, deconfliction process.
3. Default to least-impact techniques. Escalate only as the engagement scope requires.

## Methodology

### 1. Plan
- Map objectives to MITRE ATT&CK.
- Choose a threat-actor profile to emulate.
- Design a kill chain from initial access to objectives.
- Define success criteria and abort conditions.

### 2. Infrastructure
- Redirectors: domain fronting, CDN-backed C2, redirector VPS.
- Domain categorization: pre-check against major category databases.
- TLS: valid certificates for C2 domains.
- C2 profiles: Malleable C2 profiles or equivalent for traffic shaping.
- Separate staging infrastructure from long-haul C2.

### 3. Initial access
- Coordinate with phishing or web exploitation per scope.
- Document every artifact placed on target.
- Verify sandbox evasion and execution barriers.

### 4. Foothold
- Minimal payload: staged or stageless based on OPSEC requirements.
- Sandbox checks: domain-joined, disk size, running processes, uptime.
- Signed loaders where appropriate.
- Document every artifact placed.

### 5. Persistence and privilege escalation
- Prefer reversible mechanisms.
- Document persistence mechanism for cleanup.

### 6. Lateral movement
- Pace to defender capability.
- Prefer quieter protocols (WinRM, WMI) over noisy ones (PSExec).

### 7. Action on objectives
- Demonstrate access without exfiltrating real data.
- Use canary files or synthetic objectives.
- Document every action with timestamps.

### 8. Cleanup
- Remove every artifact placed during engagement.
- Verify removal with the blue team trusted agent.
- Document any artifacts that could not be removed.

## Operator log format

Maintain one entry per action:
- Timestamp (UTC), operator, source IP, target, technique (ATT&CK ID), command, result, artifacts created, OPSEC notes.
