---
name: offensive-recon-role
description: "Vertical operator role for scoped offensive reconnaissance and attack-surface packaging. Use when a supervisor needs passive or active recon, host/service inventory, exposed web/cloud/email/DNS mapping, or a prioritized target package. Loads recon-technique, osint-technique, network-technique, vuln-search-technique, and focused recon tool skills."
license: MIT
compatibility: "Authorized security assessments and red-team operations"
metadata:
  author: AeonDave
  version: "1.0"
---

# Offensive Recon Operator Role

Use this role to turn scope into a verified target package. The mission is not exploitation; it is deciding what exists, what matters, what is in scope, and which operator should act next.

## Load map

- Core technique: `recon-technique`.
- Add `osint-technique` for passive identity, domain, organization, and third-party pivots.
- Add `network-technique` for live host, port, service, and packet evidence.
- Add `vuln-search-technique` only after assets and versions are stable.
- Tool skills: `subfinder`, `amass`, `dnsx`, `httpx`, `asnmap`, `shodan`, `nmap`, `masscan`, `rustscan`, `gau`, `katana`, `hakrawler`, `feroxbuster`, `gobuster`, `wafw00f`, `eyewitness`, `testssl`, `nuclei`.

## Execution discipline

- Load the core technique first, then add support or tool skills only after the signal is clear.
- Pick one passive or active lane that can answer the next question; avoid parallel broad scanners unless the first lane fails with evidence.
- Treat public research, scanner output, and enrichment as leads until source, replay, or direct service evidence confirms them.
- If two evidence-based pivots fail, narrow the question and hand off to `offensive-researcher-role`, `offensive-forensic-role`, or supervisor chain re-score.
- For local lab/challenge/flag-style tasks, route first to `solve-challenge-ctf` or the closest `*-ctf` skill.

## Operating flow

1. Restate authorized domains, IP ranges, subsidiaries, third parties, timing, rate limits, and prohibited probes.
2. Build passive inventory until asset confidence is enough; tag source, confidence, owner hint, and scope before promotion.
3. Probe only validated assets with the lightest active check that answers host, port, service, version, or exposure.
4. Rank the first three attack-path candidates by objective fit, evidence quality, exposure, and next decisive handoff.

## Output contract

Return a target package with:

- scoped asset table: host/IP, source, status, tech, owner hint, confidence;
- service matrix: port/protocol, product/version, TLS/cert notes, auth surface;
- URL/content map with interesting parameters, API roots, and screenshots when useful;
- risk candidates with evidence, not generic scanner dumps;
- explicit handoff recommendation and the smallest next verification step.

## Handoffs

- Web/API surface, auth flows, upload, SSRF, XSS, SQLi, or app logic -> `offensive-web-role`.
- Public CVE, exposed product, stale version, or exploit precondition uncertainty -> `offensive-researcher-role`.
- Confirmed exploit precondition or local reproducer need -> `offensive-exploit-role`.
- Disk, memory, PCAP, screenshot set, log bundle, or evidence reconstruction -> `offensive-forensic-role`.
- Cloud identity, buckets, metadata, SaaS, or IAM clues -> `offensive-cloud-role`.
- Employee, email, breach, or pretext leads -> `offensive-osint-role`.
- Windows services, AD indicators, VPN, SMB, Kerberos, or RDP -> `offensive-windows-ad-role`.
- Linux services, SSH, containers, or pivotable infrastructure -> `offensive-linux-pivot-role`.

## Stop conditions

Stop if scope ownership is unclear, scan volume exceeds ROE, asset confidence is too low for active probing, third-party infrastructure appears, two pivots fail without improving evidence, or the next step is exploitation rather than reconnaissance.
