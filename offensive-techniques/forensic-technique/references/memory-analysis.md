# Memory analysis workflow

## Purpose

Use memory evidence to reconstruct active execution state and detect fileless or injected behavior.

## 1) Start with process reality

- Enumerate process list and parent-child trees.
- Validate suspicious parentage, duplicate system process names, odd command lines.

## 2) Map runtime behavior

- Active sockets and remote peers.
- Loaded modules and unsigned/unexpected regions.
- Handles and in-memory objects tied to suspicious processes.

## 3) Injection and evasion checks

- RWX or execute-write memory regions.
- Hollowing-like or remapped executable regions.
- Hidden/unlinked process or module artifacts.

## 4) Extraction strategy

- Dump only processes/regions tied to hypotheses.
- Preserve extraction metadata (offsets, plugin/tool versions, timestamps).
- Re-hash dumped artifacts before static follow-up.

## 5) Cross-source validation

- Match suspicious process execution to disk traces.
- Match sockets/domains to PCAP sessions.
- Treat unmatched memory-only findings as transient until corroborated.

## 6) Output

- Suspect process map (process, parent, command line, reason).
- Network correlation list (process-to-session mapping).
- Extracted artifact list with integrity data and follow-up status.
