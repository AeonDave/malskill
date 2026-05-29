# Engagement Planning

## Purpose

Plan and structure penetration testing and red team engagements with clear phases, technique mapping, and rules of engagement.

## When to load this reference

- Planning a new penetration test or red team engagement.
- Need to define scope, methodology, and phases.
- Creating rules of engagement documentation.
- Estimating time and resources per phase.

---

## Engagement types

- **External Network**: internet-facing attack surface.
- **Internal Network**: assumed internal position or VPN access.
- **Web Application**: OWASP methodology focused.
- **Wireless**: 802.11 assessment.
- **Social Engineering**: phishing, vishing, physical.
- **Cloud**: AWS, Azure, GCP environment testing.
- **Red Team**: full-scope adversary simulation.
- **Assumed Breach**: starting from internal foothold.
- **Physical**: on-site security assessment.

## Planning standards

For each engagement phase, specify:

| Element | Description |
|---------|-------------|
| Objectives | What this phase aims to achieve |
| Techniques | Specific methods with MITRE ATT&CK IDs |
| Tools | Recommended tooling with specific configurations |
| Expected Artifacts | What evidence and data this phase produces |
| Time Estimate | Hours or days allocated |
| Risk Level | Low / Medium / High (with justification) |
| Dependencies | What must complete before this phase begins |

## Phased engagement structure

### Phase 1: Scoping
- Define in-scope and out-of-scope systems.
- Identify engagement type and constraints.
- Document emergency contacts and abort procedures.
- Establish communication protocols and reporting cadence.

### Phase 2: Reconnaissance
- Passive OSINT and infrastructure discovery.
- Active scanning within scope boundaries.
- Technology stack identification.

### Phase 3: Enumeration
- Service-specific enumeration.
- User and share enumeration.
- API and endpoint discovery.

### Phase 4: Vulnerability analysis
- Automated scanning (nuclei, OpenVAS, Nikto).
- Manual verification and false positive elimination.
- Prioritization by exploitability and impact.

### Phase 5: Exploitation
- Confirmed vulnerability exploitation.
- Initial access establishment.
- Credential harvesting.

### Phase 6: Post-exploitation
- Privilege escalation.
- Lateral movement.
- Persistence (if authorized).
- Objective completion.

### Phase 7: Reporting
- Findings compilation.
- Executive summary.
- Remediation guidance.
- Evidence preservation.

## Rules of engagement template

```
Engagement: [CLIENT NAME] - [ENGAGEMENT TYPE]
Date Range: [START DATE] to [END DATE]
Assessor: [ASSESSOR NAME/COMPANY]

1. Authorized Targets: [IP ranges, domains, URLs]
2. Excluded Targets: [systems not to touch]
3. Authorized Techniques: [specific techniques approved]
4. Prohibited Actions: [DoS, data destruction, persistence]
5. Communication: [daily standup, email, Slack]
6. Emergency Contact: [name, phone, email]
7. Abort Signal: [what triggers immediate stop]
8. Data Handling: [retention, destruction policy]
9. Evidence Storage: [encryption, access control]
10. Legal Authority: [signed ROE reference]
```
