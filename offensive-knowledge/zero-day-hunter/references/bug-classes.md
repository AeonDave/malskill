# Bug Classes and False-Positive Filters

## High-value bug classes

### C and C++

- fixed-size stack or heap buffer overflow
- integer overflow or truncation in size math
- null dereference in parser or request handling paths
- type confusion on unions, tagged structs, variant-like data
- out-of-bounds read or write through index or length misuse
- use-after-free with a believable ownership path

### Go and Rust

Focus less on memory corruption and more on:

- path traversal
- authorization gaps
- unsafe deserialization
- panic or unwrap on attacker-controlled input causing availability issues
- misuse of unsafe blocks, FFI, or C bindings

### Python, JavaScript, PHP, Java, C#

Prioritize:

- command injection
- path traversal
- deserialization problems
- SSRF and URL fetch trust issues
- template injection
- authentication or authorization mistakes
- arbitrary file write or plugin loading issues

## False-positive filters

A candidate becomes weaker when:

- the suspicious function is `static` or private and all callers enforce the precondition
- the value is attacker-controlled in name only but bounded by trusted parsing upstream
- the code is test-only, example-only, or dead
- the finding relies on impossible integer ranges for the target type
- the model cites a constant but never resolves its real numeric value

## Useful review patterns

Search for:

- callers of the function named in the finding
- constant definitions used as bounds
- validation helpers that sanitize the relevant field
- feature flags or build guards that disable the path
- earlier parsing layers that cap sizes or normalize paths

## Reporting language

Good wording:

- likely reachable from request parser input
- candidate stack overflow if `len` exceeds local buffer size
- review did not find a sufficient bound before copy

Avoid:

- definite RCE without evidence
- guaranteed exploitability
- zero false positives
