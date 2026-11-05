# Targeted Source Filters

Use this reference when choosing **where** a useful hint is likely to live. Start with the available clue, even if its technical name is unknown. Pick the most relevant lane; switch when its results do not resolve the question.

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

Check the applicable specification version and relevant errata. Follow drafts or implementation notes when they address the unresolved behavior; do not substitute a draft for the version actually implemented.

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

For [GitHub issue/PR search](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests), use `repo:owner/name`, `is:issue` or `is:pr`, and `in:title,body,comments` as needed. Select code or commit search separately and use that search type's supported qualifiers; issue-search syntax is not interchangeable with code-search syntax.

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

Load [exploit-hint-recipes.md](exploit-hint-recipes.md) when the clue needs version, changelog, patch or PoC applicability checks.

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
