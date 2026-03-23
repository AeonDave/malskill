# Measurement Workflow

Use this reference when a Rust performance claim needs a real baseline.

## Start with the symptom

- Define the metric: latency, throughput, alloc count, heap size, CPU time, lock wait, or tail latency
- Reproduce the issue with a stable workload before changing code
- Prefer release-mode measurements unless debug behavior is the actual problem

## Benchmark hygiene

- Use Criterion for stable benchmark comparisons and statistics
- Use `black_box` around benchmark inputs to avoid dead-code elimination
- Compare before vs after under the same environment
- Run enough iterations to smooth noise; do not trust a single lucky run

## Release-profile basics

- Measure optimized code with `cargo bench` or `cargo run --release`
- Tune release settings only after confirming they matter for the workload
- Record what changed so future regressions have a baseline to compare against
