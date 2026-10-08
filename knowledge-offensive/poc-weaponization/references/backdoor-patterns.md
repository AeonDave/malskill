# PoC Review Indicators

**Load when**: Performing static review of a third-party PoC artifact or its build and dependency files.

Trace behavior and record file paths or symbols as evidence. Indicators trigger closer review; they do not prove malicious intent by themselves.

## Source and build chain

- Compare the artifact with the claimed upstream revision and release. Note forks, unexplained changes, generated files, submodules, or downloaded binaries that are absent from the reviewed source.
- Inspect manifests, lockfiles, install/build hooks, shell scripts, containers, and CI workflows for undeclared downloads, mutable dependency sources, commands that run during setup, or access to secrets and tokens.
- Check encoded or dynamically assembled content, reflection, dynamic imports/loading, and indirect command execution. Determine what is decoded or invoked from the data flow before classifying it.

## Runtime behavior

- Trace network destinations, DNS lookups, callbacks, and outbound data. Compare each with the stated assessment purpose and the declared test environment; unexplained third-party destinations or data transfer require investigation.
- Identify reads of credential stores, environment secrets, browser profiles, SSH keys, cloud credentials, and unrelated user files. Record the code path and whether the data is transmitted, logged, or retained.
- Identify writes, deletion, service/task changes, startup hooks, privilege changes, and process injection. Decide whether each is necessary for the stated test and whether it can change the reviewed host or target.
- Follow error handlers and cleanup paths. A benign-looking primary path can conceal side effects on failures, retries, or particular platform/version branches.

## Evidence and limits

- Review dependency and build behavior without installing or invoking it. A package name or declared version does not prove which code would be fetched; record registry/source and pinning evidence when available.
- Treat an unexplained callback or sensitive-data access as a finding to explain, not a reason to run the artifact and observe what it does.
- Hashes identify the reviewed bytes. Signatures and provenance can support origin and build claims when their trust roots and statements are verified; neither demonstrates that the artifact's behavior is benign.
- State static-review coverage explicitly. Dynamic loading, opaque binaries, environment-specific branches, and unobserved dependencies can leave behavior unresolved.
