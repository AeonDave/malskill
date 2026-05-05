# Targeted Source Filters

Use this reference after the problem fingerprint exists and the next question is **where** a decisive hint is likely to live. Pick one or two lanes; do not sweep every site.

## Contents

- Query shape
- Research papers and preprints
- Standards and specifications
- Source code, commits, and implementation discussions
- Issue trackers and advisories
- Exploit and PoC sources
- Security research blogs and technical articles
- Q&A and public discussions
- Public solution notes and writeups
- Jina and Tavily workflow

## Query shape

Build source-filtered queries from:

```text
site:{source} {exact anomaly} {version|parameter|error|primitive} {source-type term}
```

Good source-type terms: `paper`, `implementation`, `issue`, `commit`, `patch`, `spec`, `standard`, `discussion`, `writeup`, `proof`, `bounds`, `PoC`, `regression`, `workaround`.

## Research papers and preprints

Use when the missing hint is likely a theorem, construction, measurement result, attack name, or bound.

```text
site:arxiv.org {attack or anomaly} {primitive or subsystem}
site:eprint.iacr.org {crypto attack phrase} {parameter clue}
site:openreview.net {model or method anomaly} {paper}
site:usenix.org/conference {bug class or system} {paper}
site:ndss-symposium.org {protocol or vulnerability class} {paper}
site:dl.acm.org {system or bug class} {exact phrase}
site:ieeexplore.ieee.org {protocol or implementation} {exact phrase}
```

If a publisher page is thin or paywalled, search the exact paper title plus `pdf`, `arxiv`, `author`, or `github`.

## Standards and specifications

Use when behavior depends on a protocol rule, file format, parser edge case, or normative requirement.

```text
site:rfc-editor.org {protocol} {exact keyword}
site:datatracker.ietf.org {protocol draft} {edge case}
site:w3.org/TR {web standard} {exact keyword}
site:csrc.nist.gov {algorithm or standard} {mode or parameter}
site:oasis-open.org {standard name} {field or behavior}
```

Fetch the final spec first, then one-hop to errata, drafts, or implementation notes only if the mismatch remains unclear.

## Source code, commits, and implementation discussions

Use when the hint is probably in a fix, reviewer comment, issue, or compatibility workaround.

```text
site:github.com {exact error} {library or symbol}
site:github.com {function name} {anomaly} issue
site:github.com {attack or bug phrase} {language} implementation
site:gitlab.com {exact error} {project or library}
site:lore.kernel.org {subsystem or symbol} {exact phrase}
site:lists.openssl.org {function or protocol} {exact phrase}
site:mail.openjdk.org {class or JVM behavior} {exact phrase}
site:oss-security.openwall.com {CVE or bug class} {project}
```

When using GitHub native search, prefer focused scopes such as `repo:owner/name`, `in:issues`, `in:comments`, `in:commits`, or `path:`.

## Issue trackers and advisories

Use when the problem has a version, CVE, regression, patch level, or vendor behavior clue.

```text
site:nvd.nist.gov {CVE or product} {version}
site:cve.org {CVE or product} {weakness}
site:osv.dev {package} {version or symbol}
site:github.com/advisories {package} {CVE or function}
site:bugzilla.mozilla.org {exact error or component}
site:bugs.chromium.org {exact error or component}
site:issues.apache.org {project} {exact phrase}
```

Prioritize sources that include affected versions, fixing commits, tests, or minimal reproducer details.

## Exploit and PoC sources

Use when the version and affected component are already known and the next hint is likely a public PoC, module, template, or exploit note.

```text
site:exploit-db.com {CVE or product version}
site:packetstormsecurity.com {CVE or product version}
site:rapid7.com/db/modules {CVE or product}
site:github.com {CVE} PoC {product}
site:gist.github.com {CVE or exact bug phrase}
site:github.com/projectdiscovery/nuclei-templates {CVE or product}
```

Load `references/exploit-hint-recipes.md` for the full version/changelog/diff/PoC workflow.

## Security research blogs and technical articles

Use when papers are too abstract and you need a practical reproduction, debugging note, or exploit constraint explanation.

```text
site:googleprojectzero.blogspot.com {bug class or product} {exact clue}
site:portswigger.net/research {web behavior or bug class}
site:blog.trailofbits.com {tool or vulnerability class} {implementation}
site:research.nccgroup.com {protocol or product} {bug class}
site:zerodayinitiative.com/blog {product or bug class} {root cause}
site:msrc.microsoft.com/blog {CVE or product} {root cause}
```

Prefer posts with code, traces, diagrams, patch links, or explicit environmental constraints.

## Q&A and public discussions

Use when the clue is a confusing equation, API behavior, compiler/runtime error, or edge case others may have debugged.

```text
site:crypto.stackexchange.com {parameter relation} {primitive}
site:security.stackexchange.com {bug class} {constraint}
site:reverseengineering.stackexchange.com {binary behavior} {symbol or error}
site:math.stackexchange.com {equation or theorem clue}
site:stackoverflow.com {exact error} {library or version}
site:news.ycombinator.com {paper title or bug phrase}
```

Treat discussions as leads. Trust answers more when they cite specs, papers, commits, or reproducible code.

## Public solution notes and writeups

Use when the problem resembles a known lab, puzzle, benchmark, or reproducible bug pattern and you need the transferable trick.

```text
site:github.io {attack or bug phrase} {exact clue}
site:gist.github.com {exact error or code phrase}
site:medium.com {technique} {implementation clue}
site:dev.to {library or runtime error} {workaround}
site:hackmd.io {equation or exploit constraint} {writeup}
```

Extract the technique and validation condition, not the surrounding narrative.

## Jina and Tavily workflow

Use Tavily for discovery and claim triage, then fetch primary pages before citing them.

Use Jina Reader for clean extraction of a candidate page:

```text
https://r.jina.ai/{full-url-with-scheme}
```

Stop when one source gives a local test or when high-signal sources contradict the current hypothesis.
