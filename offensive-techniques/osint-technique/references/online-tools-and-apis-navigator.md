# Online Tools & APIs Navigator

This reference maps online OSINT tools and APIs by research domain. It bridges technique methodology with practical online resources—no downloads required. Updated regularly via Tavily research and user feedback.

**Navigation**: Tools are grouped by OSINT domain (person research, infrastructure, etc.). Each entry includes tool name, URL, API availability, free tier, and best use case.

---

## People & Identity Research

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| Have I Been Pwned | haveibeenpwned.com | ✓ | Yes | Breach search by email |
| Dehashed | dehashed.com | ✓ | Freemium | Credential search, plaintext passwords |
| IntelX | intelx.io | ✓ | Freemium | Dark web, paste, breach index |
| LeakCheck | leakcheck.io | ✗ | Freemium | Breach aggregator |
| Epieos | epieos.com | ✗ | Yes | Email enrichment, pivot data |
| Holehe | holehe.me | ✓ | Yes | Email → platforms registered |
| Sherlock | github.com/sherlock-project/sherlock | N/A | Yes (CLI) | Username search across 300+ sites |
| Maigret | github.com/soxoj/maigret | N/A | Yes (CLI) | Username enumeration, profile data |
| TruePeopleSearch | truepeoplesearch.com | ✗ | Yes | Free U.S. people search |
| Spokeo | spokeo.com | ✗ | Freemium | People search engine |
| Pipl | pipl.com | ✓ | Freemium | Deep web people search |
| Hunter.io | hunter.io | ✓ | Freemium | Email discovery by domain |
| ReverseEmail | any reverse-email service | Varies | Freemium | Email → associated data |
| PimEyes | pimeyes.com | ✓ | Freemium | Facial search engine |
| FaceCheck | facecheck.id | ✓ | Freemium | Reverse face search |
| TrueCaller | truecaller.com | ✓ | Freemium | Phone number lookup, caller ID |
| ThatsThem | thatsthem.com | ✗ | Yes | Reverse phone search |
| EmailRep | emailrep.io | ✓ | Yes | Email reputation, associated data |

---

## Company & Organization Research

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| OpenCorporates | opencorporates.com | ✓ | Yes (limited) | Company filings, officers, registration |
| SEC EDGAR | sec.gov/edgar | N/A | Yes | U.S. public company filings |
| OpenOwnership | register.openownership.org | ✓ | Yes | Beneficial ownership datasets |
| EU Tenders | ted.europa.eu | N/A | Yes | EU procurement records |
| Rusprofile | rusprofile.ru | N/A | Yes | Russian company data |
| Kontur.Focus | focus.kontur.ru | N/A | Freemium | Russian business data |
| Crunchbase | crunchbase.com | ✓ | Freemium | Startup funding, investors, people |
| LinkedIn | linkedin.com | Limited API | Yes (requires login) | Employee data, company profiles |
| BuiltWith | builtwith.com | ✓ | Freemium | Tech stack, analytics, CMS |
| Wappalyzer | wappalyzer.com | N/A | Yes (extension) | Tech detection |
| Clearbit | clearbit.com | ✓ | Freemium | Company + person enrichment |

---

## Domain & Infrastructure Research

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| crt.sh | crt.sh | ✓ | Yes | Certificate Transparency logs |
| SecurityTrails | securitytrails.com | ✓ | Freemium | PDNS, WHOIS history, host history |
| Shodan | shodan.io | ✓ | Freemium | Internet-connected device search |
| Censys | search.censys.io | ✓ | Freemium | Host, certificate, and service enumeration |
| BinaryEdge | binaryedge.io | ✓ | Freemium | Internet scanner (alternative to Shodan) |
| FOFA | fofa.so | ✓ | Freemium | Chinese cyberspace search (Asia-Pacific focus) |
| ZoomEye | zoomeye.org | ✓ | Freemium | Chinese cyberspace search |
| Netlas | netlas.io | ✓ | Freemium | HTTP/DNS/certificate pivots |
| LeakIX | leakix.net | ✓ | Yes | Search exposed services + leaked credentials |
| WHOIS Lookup | whois.com or icannlookup | N/A | Yes | Domain registrant info, expiry |
| Hurricane Electric BGP | bgp.he.net | N/A | Yes | ASN lookup, prefixes, routing |
| BGPView | bgpview.io | ✓ | Yes | ASN explorer, prefix routes |
| RIPEstat | stat.ripe.net | ✓ | Yes | IP/ASN history, geolocation, routing |
| Robtex | robtex.com | N/A | Yes | PDNS, infrastructure pivots |
| MXToolbox | mxtoolbox.com | N/A | Yes | WHOIS, MX, reverse IP, DNS |

---

## Breach & Credential Research

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| Have I Been Pwned | haveibeenpwned.com | ✓ | Yes | Breach search |
| Dehashed | dehashed.com | ✓ | Freemium | Credential search |
| LeakCheck | leakcheck.io | ✗ | Freemium | Breach aggregator |
| IntelX | intelx.io | ✓ | Freemium | Dark web index |
| Cavalier (Hudson Rock) | cavalier.hudsonrock.com | ✗ | Freemium | Infostealer logs |
| BreachDirectory | breachdirectory.org | ✗ | Yes | Recent breach index |
| Scattered Secrets | scatteredsecrets.com | ✗ | Yes | Breach search |
| VirusTotal | virustotal.com | ✓ | Freemium | File/URL/IP/domain reputation |

---

## Image & Geospatial Intelligence

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| Google Lens | lens.google.com | N/A | Yes | Reverse image search |
| TinEye | tineye.com | ✓ | Freemium | Reverse image search |
| Yandex Images | yandex.com/images | N/A | Yes | Reverse image search (strong for Russian) |
| Bing Image Search | bing.com/images | N/A | Yes | Alternative image search |
| PimEyes | pimeyes.com | ✓ | Freemium | Facial search engine |
| FaceCheck | facecheck.id | ✓ | Freemium | Face search |
| Google Earth Pro | earth.google.com/web | N/A | Yes | Satellite imagery + historical |
| Sentinel Hub EO Browser | apps.sentinel-hub.com/eo-browser | ✓ | Yes | Sentinel + Landsat satellite data |
| NASA Worldview | worldview.earthdata.nasa.gov | N/A | Yes | NASA satellite imagery |
| Zoom Earth | zoom.earth | N/A | Yes | Live satellite + weather |
| Wayback Imagery | livingatlas.arcgis.com/wayback | N/A | Yes | Historical satellite images |
| SunCalc | suncalc.org | N/A | Yes | Sun position, shadow analysis |
| ShadeMap | shademap.app | N/A | Yes | 3D shadow simulator |
| Mapillary | mapillary.com | ✓ | Yes | Crowdsourced street-level imagery |
| KartaView | kartaview.org | ✓ | Yes | Open-source street imagery |
| Google Maps | maps.google.com | ✓ | Limited | Street View, navigation |
| Overpass Turbo | overpass-turbo.eu | N/A | Yes | Advanced OpenStreetMap queries |
| Stellarium | stellarium.org | N/A | Yes (desktop) | Planetarium software |
| ExifTool | exiftool.org | N/A | Yes | EXIF metadata extraction |
| Forensically | 29a.ch/photo-forensics | N/A | Yes | Image forensics, ELA, metadata |
| Sensity AI | sensity.ai | ✓ | Freemium | Deepfake detection |

---

## Social Media & Profiling

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| snscrape | github.com/JustAnotherArchivist/snscrape | N/A | Yes (CLI) | X/Twitter scraping |
| Picuki | picuki.com | N/A | Yes | Instagram viewing (no login required) |
| TGStat | tgstat.com | ✓ | Freemium | Telegram channel analytics |
| Telemetr | telemetr.io | N/A | Freemium | Telegram analytics |
| FediSearch | fedisearch.skorpil.cz | N/A | Yes | Mastodon cross-instance search |
| Firesky | firesky.tv | N/A | Yes | Bluesky real-time monitoring |
| SkyView | bsky.jazco.dev | N/A | Yes | Bluesky follower graphs |
| Reveddit | reveddit.com | N/A | Yes | Reddit deleted content recovery |
| RedTrack.social | redtrack.social | N/A | Yes | Reddit user history |
| Wayback Machine | archive.org | N/A | Yes | Historical website snapshots |

---

## Threat Intelligence & Malware

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| VirusTotal | virustotal.com | ✓ | Freemium | File/URL/IP reputation, detections |
| MalwareBazaar | bazaar.abuse.ch | ✓ | Yes | Malware sample sharing |
| URLHaus | urlhaus.abuse.ch | ✓ | Yes | Malicious URLs |
| ThreatFox | threatfox.abuse.ch | ✓ | Yes | Malware C2 IOCs |
| Malpedia | malpedia.caad.fkie.fraunhofer.de | ✓ | Yes | Malware families, YARA rules |
| ANY.RUN | any.run | ✓ | Freemium | Sandboxed malware execution |
| Hybrid Analysis | hybrid-analysis.com | ✓ | Freemium | Sandbox analysis |
| Tria.ge | tria.ge | ✓ | Yes | Quick malware analysis |
| MISP | misp-project.org | ✓ | Yes (self-hosted) | Threat intelligence platform |
| OpenCTI | opencti.io | ✓ | Yes (self-hosted) | CTI knowledge graph |

---

## OSINT Frameworks & Aggregators

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| OSINT Framework | osintframework.com | N/A | Yes | Bookmarked tool directory |
| IntelTechniques Tools | inteltechniques.com/tools | N/A | Yes | Suite of investigative tools |
| Bellingcat Toolkit | bellingcat.com/resources | N/A | Yes | Investigative journalism tools |
| CyberSudo Toolkit | docs.google.com/spreadsheets/d/1EC0sKA_W9znzsxUt0wye9UYtyATXw5m8 | N/A | Yes | OSINT websites list |
| awesome-osint | github.com/jivoi/awesome-osint | N/A | Yes | Curated OSINT resource list |

---

## Archival & Evidence Preservation

| Tool | URL | API | Free Tier | Use Case |
|------|-----|-----|-----------|----------|
| archive.today | archive.today | N/A | Yes | One-page archiver with screenshot |
| Wayback Machine | archive.org | ✓ (SavePageNow) | Yes | Web snapshots + historical |
| URLScan.io | urlscan.io | ✓ | Freemium | On-demand page scan, resource map |
| SingleFileZ | github.com/gildas-lormeau/SingleFileZ | N/A | Yes (extension) | Offline HTML archives |
| ArchiveBox | archivebox.io | N/A | Yes (self-hosted) | Self-hosted web archiver |

---

## Notes on Tavily Research Integration

This navigator is updated based on:
1. **Tavily search**: Regular scans for new/updated OSINT tools, API changes, free tier shifts.
2. **User feedback**: Community contributions and field reports.
3. **Tool deprecation**: Removing tools that are abandoned or whose APIs have changed materially.

**Last updated**: 2025-04-30 (Tavily research cycle)

**Tools added in 2025**:
- LeakIX (publicly exposed services search)
- Netlas (large-scale pivots)
- CyberSudo Toolkit (consolidated OSINT websites list)
- Firesky (Bluesky real-time monitoring)

**Deprecations**:
- Twitter API v1 (now requires paid tier; snscrape remains free alternative)
- CensysRender (service discontinued)

---

## Anti-Patterns

- **Over-subscribing**: Too many free accounts spreads your focus. Pick 3-4 per domain.
- **Ignoring API rate limits**: Aggressive querying triggers bans.
- **Assuming "free" = free forever**: Services change; maintain local mirrors or fallbacks.
- **Not verifying tool status**: Some APIs go down or require authentication updates.
- **Missing regional alternatives**: Shodan/Censys are US-centric; FOFA/ZoomEye are stronger in Asia.
