---
name: report-generation-technique
description: "Penetration test report generation methodology: executive summaries, detailed findings with CVSS scoring, attack narratives, MITRE ATT&CK mapping, and remediation guidance. Use when writing penetration test reports, compiling findings into professional documentation, or creating executive summaries for security assessment deliverables."
license: MIT
compatibility: "Markdown, PDF, DOCX output; PTES, OWASP, and SANS reporting standards"
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Report Generation Technique

Goal: produce professional penetration test reports that meet industry standards and satisfy both technical and executive audiences.

## When this technique applies

- Need to compile pentest findings into a structured report.
- Writing executive summaries or detailed technical findings.
- Creating attack narratives or remediation guidance.

## Initial triage

Before writing, classify the deliverable and the evidence maturity so the report structure matches the engagement outcome.

- **Starting state**: are you producing an executive summary, a full technical report, an interim findings memo, or a single-finding writeup?
- **First questions**: who is the audience, what evidence is already validated, what findings are report-ready, and what methodology/scope context must be stated up front?
- **Immediate actions**: sort findings by severity and confidence, identify missing proof or remediation details, and build the report skeleton before prose.
- **Tool-family direction**: this technique mostly coordinates evidence and structure; pull from the relevant technique/tool outputs rather than inventing new tooling here.
- **Escalation rule**: do not polish narrative before confirming evidence quality, scope statements, and remediation ownership.

## Boundary with other skills

- **Evidence production**: the relevant offensive or analysis technique should already have produced validated findings and artifacts.
- **Writing support**: use `knowledge/evidence-before-claims/` and `knowledge/verification-before-completion/` logic when a finding is not yet report-ready.

## Report structure

### 1. Cover page

```
[CLASSIFICATION LEVEL]
Penetration Test Report
[ENGAGEMENT TITLE]

Client: [CLIENT NAME]
Assessment Dates: [START DATE] -- [END DATE]
Report Date: [REPORT DATE]
Assessor(s): [ASSESSOR NAME(S)]
Report Version: 1.0
Distribution: [DISTRIBUTION LIST]
```

### 2. Executive summary

- Written for non-technical leadership (C-suite, board members, risk committee).
- 1-2 pages maximum.
- Overall risk rating with justification.
- Key statistics: total findings by severity, systems tested, critical issues.
- Top 3-5 findings summarized in business impact terms.
- Strategic recommendations (business decisions, not technical fixes).
- Comparison to previous assessment if applicable.

### 3. Scope and methodology

- Systems, networks, and applications in scope (with IP ranges, URLs).
- Explicitly stated exclusions.
- Testing approach and methodology (PTES, OWASP, custom).
- Testing window and any constraints.
- Tools used (with versions).
- Limitations encountered during testing.

### 4. Findings summary table

| ID | Finding | Severity | CVSS | Affected Systems | Status |
|---|---|---|---|---|---|

Sorted by severity (Critical to Informational).

### 5. Detailed findings

Each finding:

```markdown
### [ID] -- Finding Title

**Severity**: Critical | High | Medium | Low | Informational
**CVSS v3.1**: X.X (Vector: CVSS:3.1/AV:X/AC:X/PR:X/UI:X/S:X/C:X/I:X/A:X)
**CWE**: CWE-XXX -- Name
**Affected Systems**: [IP/hostname/URL list]
**MITRE ATT&CK**: TXXXX -- Technique Name

#### Description
What the vulnerability is, where it exists, and the technical root cause.

#### Evidence
[Screenshot placeholder: evidence-XX.png]
[Redacted proof-of-concept details]

#### Impact
Business impact: what an attacker could achieve.

#### Remediation
1. Immediate mitigation
2. Root cause fix
3. Preventive measures

#### Verification
How to confirm the fix was applied correctly.

#### References
- CVE-XXXX-XXXXX
- CWE-XXX
```

### 6. Attack narrative (optional)

Chronological walkthrough: initial access, privilege escalation, lateral movement, objective completion. Mapped to MITRE ATT&CK at each step.

### 7. Remediation priorities

Group fixes by effort and impact:
- Quick wins (low effort, high impact).
- Strategic fixes (architectural changes).
- Compensating controls (interim measures).

## Resources

- `references/report-templates.md` — full report templates in Markdown with placeholder sections.
- `references/finding-writing-guide.md` — guidance for writing clear, defensible finding descriptions.
