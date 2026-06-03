---
name: jazzer
description: "Auth/lab ref: Coverage-guided in-process fuzzing for JVM (Java/Kotlin/etc), based on libFuzzer concepts."
license: Apache-2.0
compatibility: "Linux/macOS/Windows x64 JVM workflows; Maven/Gradle/Bazel supported."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# jazzer

JVM-native fuzzing engine with `@FuzzTest` workflow and built-in security bug detectors.

## Quick Start

```xml
<!-- pom.xml -->
<dependency>
  <groupId>com.code-intelligence</groupId>
  <artifactId>jazzer-junit</artifactId>
  <version>LATEST</version>
</dependency>
```

```java
@FuzzTest
void fuzzDecode(String input) {
  assertEquals(input, decode(encode(input)));
}
```

```bash
# Fuzzing mode
JAZZER_FUZZ=1 mvn test
```

## Operator Flow

1. Start with JUnit `@FuzzTest` in a narrow API surface.
2. Seed meaningful examples (parameter sources + existing regression inputs).
3. Run fuzz mode to discover, then store crash inputs under test resources.
4. Keep regression mode in CI to prevent bug reintroduction.
5. Expand instrumentation scope only when throughput remains acceptable.

## Key Points

- Regression mode by default; fuzz mode via env var.
- Stores generated corpus and crashing inputs in predictable directories.
- Includes bug detectors (e.g., SSRF / path traversal / command injection classes).

## Practical Tricks

- Use annotations (`@WithUtf8Length`, `@InRange`, etc.) to constrain data and improve signal density.
- Tune run duration with `maxDuration` / `max_total_time` style controls.
- Configure instrumentation includes/excludes to avoid useless classpath overhead.
- Explicitly manage detector hooks if false positives appear in complex multi-thread setups.

## Common Pitfalls

- One giant fuzz test that mixes unrelated APIs reduces triage quality.
- Ignoring corpus path conventions causes lost regressions.
- Treating finder output as final root cause without replaying and minimizing reproducer.

## Configuration Notes

- Option precedence matters: defaults < env vars < system properties < JUnit params < CLI.
- For standalone mode, verify classpath and target class/method wiring first.

## Resources

- https://github.com/CodeIntelligenceTesting/jazzer
- https://github.com/CodeIntelligenceTesting/jazzer/blob/main/docs/arguments-and-configuration-options.md
- https://llvm.org/docs/LibFuzzer.html
- https://google.github.io/oss-fuzz/getting-started/new-project-guide/jvm-lang/
