# Breach & Leak Research

Breach and credential research reveals what data has been compromised and exposed publicly. This is critical for risk assessment, incident response, and person/organization profiling.

## Research Objectives

- **Breach confirmation**: Has an email/domain/person been exposed in known breaches?
- **Credential exposure**: What usernames, passwords, or data were leaked?
- **Breach timeline**: When did the breach occur and get disclosed?
- **Scope assessment**: How many records were exposed? What type of data?
- **Supplier chain**: Were third-party vendors/partners breached, affecting your target?
- **Dark web exposure**: Infostealer logs, ransomware leak sites, criminal marketplaces.

---

## Public Breach Databases

### Have I Been Pwned (HIBP)

**Website**: haveibeenpwned.com

- **Input**: Email address or phone.
- **Output**: Which breaches exposed that email (Equifax, Ashley Madison, LinkedIn, Target, etc.). Often shows what data was exposed (passwords, credit cards, SSNs, etc.).
- **Pwned Passwords API**: k-anonymous search for plaintext passwords (check if a password has appeared in breaches).
- **Free**: Web interface and API.

### Dehashed

**Website**: dehashed.com

- **Input**: Email, username, or hash.
- **Output**: Leaked credentials (plaintext passwords if available), associated data.
- **Coverage**: Thousands of breaches aggregated.
- **Note**: Often has more recent/complete data than HIBP, but requires account (freemium).

### LeakCheck

**Website**: leakcheck.io

- **Input**: Email, username, phone, IP.
- **Output**: Breached datasets.
- **Coverage**: Aggregated breaches.

### IntelX

**Website**: intelx.io

- **Input**: Email, username, IP, hash.
- **Output**: Dark web index (pastes, breaches, leaks).
- **Unique**: Includes darknet indices and API access for automation.

### BreachDirectory

**Website**: breachdirectory.org

- **Input**: Email.
- **Output**: Exposed data (recent breaches primarily).

### Scattered Secrets

**Website**: scatteredsecrets.com

- **Input**: Email.
- **Output**: Breach index.

---

## Credential-Specific Searches

### Password Hash Lookups

- **VirusTotal URL/File scan**: Submit a hash to see if it's flagged as malware or appears in threat intelligence.
- **Local cracking**: If you have a hash, attempt cracking with **Hashcat**, **John the Ripper**, or online services (**CrackStation**).
- **Rainbow tables**: Precomputed hash tables (limited by storage).

### Username + Password Pairs

- **Dehashed, LeakCheck**: Often return plaintext username + password pairs from leaked databases.
- **Combo lists**: Public repositories may contain username+password combinations from historical breaches.

---

## Infostealer & Malware Log Databases

### Cavalier (Hudson Rock)

**Website**: cavalier.hudsonrock.com

- **Purpose**: Infostealer logs (malware that steals browser cookies, passwords, etc.).
- **Input**: Email, domain.
- **Output**: How many infostealer infections have been detected with this email/credentials?
- **Value**: Reveals real-time compromise; more current than static breach databases.

### Other Infostealer Sources

- **Telegram channels**: Threat actors publish infostealer logs on Telegram (requires access + translation).
- **Dark web markets**: Infostealer logs sold on various forums.
- **OSINT services**: Some commercial threat intel services aggregate infostealer data (Hudson Rock, Digital Shadows, etc.).

---

## Ransomware Leak Sites

### Tactic

Threat actors publish breach data on "leak sites" to pressure victims into paying ransoms.

### Research

- **Ransomware leak site aggregators**: Some OSINT tools monitor and archive ransomware group leak sites.
- **Conti leaks**, **LockBit leaks**, **REvil leaks**, etc. occasionally surface on dark web forums or archived via security researchers.
- **Manual monitoring**: Follow threat intelligence feeds that track active ransomware campaigns.

---

## Dark Web & Darknet Searches

### IntelX

- **Tor-accessible index**: IntelX maintains a Tor version at `intelx.io` (onion address: `intelxio2nxrz374.onion`).
- **Email/username search**: Returns darknet pastes, leaks, and database entries.

### Pastebin & Code Hosting

- **Pastebin** (pastebin.com): Public paste sharing; searchable via Google, sometimes contains leaked credentials or source code.
- **GitHub**: Occasionally contains accidentally committed credentials, API keys, or source code.
- **GitLab, Gitea**: Similar risks.
- **Tool**: **truffleHog**, **gitleaks** can scan repos for secrets.

---

## Email-Specific Breach Research

### Email Enrichment & Validation

**Epieos** (epieos.com):
- Input email → pivot data: associated emails, names, phone numbers, social accounts (if leaked/found).
- Web interface; free.

**ReverseEmail** services:
- Input email → associated names, phone numbers, addresses (from breaches + public records).

### Email-to-Platform Enumeration

- **Holehe** / **Epieos**: Which platforms is this email registered on? (Useful for cross-referencing).

---

## Workflow: Breach Investigation for an Email

1. **Have I Been Pwned**: Input email → note breaches.
2. **Dehashed**: Input email → credential pairs (if plaintext available).
3. **LeakCheck/IntelX**: Confirm + expand breach coverage.
4. **VirusTotal**: If password hash obtained, search for known malware associations.
5. **Epieos**: Email enrichment → associated accounts, names, phones.
6. **Cavalier**: Infostealer compromise check.
7. **Archive**: Screenshots of each breach record, timestamp, URL.
8. **Assess**: Breach timeline, exposure severity, recommended actions (password reset, monitoring, etc.).

---

## Workflow: Breach Investigation for a Domain

1. **Domain WHOIS**: Extract registrant email.
2. **Email breach check**: Have I Been Pwned, Dehashed (registrant email).
3. **Domain-specific databases**:
   - **Shodan / Censys**: Check for exposed data from domain infrastructure.
   - **SecurityTrails**: Historical DNS + WHOIS changes (may reveal compromised infrastructure).
4. **Employee emails**: Build list of employee emails (via LinkedIn, job boards, LinkedIn), check each for breaches.
5. **Supplier/partner domains**: Check if vendors were breached (supply chain risk).
6. **Dark web**: IntelX for domain name in pastes/leaks.
7. **Synthesis**: Breach timeline, exposed assets, remediation path.

---

## Source Validation & Confidence

### Breach Confirmation

- **Multiple sources**: If email appears in HIBP *and* Dehashed, confidence is higher.
- **Original breach disclosure**: Check if breach was officially disclosed by the affected organization.
- **CISA / government advisories**: Major breaches often get government advisories (CISA, NCSC-UK).

### False Positives

- **Breach aggregators may have duplicates** or **data entry errors**: Validate independently.
- **Private databases**: Some services claim to index "secret" databases; not all are legitimate.
- **Timing**: Verify breach date matches timeline of target's activity (stale data is less actionable).

---

## Privacy & Legal Considerations

### Responsible Disclosure

- **If you discover** a company's exposed data, consider responsible disclosure (notify them confidentially before public disclosure).
- **Ransomware leak data**: Do not download/retain without legal authority; accessing and storing may violate CFAA (US) or equivalent laws.

### Personal Data Protection

- **GDPR**: Carelessly handling leaked EU citizen data violates GDPR; document legal basis for processing.
- **Consent**: Research ethics approval needed for large-scale data analysis.

---

## Anti-Patterns

- **Assuming all breached data is accurate**: Infostealer logs may contain stale, incorrect, or honeypot credentials.
- **Correlating two breaches = ownership**: Email in Breach A + Breach B does not prove same person; could be data aggregation error or coincidence.
- **Ignoring dark web**: Public databases capture 10-20% of total breach data; critical intelligence often exists only on darknet.
- **Over-reliance on HIBP**: Large, recent breaches (2024) may not yet be in HIBP; check Dehashed + IntelX.
- **Not archiving links**: Breach databases and pastes disappear; screenshot and archive everything.
