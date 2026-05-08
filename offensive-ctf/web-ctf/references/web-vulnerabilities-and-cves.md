# Web Vulnerabilities and CVEs

Use this reference for framework-, library-, and product-specific web vulnerabilities that often short-circuit normal exploit development in web CTFs.

## Table of Contents
- [When to use this file](#when-to-use-this-file)
- [High-value targets](#high-value-targets)
- [Common exploit classes](#common-exploit-classes)
- [Modern framework pivots](#modern-framework-pivots)
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

## Modern framework pivots

React Server Components / Next.js:
- If responses or requests expose `Next-Action`, `text/x-component`, Flight payloads, or App Router server-action behavior, check React Server Components handling before generic Node payload iteration.
- CVE-2025-55182 affects the React Server Components server-function protocol and is surfaced through frameworks such as Next.js. In CTFs, treat it as a stack-fingerprinted deserialization/Flight-protocol lane, not as a blind spray.
- Useful proof signals are server-action responses, redirect/error headers, a harmless callback, or a controlled file-read/command echo in the challenge container.

Framework routing:
- Compare middleware checks with final route handlers, especially around encoded slashes, trailing dots, locale/basePath prefixes, rewrite rules, and method overrides.
- For serverless and edge runtimes, check whether the edge layer authenticates one normalized URL while the origin receives another.

Document and media processors:
- If upload handling invokes PDF/image/Office converters, model both the parser and the fetcher: local file reads, SSRF, attachment embedding, metadata execution, and archive expansion are separate lanes.

## Triage workflow

1. fingerprint exact framework or component from headers, static files, stack traces, source, or lockfiles
2. check version only as precisely as needed
3. test one stack-matching bypass first
4. if positive, chain only toward objective proof
5. if negative, fall back to generic references instead of CVE thrash

Primary external anchors for current RSC/Next.js issues:
- React advisory: https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components
- Next.js advisory: https://github.com/vercel/next.js/security/advisories/GHSA-9qr9-h5gf-34mp

## See also

- `server-injection.md` — generic server-side sinks
- `server-execution.md` — execution and advanced chains
- `auth-access-control.md` — token and auth-impacting bugs
