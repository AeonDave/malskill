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

## XXE, GraphQL, and parser abuse

Keep a parser-first mindset.

XXE:
- inline entities
- external DTDs for OOB
- document upload formats like DOCX/XML containers

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

## Command and query-adjacent injection

Before full RCE, check smaller adjacent wins:
- command wrappers with quoting mistakes
- GraphQL resolver injection into internal calls
- NoSQL / AQL fragments inside filters and merges
- SQL routed elsewhere -> use `sql-injection.md`

## See also

- `sql-injection.md` — dedicated SQLi reference
- `server-execution.md` — code-exec, deserialization, upload-to-RCE, advanced framework chains
- `field-notes.md` — compact quick-reference cheats
