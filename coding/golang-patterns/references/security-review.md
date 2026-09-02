# Security Review

Use this reference when auditing Go source for security bugs: reviewing an unfamiliar package,
hardening code against untrusted input, or checking a dependency tree. For `unsafe`/`cgo`/syscall
soundness, load `unsafe-cgo.md`. For fuzzing and the race detector, see the `golang-testing`
skill's `fuzzing-and-race.md`.

## Contents

- [Orient in an unfamiliar codebase](#orient-in-an-unfamiliar-codebase)
- [Grep patterns for risky constructs](#grep-patterns-for-risky-constructs)
- [Denial of service](#denial-of-service)
- [Untrusted input](#untrusted-input)
- [HTTP and TLS defaults](#http-and-tls-defaults)
- [Crypto and auth](#crypto-and-auth)
- [Concurrency-derived bugs](#concurrency-derived-bugs)
- [Supply chain](#supply-chain)
- [What to hand off](#what-to-hand-off)

## Orient in an unfamiliar codebase

- `go list -m all` — full module graph; `go mod why <mod>` — why a dep is pulled in.
- `go doc ./...` + gopls (find-references, incoming-calls, list-implementors) to trace how untrusted
  input flows to sensitive sinks.
- Identify **trust boundaries** first: `main`, HTTP/gRPC handlers, `Unmarshal`/decoder inputs, any
  `os.Getenv`/flag/config load, `cgo`/`syscall` edges, `init()` in third-party deps.

## Grep patterns for risky constructs

Fast first pass; each hit is a lead, not a verdict:

```
rg -n "unsafe\.|reflect\.Value|//go:linkname|//go:nosplit"      # unsafe / linker escapes
rg -n "exec\.Command|exec\.CommandContext|/bin/sh|cmd\.exe"     # command execution
rg -n "os\.Open|os\.Create|os\.ReadFile|filepath\.Join"         # path handling / traversal
rg -n "html/template|text/template"                             # template auto-escape choice
rg -n "InsecureSkipVerify|MinVersion|CipherSuites"              # TLS defaults
rg -n "sql\.\.Query|db\.\.Query|Sprintf.*SELECT|Sprintf.*INSERT" # SQL built via Sprintf
rg -n "json\.Unmarshal|yaml\.Unmarshal|gob\.NewDecoder"         # deserialization sinks
rg -n "http\.ListenAndServe\(|http\.Server\{"                   # server timeouts?
rg -n "rand\.Intn|math/rand"                                    # non-CSPRNG use
```

## Denial of service

Go prevents memory corruption but not resource exhaustion or panics-as-crash:

- **Panics on attacker input** crash the process by default (unless a `recover` sits above): nil
  deref, slice `s[i]` out of range, integer division by zero, sending on a closed channel, `assert`
  helpers panicking. Handlers behind `net/http` are recovered by the server, but custom goroutines
  are not — a panic in a spawned goroutine terminates the program.
- **Unbounded request bodies**: wrap with `http.MaxBytesReader(w, r.Body, N)` before `json.Decode`;
  otherwise a large POST forces `ioutil.ReadAll`/decoder to buffer arbitrary bytes.
- **Decoder bombs**: `json`/`yaml`/`xml` decoders and `encoding/gob` will happily inflate nested
  structures. Set body caps and depth limits; reject `Content-Length` outliers early.
- **Zip/gzip bombs**: cap the decompressed byte count (`io.LimitReader` on the reader you *return*
  from `NewReader`, not on the input).
- **Slow-loris / unbounded server**: `http.Server{}` with zero timeouts holds connections forever.
  Always set `ReadHeaderTimeout` at minimum; add `ReadTimeout`, `WriteTimeout`, `IdleTimeout`.
- **Unbounded goroutine spawn** on request: any handler that does `go doWork(r)` without a semaphore
  or `errgroup.SetLimit` is a DoS. Cap fan-out; use bounded channels.
- **Regex from user input** or catastrophic backtracking — `regexp` is RE2 (linear) so backtracking
  ReDoS does not apply, but compiling attacker-controlled patterns still costs CPU/memory.

## Untrusted input

- **Path traversal (Go 1.24+)**: use `os.OpenRoot("/safe/root")` and its `Root.Open`/`Root.Create`/
  `Root.Stat` — they refuse paths escaping the root, including via symlinks. Before Go 1.24, use
  `filepath.IsLocal` plus a resolved-prefix check; do not rely on `filepath.Clean` + `HasPrefix`
  alone.
- **Command injection**: never build a shell string. Use `exec.CommandContext(ctx, prog, args...)`
  with a fixed program and separate arguments; do not pipe user data into `sh -c` / `cmd /C`.
  Allowlist the program name when it is dynamic.
- **SQL injection**: always parameterize — `db.QueryContext(ctx, "... WHERE email = $1", email)`.
  Never `fmt.Sprintf` values into the query. Table/column names cannot be parameters — allowlist
  them against a constant set.
- **Template injection / XSS**: use `html/template` (auto-escapes per context) for HTML output;
  `text/template` does not escape and must not render into an HTML response. `template.HTML(...)`
  bypasses escaping — treat every call as a review item.
- **Deserialization**: decode into a typed struct, then validate the decoded value. `encoding/gob`
  and third-party formats that instantiate arbitrary types on read are hostile territory — avoid
  on attacker-controlled input.
- **SSRF**: validate host/scheme against an allowlist after parsing (`url.Parse`); block private and
  link-local ranges when fetching user-supplied URLs.
- **Typed-nil trap**: an interface holding a `(*T)(nil)` is **not** `== nil`. Return `nil`
  explicitly at the interface level; a common source of "handled" errors that then panic downstream.

## HTTP and TLS defaults

- `http.Server` needs timeouts (see above). `http.DefaultClient` has none — construct an
  `http.Client{Timeout: ...}` for outbound calls, especially SSRF-relevant fetches.
- TLS: `tls.Config{MinVersion: tls.VersionTLS12}` at minimum; TLS 1.3 preferred. `InsecureSkipVerify:
  true` is only for local tests — reject it in code review outside tests.
- Behind a proxy, trust `X-Forwarded-For` only if you terminate a known proxy; otherwise a client
  can forge the client IP for rate limits and audit logs.
- `net/http/pprof` and `expvar` register handlers on `http.DefaultServeMux` at import time — do not
  expose the default mux publicly. Use a private mux for `pprof` and bind it to `127.0.0.1`.

## Crypto and auth

- Randomness: `crypto/rand` for keys/tokens/nonces/session IDs; `math/rand` (and `math/rand/v2`) is
  **not** cryptographically secure regardless of seeding.
- Password hashing: `golang.org/x/crypto/bcrypt` (or `argon2`); never MD5/SHA-256 for passwords.
- Constant-time comparison: `crypto/subtle.ConstantTimeCompare` for MACs/tokens/secrets — plain
  `==` on byte slices leaks length/prefix via timing.
- JWT: reject `alg: none`; verify against an expected algorithm and a keyset you control; validate
  `exp`, `iss`, `aud`. Don't parse claims before verifying the signature.
- Secrets: never log them, never derive `String()`/`Error()` that includes them, never commit;
  `.env`/`*.pem`/`*.key`/`credentials.json` belong in `.gitignore` and pre-commit secret scanning
  (`gitleaks`, `trufflehog`).

## Concurrency-derived bugs

Concurrency bugs often *are* security bugs — races on auth state, closed-channel panics, goroutine
leaks that DoS a service. Baseline defenses:

- `go test -race ./...` in CI on the packages that see concurrent access; race findings are real,
  not flakes.
- `go vet` includes `waitgroup` and (via gopls) `waitgroupgo` — `WaitGroup.Add` inside a new
  goroutine races with `Wait`. Move `Add` before `go func()`, or use `wg.Go(...)` (Go 1.25+).
- Goroutine leaks are memory exhaustion in disguise; hunt them with `pprof/goroutine?debug=2` and
  the `go.uber.org/goleak` gate in tests (see `golang-testing`).

## Supply chain

- `govulncheck ./...` — official Go vuln scanner; reports vulns *actually reachable* from the code
  (not just present in `go.sum`). Run in CI and fail on findings you haven't triaged.
- `gosec` — static analyzer for common insecure patterns (weak crypto, hardcoded creds, sql
  concatenation, TLS misconfig). Noisy but useful as a first pass.
- `staticcheck` / `golangci-lint` — general static analysis; catches nil-deref, defer-in-loop,
  useless recover, `errcheck`.
- Pin a `go.sum` and build `-mod=readonly` (or `-mod=vendor`) in CI. Review `//go:generate` and
  `init()` in dependencies — they run at build/import time and are a supply-chain vector.
- Prefer `GOFLAGS=-trimpath -buildvcs=false` for reproducible artifact builds; committed
  `default.pgo` benefits from the same reproducibility rules.

## What to hand off

Per finding: source location, the untrusted-input path that reaches it, the concrete impact
(crash/DoS, RCE, secret leak, privilege escalation), and a minimal fix or reproducer. Separate
proven issues (repro, race hit, or fuzz crash) from suspected ones needing confirmation.
