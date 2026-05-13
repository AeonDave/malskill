# Roots

Load this file when the client provides workspace or path scope.

## What roots are

Roots are client-provided URIs that tell the server where the relevant working area is.

They are best understood as **scope hints** or **focus boundaries**, not as proof that every path under them is authorized forever.

## When to use roots

- file-oriented local servers
- workspace analysis tools
- project-scoped search/read flows
- multi-root scenarios where the host already knows the relevant directories

## Design rules

- check whether the client actually declared roots support
- prefer operating inside the provided roots instead of scanning the whole machine
- normalize and validate paths before using them
- pick the nearest relevant root instead of combining unrelated roots blindly

## Good patterns

- search only inside the selected workspace root
- read files relative to a root-aware base path
- reflect root choices back in logs or result summaries when helpful

## What roots are not

- not a replacement for host approvals
- not a permanent ACL system by themselves
- not a reason to skip path validation or least-privilege design

## Common mistakes

- assuming roots are always available
- ignoring roots and scanning everywhere anyway
- treating roots as trusted absolute authorization rather than host-supplied scope
- mixing root-relative and machine-global paths without clarity

Treat roots as useful focus boundaries, not as magical trust objects.

