# Artifacts, Redaction, and Packaging

Load when deciding what to publish, what to sanitize, and how to package a reproducible writeup.

## What to include

Prefer a small artifact set that proves the solve:

- final solver script or minimal helper script
- sample input or challenge data needed to run it
- exact command line or run instructions
- decisive output snippet
- hashes or filenames when multiple artifacts exist

## What to redact

Redact secrets that are not needed to understand the solve:

- live tokens, cookies, session IDs, API keys
- third-party target identifiers
- external endpoints unrelated to the challenge proof
- personal paths or workstation-specific data

Redaction rule: preserve structure, remove risk.

## Screenshots vs raw artifacts

Use screenshots only when the image adds context that text cannot:

- GUI-only state change
- waveform or spectrum visualization
- graph or timeline that matters to the solve

Do not rely on screenshots for:

- raw HTTP requests
- commands
- solver code
- exact outputs that can be copied as text

Use code blocks or attached scripts for those.

## Packaging checklist

Before finishing, check that the package contains:

- one clear writeup file
- one minimal runnable solver when code is needed
- dependencies or version notes only when they affect reproduction
- sanitized artifact names and paths
- expected success signal in the writeup

## Common pitfalls

- publishing a helper script without run instructions
- sanitizing so aggressively that the proof no longer reproduces
- including huge raw logs instead of the decisive excerpts
- dumping all screenshots without captions or context
- packaging challenge artifacts but forgetting to name which one the solver consumes
