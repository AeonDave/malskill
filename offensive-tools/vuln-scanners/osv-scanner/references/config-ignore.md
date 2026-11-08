# OSV-Scanner configuration and call analysis

Place `osv-scanner.toml` beside each scanned lockfile; it does not propagate to child directories. `--config /path/to/config.toml` overrides directory-specific configurations for all parsed files. Example exception:

```toml
[[IgnoredVulns]]
id = "GO-2022-0968"
ignoreUntil = 2027-12-31
reason = "Documented applicability assessment"
```

Ignoring an ID also ignores its aliases. Review exceptions and expiry dates against the [v2.7.0 configuration reference](https://github.com/google/osv-scanner/blob/v2.7.0/docs/configuration.md).

Go call analysis is enabled by default and needs `go` on `PATH`; `--no-call-analysis=go` disables it. Rust call analysis is experimental and opt-in with `--call-analysis=rust`: it compiles the project and may run dependency build scripts. An uncalled result is an analysis result, not a guarantee of non-exposure. See the [source-scanning documentation](https://github.com/google/osv-scanner/blob/v2.7.0/docs/scan-source.md#scanning-with-call-analysis) for prerequisites and limitations.
