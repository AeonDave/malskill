# Web Vulnerabilities and CVEs

Use this reference for framework-, library-, and product-specific web vulnerabilities that often short-circuit normal exploit development in web CTFs.

## Table of Contents
- [When to use this file](#when-to-use-this-file)
- [High-value targets](#high-value-targets)
- [Common exploit classes](#common-exploit-classes)
- [Triage workflow](#triage-workflow)

## When to use this file

Load this file when you already fingerprinted the stack or strongly suspect a product family, for example:
- Next.js
- Uvicorn / FastAPI
- WeasyPrint
- ExifTool-backed media processing
- Deno / Node frontend build chains
- browser behaviors that are version-sensitive

## High-value targets

Typical web CTF CVE buckets:
- auth or middleware bypasses
- SSRF and internal fetch abuse
- CRLF and header injection
- request splitting and parser differential issues
- file-read or upload-to-RCE product bugs
- admin-panel or CI/CD takeover bugs
- browser or headless automation quirks that leak tokens or enable JS unexpectedly

## Common exploit classes

Patterns that repeat across products:
- request metadata trusted too early (`Host`, middleware flags, forwarded headers)
- header/body boundary confusion
- parser inconsistency between validation function and transport function
- exposed or weakly protected helper endpoints
- attachment or document processors with side-fetch behavior
- optimistic trust in public keys, import maps, or external config

## Triage workflow

1. fingerprint exact framework or component from headers, static files, stack traces, source, or lockfiles
2. check version only as precisely as needed
3. test one stack-matching bypass first
4. if positive, chain only toward objective proof
5. if negative, fall back to generic references instead of CVE thrash

## See also

- `server-injection.md` — generic server-side sinks
- `server-execution.md` — execution and advanced chains
- `auth-access-control.md` — token and auth-impacting bugs
