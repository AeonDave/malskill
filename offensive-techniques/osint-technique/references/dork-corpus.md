# Dork Corpus — Cross-Engine Reusable Templates

Curated dork corpus organized by intent. Run each across Google **and** Bing **and** DuckDuckGo (results diverge significantly). Substitute `{target}` (company name) and `{domain}` (DNS root).

## Hard rules

- Engines rotate index coverage; never rely on a single engine.
- Wrap multi-word values in `"..."`.
- DuckDuckGo strips many advanced operators silently — verify with `site:` test first.
- For automation, prefer **paid SerpAPI / Serper.dev** over scraping HTML; raw scraping triggers captchas fast.
- Pair each hit with `archive.org/web/save/<url>` immediately — pastes/repos disappear.

---

## A. Credential & Token Leaks

```text
"{target}" "password" filetype:txt
"{target}" "api_key" OR "apikey" filetype:env
"{target}" "BEGIN RSA PRIVATE KEY"
"{target}" filetype:log "password"
"{target}" "AWS_ACCESS_KEY_ID" filetype:env
"{target}" "client_secret" filetype:json
"{domain}" "DB_PASSWORD" filetype:env
"{domain}" intext:"@{domain}" filetype:txt "password"
site:pastebin.com "{target}" "password"
site:gist.github.com "{domain}"
```

## B. Config Files

```text
"{target}" filetype:yml "password"
"{target}" filetype:conf "password"
"{target}" filetype:ini "password"
"{target}" filetype:xml "<password>"
"{target}" filetype:properties "password="
inurl:"{domain}" ext:env
inurl:"{domain}" ext:bak
inurl:"{domain}" ext:swp
```

## C. Exposed Services / Panels

```text
site:{domain} intitle:"phpMyAdmin"
site:{domain} intitle:"Jenkins"
site:{domain} intitle:"Grafana"
site:{domain} intitle:"Kibana"
site:{domain} intitle:"Index of /"
site:{domain} inurl:"/admin"
site:{domain} inurl:"/wp-admin"
site:{domain} inurl:"/.git/"
site:{domain} inurl:"/.svn/"
site:{domain} inurl:"/server-status"
site:{domain} inurl:"/swagger"
site:{domain} inurl:"/graphql"
site:{domain} inurl:"/actuator"
```

## D. Code & Repository Leaks

```text
site:github.com "{target}" password
site:github.com "{domain}" api_key
site:github.com "{target}" "BEGIN PRIVATE KEY"
site:gitlab.com "{target}"
site:bitbucket.org "{target}"
site:codeberg.org "{target}"
site:sourcehut.org "{target}"
"@{domain}" site:github.com
```
> Then escalate per [code-and-package-leaks.md](code-and-package-leaks.md).

## E. Documents & Sensitive Files

```text
site:{domain} filetype:pdf "confidential"
site:{domain} filetype:pdf "internal use only"
site:{domain} filetype:xlsx
site:{domain} filetype:docx "draft"
site:{domain} filetype:pptx "internal"
site:{domain} "Q3 2025" filetype:pdf
"{target}" "org chart" filetype:pdf
"{target}" "incident report" filetype:pdf
```

## F. Infrastructure Discovery

```text
"{domain}" site:shodan.io
"{domain}" site:censys.io
"{domain}" site:fofa.info
"{target}" site:zoomeye.org
"{domain}" -site:{domain}   # mirrors / shadow domains
ip:"<known-IP>" site:shodan.io
```

## G. People & Identity

```text
site:linkedin.com/in "{target}"
"@{domain}" site:linkedin.com
"@{domain}" site:twitter.com OR site:x.com
"@{domain}" site:facebook.com
"@{domain}" intext:"@{domain}"
"{target}" "employee directory"
```

## H. Breach Indicators

```text
"{domain}" site:haveibeenpwned.com
"{target}" site:dehashed.com
"{target}" site:intelx.io
"{domain}" "data breach"
"{target}" "leaked database"
"{target}" intext:"compromised"
```

## I. Vendor & Supply-Chain

```text
"{target}" "case study" site:vendor.com
"{target}" "partner" "{technology}"
"{target}" "uses" "{SaaS-name}"
"{target}" "is built on" OR "powered by"
"{target}" "trusted by" site:*.io
```

## Workflow

For each dork:
1. Run across the 3 engines (Google → Bing → DuckDuckGo) — capture distinct result sets.
2. Top 20 results per engine → manual triage; archive promising hits immediately.
3. Pivot leaked artifacts to validators in [secret-patterns-and-validators.md](secret-patterns-and-validators.md).
4. Pivot code/repo hits to [code-and-package-leaks.md](code-and-package-leaks.md).
5. Pivot people hits to [linkedin-and-tech-stack-osint.md](linkedin-and-tech-stack-osint.md).
6. Severity per [attack-path-and-severity.md](attack-path-and-severity.md).
