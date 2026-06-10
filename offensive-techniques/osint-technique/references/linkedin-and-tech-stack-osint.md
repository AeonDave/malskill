# LinkedIn Employee Enum & Job-Posting Tech Stack OSINT

Load when building a people graph from LinkedIn or extracting confirmed technology stack from public job postings.

---

## 1. LinkedIn employee enumeration

Highest-signal source for target list generation, role prioritization, email-pattern derivation, pretext development.

### 1.1 Search techniques

**Free LinkedIn (no Sales Navigator):**
```
https://www.linkedin.com/search/results/people/?currentCompany=["<company-id>"]
```
Get company-id from the company's LinkedIn URL or page JSON. Default search shows only 1st/2nd-degree — bypass via Google dorking.

**Google dorks:**
```
site:linkedin.com/in "<company name>"
site:linkedin.com/in "<company name>" "engineer"
site:linkedin.com/in "<company name>" "<location>"
site:linkedin.com/in "<company name>" -inurl:/posts
```
Cross-engine with Bing + DuckDuckGo — they often return different result sets; union them.

**Sales Navigator (paid):** lead lists by company × role × seniority → CSV export.

**Tooling:**
- `theHarvester -b linkedin` (search-engine driven)
- CrossLinked — https://github.com/m8r0wn/CrossLinked
- LinkedInDumper / Linkook (verify currency; break frequently)
- Paid SaaS: PhantomBuster, Apollo.io, RocketReach, Hunter.io Email Finder (one-shot enum + email derivation)

### 1.2 Role tier rubric (for breach lookup + phishing prioritization)

| Tier | Examples | Why |
|---|---|---|
| **P0** | CEO, CFO, CTO, CISO, CIO, COO, GC, CRO | Exec accounts; BEC + finance + legal authority |
| **P1** | VP / Director of IT / Security / Engineering / Finance / HR | Privileged tool access; reset workflows |
| **P2** | DevOps, SRE, Platform, Security Engineer, DBA | GitHub / cloud / CI access; secrets in their personal accounts |
| **P3** | Software Engineer, Architect, Senior Developer | Code + occasional cloud |
| **P4** | Sales, Marketing, HR, Finance Analyst, Customer Support | SaaS access (Salesforce, HubSpot, Workday); BEC enabler |
| **P5** | IC, intern, contractor | Lowest per-account, but breadth |

### 1.3 Per-employee capture

For every enumerated person, record:
- Canonical name (First Last; drop "PMP"/"PhD" suffixes for email matching)
- Job title (raw + tier from §1.2)
- Tenure (years; longer = more access typically)
- Location (city/region; informs phishing time-of-day)
- Recent activity (posts/comments/conferences → pretext hooks)

### 1.4 Email-pattern derivation
- Apply patterns from `osint-technique/SKILL.md` §11.
- Confirm pattern via Hunter.io `domain-search`.
- Cross-ref against breach corpus (HudsonRock, HIBP, DeHashed, IntelX).

### 1.5 Sock-puppet hygiene
- **Never connect from corporate persona.** LinkedIn shows "viewed your profile" notifications.
- Sock puppet: 5+ years history, plausible industry, mutual connections to dilute correlation.
- "Private mode" anonymous viewing reduces one signal — Sales Navigator can still see anonymized "someone viewed your profile."
- No connection requests during recon (detectable).
- Throttle profile views: <20/day per persona; 100+ views of one company in a day = traceable pattern.

### 1.6 Output schema
```yaml
Person:
  name:        "Alice Doe"
  title:       "Senior DevOps Engineer"
  role_tier:   P2
  company:     "Acme Corp"
  location:    "Boston, MA"
  linkedin_url: https://www.linkedin.com/in/alicedoe
  derived_emails:
    - alice.doe@acme.com    (TENTATIVE)
    - adoe@acme.com         (TENTATIVE)
    - alice@acme.com        (TENTATIVE)
  breach_hits:
    - alice.doe@acme.com    (HudsonRock; cleartext password redacted; FIRM)
  pretext_hooks:
    - "DevOps tooling vendor evaluation" (recent posts)
    - "Boston DevOps Days speaker" (conference activity)
```

---

## 2. Job-posting tech-stack analysis

Job postings reveal exact internal stack with vendor names. Free, public, high-fidelity.

### 2.1 Sources

| Platform | URL pattern |
|---|---|
| LinkedIn Jobs | `https://www.linkedin.com/jobs/search/?f_C=<company-id>` |
| Indeed | `https://www.indeed.com/cmp/<company>` |
| Glassdoor | `https://www.glassdoor.com/Jobs/<company>-Jobs-E<id>.htm` (+ salary + reviews) |
| Lever ATS | `https://jobs.lever.co/<company>` |
| Greenhouse ATS | `https://boards.greenhouse.io/<company>` |
| Workable ATS | `https://apply.workable.com/<company>/` |
| AshbyHQ ATS | `https://jobs.ashbyhq.com/<company>` |
| Wellfound (AngelList) | `https://wellfound.com/company/<company>/jobs` |
| BuiltIn | `https://builtin.com/companies/view/<company>` |
| Direct careers page | `https://careers.<target>.com` / `https://<target>.com/careers` |

Direct ATS endpoints usually have fuller descriptions than aggregator listings.

### 2.2 Extraction targets

For every posting harvest:
- **Required tech** ("must have X, Y, Z") → confirmed in-use
- **Nice-to-have tech** → likely in use, possibly in transition
- **Vendor names** (Workday, Salesforce, Snowflake, Databricks, Datadog…) → SaaS tenants → §1.4 of `identity-fabric-enumeration.md`
- **Internal codenames** ("you'll work on Project Aurora") → recon vocabulary
- **Team size hints** ("part of a 12-person platform team") → org structure
- **Office locations** ("hybrid 3 days Boston office") → physical recon
- **Cloud vs on-prem hints** ("migrating from on-prem to AWS") → posture intel
- **Compliance frameworks** (SOC2, FedRAMP, HIPAA, PCI) → defensive priorities + reporting framing

### 2.3 Output schema
```yaml
Tech_inferred:
  product:     "Snowflake"
  category:    "data warehouse"
  source:      "linkedin job posting #<id>"
  source_url:  https://www.linkedin.com/jobs/view/...
  confidence:  TENTATIVE  # job listing implies in-use; not directly probed yet
  posting_date: 2026-03-15
  required_or_nice: "required"
```

Aggregate to a **target tech-stack profile** that drives:
- Vendor-specific secret patterns to add to scans (Snowflake keys, Databricks tokens).
- SaaS tenant fingerprinting (Snowflake account URL pattern).
- Vendor-product fingerprinting against frontend JS (Snowflake DSN paths).

### 2.4 Tooling
- `scrapy` / BeautifulSoup — per-ATS scrapers
- `theHarvester` with appropriate sources
- Manual review of 20–30 postings — fast + high-fidelity for small targets

---

## 3. Hard rules
- All findings TENTATIVE until cross-confirmed (Hunter.io, breach hit, direct probe).
- Never connect/message from operator persona.
- Job postings are passive intel — extracting them generates zero outbound traffic to target.
