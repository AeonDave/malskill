# Operational Security & Evidence Preservation

OSINT investigations leave traces. Protecting your identity, maintaining chain of custody, and ensuring reproducibility are critical to operational security and legal defensibility.

## Operational Security (OpSec)

### Sock Puppets & False Identities

**Purpose**: Investigate without revealing your real identity.

**Setup**:
- Fake name generator (fakenamegenerator.com, thispersondoesnotexist.com for avatars).
- Separate browser profiles (Firefox Multi-Account Containers, Chrome profiles).
- Disposable email (10minutemail, guerrillamail, or dedicated forwarding service).
- Disposable phone numbers (Burner, Silent Link, Twilio).

**Activation**:
- Build posting history *before* using for investigation (post innocuous content for weeks).
- Link fake identity across platforms (consistent username/avatar).
- Avoid logging into personal accounts while using fake identity.

### Browser & Network Isolation

**Multiple identities**:
- Separate browser profile per case + persona.
- Clear cookies between sessions.
- Use dedicated VPN/proxy per persona (to avoid cross-pollination via IP).

**VPN/Proxy**:
- Commercial VPN (NordVPN, ProtonVPN, Mullvad): Hides your IP.
- Residential proxies: Appear as normal home connections (avoid bot detection).
- Tor: Maximum anonymity; some sites block Tor exit nodes.

**Avoid**:
- Logging into personal accounts while investigating (metadata linkage).
- Reusing usernames across cases.
- Browser extension supply-chain attacks (audit before install; security researchers have found trojanized extensions).

### Rate-Limiting & Stealth

- **API rate limits**: Respect API limits; aggressive querying triggers IP bans or legal action.
- **Spread queries**: Stagger OSINT queries over time (not all at once).
- **User-agents**: Rotate user-agents to appear like different browsers/devices.
- **DNS leaks**: Use VPN's DNS, not ISP DNS (DNS queries leak identity even over VPN).

### Hardware-Backed Credentials

- **Passkeys** (FIDO2): Hardware-backed authentication (USB keys, biometric).
- **Recovery codes**: Store offline; essential for account recovery.
- **Avoid**: Password managers alone for critical accounts; add 2FA.

---

## Evidence Preservation & Chain of Custody

### Artifact Logging

**Format**: JSONL (newline-delimited JSON) or structured CSV.

```jsonl
{"run_id": "osint-2025-03-25-case-001", "timestamp": "2025-03-25T14:32:00Z", "tool": "crt.sh", "query": "example.com", "result_count": 42, "url": "https://crt.sh/?q=example.com", "notes": "Found 5 new subdomains", "hash_screenshot": "sha256-abc123..."}
```

**Fields**:
- `run_id`: Unique campaign identifier (for reproducibility).
- `timestamp`: UTC time (avoid timezone confusion).
- `tool`: OSINT tool used.
- `query`: Exact search term.
- `result`: Finding (count, first result, etc.).
- `url`: Link to result.
- `notes`: Analyst commentary.
- `hash_*`: SHA-256 hash of archived artifacts.

### Archival Methods

**Screenshots**:
- PNG format; metadata stripped by default.
- Include date, time, URL in screenshot or annotation.

**WARC Archives**:
- Web Archive format; preserves entire page (HTML + resources).
- **ArchiveBox**, **Browsertrix Crawler**: Automated WARC generation.
- **SingleFileZ** (browser extension): One-file offline archives.

**Archive.today / Wayback SavePageNow**:
- External archival; provides timestamp-proof.
- Useful for legal defensibility (third-party archive).

### Hash Verification

- **SHA-256** of downloaded files, screenshots, archives.
- **Example**: `sha256sum malware_sample.bin` → `abc123...`
- **Store**: In JSONL log for reproducibility.

---

## Evidence Handling

### Read-Only Storage

- Archive evidence on read-only media (if in legal hold).
- Separate work profiles per case (avoid cross-contamination).

### Chain of Custody

- **Who**: Analyst name.
- **What**: Artifact (URL, file, screenshot).
- **When**: Timestamp (UTC).
- **Where**: Storage location (archive.today, local drive, cloud).
- **Why**: Investigation objective.

### Legal Considerations

**GDPR (EU)**: 
- Process personal data only with legal basis (contract, consent, legitimate interest).
- Data minimization: Collect only necessary data.
- Retention: Delete after investigation purpose met.

**CFAA (US)**:
- Do not access honeypots, protected systems, or honeypots masquerading as public.
- Scraping may violate ToS; legal status unclear (active litigation).

**Consent & Authorization**:
- Ensure you have authority to investigate before beginning.
- Incident response: Usually authorized by employer/incident response retainer.
- Public OSINT: Usually permitted; verify local law.

---

## Reproducibility

### Tool Versions

- Document tool versions used.
- **Example**: `sherlock v0.14.1`, `theHarvester 4.0.1`, `Shodan API v2`.

### Search Parameters

- Exact query string (enable others to repeat).
- **Example**: `Shodan query: "apache/2.4.41" country:US port:80`.
- **Timestamp**: When query was run (data changes over time).

### Seed Data

- Provide starting point (target domain, email, person name).
- Analysts should be able to reproduce findings using your documented method.

---

## Investigation Notes

### Structured Notes

- **Case ID**: Unique identifier (e.g., `OSINT-2025-Q1-Target-XYZ`).
- **Objective**: What are we trying to learn?
- **Scope**: Target (person/domain/organization), constraints (timeline, geography).
- **Method**: High-level workflow (e.g., "Domain → CT logs → infrastructure map → breach research").
- **Findings**: Key discoveries.
- **Unknowns**: What remains unclear.
- **Next steps**: What should be investigated further.
- **Sources**: All tools/platforms used; versions, dates.

### Timeline Construction

- Create a master timeline combining all findings.
- **Example**:
  - 2024-01-15: Domain registered (WHOIS).
  - 2024-02-01: First SSL cert issued (CT logs).
  - 2024-03-10: Mentioned in blog post (Google dorking).
  - 2024-05-20: Breach data exposure (Have I Been Pwned).

---

## Case Management

### Tools for Organization

- **ArchiveBox** (archivebox.io): Self-hosted web archiver; organize by tag.
- **Notion / Obsidian**: Case notes, timeline, evidence links.
- **MISP / OpenCTI**: Structured threat intelligence; export to reports.
- **Spreadsheet**: Simple CSV with evidence log.

### Naming Conventions

- **Case folder**: `OSINT_2025_March_Target-XYZ`
- **Evidence files**: `TARGET-XYZ_domain-research_2025-03-25.json`
- **Reports**: `TARGET-XYZ_OSINT-Report_FINAL_2025-03-30.pdf`

---

## Workflow: Preserving Evidence

1. **Open case**: Create case ID, document objective/scope.
2. **Execute queries**: Log each tool use (JSONL format).
3. **Capture results**: Screenshots or WARC archives.
4. **Hash artifacts**: SHA-256 of all captured files.
5. **Timestamp everything**: UTC timestamps for reproducibility.
6. **Archive externally**: archive.today or similar (third-party proof).
7. **Case notes**: Update notebook with findings, unknowns, next steps.
8. **Final review**: Verify tool versions, query parameters documented.
9. **Export report**: Consolidated findings, sources cited, confidence levels.
10. **Archive case**: Store evidence + notes for future reference.

---

## Anti-Patterns

- **Investigating from personal account**: Metadata linkage ruins OpSec.
- **Over-sharing findings**: Revealing investigation can tip off target.
- **Inconsistent timestamps**: Mix UTC, local time, and timezone abbreviations.
- **Forgetting tool versions**: Findings may not reproduce if tool API changed.
- **Single archive method**: If archive.today goes down, you've lost evidence; use multiple methods.
- **No chain of custody**: Legally indefensible; auditor cannot verify evidence integrity.
