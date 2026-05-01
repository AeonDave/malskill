# Company & Organization Research

Company OSINT reveals organizational structure, financial health, employee data, infrastructure, risk exposure—purely from public records and online sources.

## Research Objectives

- **Profile verification**: Legal entity status, location, leadership, financials.
- **Workforce**: Employees, roles, employment history, skills.
- **Supplier/Customer links**: Business relationships, partnerships.
- **Leaked documents**: Emails, contracts, internal plans (dark web, breach databases).
- **Risk assessment**: Regulatory violations, bankruptcies, litigations, M&A activity.
- **Infrastructure footprint**: Domains, subsidiaries, offices, acquisitions.

---

## Business Registries

Most countries maintain public registries of registered companies.

### Global & Multi-Region

- **OpenCorporates** (opencorporates.com): World's largest open company database; 175M+ companies searchable. Input company name → returns registered details (address, officers, registration date, status).
- **Wikipedia**: Often has company founding details, history, leadership.
- **Crunchbase** (web, limited free): Startup/tech company profiles, funding rounds, people, locations.

### US

- **SEC EDGAR** (sec.gov/edgar): US public company filings (10-K, 10-Q, 8-K, proxy statements). Rich financial + governance data.
- **OpenOwnership Register** (register.openownership.org): Beneficial ownership datasets (who really owns the company).

### EU

- **EU Tenders** (ted.europa.eu): EU procurement notices; reveals company contracts.

### Russia

- **Rusprofile** (rusprofile.ru): Russian company data.
- **Kontur.Focus** (focus.kontur.ru): Freemium Russian business data.
- **EGRUL/EGRIP**: Official Russian registry (captcha-gated).
- **zakupki.gov.ru**: Government procurement; reveals government contracts.

### China

- **GSXT** (gsxt.gov.cn): National Enterprise Credit Info System.
- **Qichacha** (qcc.com) / **Tianyancha** (tianyancha.com): Freemium Chinese company data.
- **MIIT Beian** (beian.miit.gov.cn): ICP filings; links domains to legal entities via Unified Social Credit Code (USCC).

---

## Employee & Recruitment Intel

### LinkedIn

- **Company page**: All employees, past employees, roles, seniority.
- **Keyword search**: `(job title) at (company)` returns people profiles.
- **Endorsements & Skills**: Reveals technical focus areas.
- **Timeline**: Job postings show openings + hiring focus.

### Job Boards

- **Indeed, LinkedIn Jobs, Glassdoor**: Reveals hiring, salaries, required skills.
- **Tech stacks**: Job descriptions mention programming languages, frameworks, tools → inference of infrastructure.
- **Salary data**: Glassdoor, Levels.fyi reveal compensation by role.
- **hh.ru** (Russia): Russian job postings with office locations, required certifications.

### GitHub

- **Company employees**: Search `org:companyname` to find repos maintained by company.
- **Commits**: Author names, email domains (company emails).
- **Technology choices**: Repos reveal tech stack, dependencies, coding practices.
- **Hiring signals**: Many new open-source projects can indicate growth.

### Glassdoor

- **Reviews**: Former employee insights on culture, pay, turnover.
- **Salaries**: Crowdsourced compensation data by role + level.
- **Interview reports**: Questions asked, company processes.

---

## Leaked Documents & Breaches

Companies suffer data breaches, insider leaks, email compromises.

### Dark Web & Leak Indices

- **OCCRP Aleph** (aleph.occrp.org): Investigative documents, leaks, company records.
- **Distributed Denial of Secrets** (ddosecrets.com): Leaked datasets (Conti, LockBit ransomware leaks, etc.).
- **Have I Been Pwned** (haveibeenpwned.com): Corporate email addresses exposed in breaches.
- **Dehashed** (dehashed.com): Company credential leaks.
- **IntelX** (intelx.io): Dark web index; company email leaks, source code.

### Search Strategies

- Email domain → breach lookups (how many employees' credentials leaked?).
- Company name + "leaked" → dark web indices.
- Ransom leak sites (Conti, LockBit, etc.) sometimes publish company names + samples.

---

## Financial & Compliance Filings

### Public Companies

- **SEC EDGAR**: 10-K (annual), 10-Q (quarterly), 8-K (material events), proxy statements.
- **CIK lookup**: SEC Central Index Key; use to search one company across all filings.

### Regulatory Records

- **Patent databases** (USPTO, WIPO, Google Patents): Reveals R&D focus, technology direction.
- **Trademark filings**: Brand portfolio, product/service names.
- **Regulatory violations**: FTC, CFPB, state Attorney General enforcement actions often public.

### Litigation

- **PACER** (pacer.uscourts.gov): US federal court records; search company lawsuits.
- **State court systems**: Vary by state; some searchable online.
- **Legal intelligence platforms** (LexisNexis, Thomson Reuters): Paid alternatives.

---

## Domain & Web Presence

### Domain Registration

- **WHOIS lookup**: Registrant info (often redacted), registrar, creation date, nameservers.
- **WHOIS history**: Domains4.com, WHOIS.ai, SecurityTrails → historical ownership.
- **Nameserver analysis**: Who hosts the company's DNS? Shared servers might reveal other domains under same operator.

### Acquisition & Portfolio Mapping

- **BuiltWith** (builtwith.com): Reverse tech-stack lookup. Input company domain → returns all technologies used (analytics, CMS, CDN, etc.).
- **Certificate Transparency logs** (crt.sh): All subdomains + certificates issued for a domain.
- **Passive DNS** (SecurityTrails, DNSDB, Rapid7 data): Historical A/AAAA/CNAME records → reveals IP ownership, provider changes, service migrations.

### Subsidiary / Acquisition Discovery

- SEC filings → merger/acquisition history.
- Domain registrant searches → find domains under same owner/registrant email.
- Trademark portfolio → product/brand acquisitions.

---

## Financial Intelligence

### Stock & Investor Data

- **FinViz** (finviz.com): Stock charts, insider trading, news.
- **Seeking Alpha**: Analyst commentary, insider trades.
- **Insider Trades** (official SEC Form 4): Track executive stock sales/purchases (timing reveals confidence/concern).

### Funding & VC

- **Crunchbase**: Funding rounds, investors, exits.
- **PitchBook** (paid): Comprehensive VC/PE intelligence.

### Bankruptcy & Litigation

- **PACER**: Federal court filings; bankruptcies are searchable.
- **BRB Publications**: Bankruptcy databases.

---

## Tech & Infrastructure Footprint

### Technology Stack Detection

- **BuiltWith**: Analytics tags, CMS, hosting provider, payment processors → business model clues.
- **Wappalyzer** (browser extension): Similar tech detection.
- **HTTPStatus codes & redirects**: Man-in-the-middle via network capture (legitimate after scoping approval).

### IP & Hosting

- **ASN lookups**: Company domain → IP → ASN (Autonomous System Number). BGP Toolkit reveals other IPs under same ASN.
- **Shodan (filtered)**: Internet-connected services indexed by IP/port. Can reveal misconfigured services, versions, banners.
- **Censys**: Certificate enumeration, host discovery.

### Cloud Footprint

- AWS/Azure/GCP buckets may be publicly exposed. Tools like:
  - **S3 bucket enumeration**: Try common patterns (company-name, company-name-backups, etc.) on AWS.
  - **Azure Blob Storage**: Similar enumeration.

---

## Relationship Mapping

### Supply Chain & Partnerships

- **SEC filings**: Material suppliers, partners, customers (in risk disclosures).
- **Press releases**: Partnerships, contracts, joint ventures.
- **LinkedIn**: Company → employees with listed experience at suppliers/partners.
- **B2B databases**: ZoomInfo, Apollo → business relationships.

### Investor Relationships

- **Investor registries**: Shareholding lists (public companies).
- **Board interlocks**: Officers serving on multiple company boards (suggests networks).

---

## Compliance & Regulatory Status

### OFAC & Sanctions

- **OFAC SDN List** (sanctionssearch.ofac.treas.gov): US Office of Foreign Assets Control; check if company/officers are sanctioned.
- **EU Sanctions Map** (sanctionsmap.eu): EU sanctions list.
- **OpenSanctions** (opensanctions.org): Aggregated persons/entities datasets.

### Business Licenses & Registrations

- **State Secretary offices**: Many states allow online business entity searches.
- **Professional licenses**: If company employs licensed professionals (accountants, lawyers, doctors), check state licensing boards.

### Anti-Corruption & AML

- **World Bank Sanctions**: Check if company has been flagged.
- **FATF Mutual Evaluation Reports**: Country-level compliance assessments.

---

## Workflow: Company Profile

1. **Initiate**: Company name + country → OpenCorporates.
2. **Registry search**: Pull legal entity details, officers, creation date.
3. **Financials**: SEC EDGAR (US) or equivalent registry.
4. **Workforce**: LinkedIn company page, job boards, GitHub.
5. **Breach exposure**: Email domain → Have I Been Pwned, Dehashed.
6. **Domain intel**: WHOIS, Certificate Transparency, BuiltWith, domain history.
7. **Relationships**: Suppliers, partners, investors (SEC filings, press releases).
8. **Regulatory**: OFAC, sanctions, litigation (PACER).
9. **Synthesis**: Org chart (officers, key employees), financial health, risk profile, infrastructure footprint.
10. **Archive**: Everything via archive.today or screenshots; document sources.
