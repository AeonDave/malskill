# Server-Side Execution and Advanced Chains

Use this reference for server-side code execution, deserialization, upload-to-RCE, dangerous framework CVEs, and deep exploit chains after a server-side sink is confirmed.

## Table of Contents
- [Fast triage](#fast-triage)
- [Language and runtime injection](#language-and-runtime-injection)
- [Uploads and post-processing](#uploads-and-post-processing)
- [Deserialization](#deserialization)
- [Framework and product chains](#framework-and-product-chains)
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

## Deserialization

Check language first, then gadget ecosystem.

Common classes:
- Java serialized objects and ysoserial chains
- Python pickle abuse
- PHP object injection in cookies/sessions
- unsafe JSON-to-object binders with magic methods

Minimal approach:
- start with blind DNS or timing gadget if execution proof is noisy,
- move to file read or command exec only when gadget compatibility is proven.

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
