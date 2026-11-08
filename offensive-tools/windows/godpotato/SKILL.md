---
name: godpotato
description: "Assess GodPotato build compatibility and interpret existing local privilege-escalation test results without assuming universal Windows support."
license: MIT
compatibility: "Upstream lists Windows 8–11 and Server 2012–2022; use the executable variant matching the installed .NET runtime."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-tools
---

# GodPotato

Qualify the exact build and process context. The [upstream release V1.20](https://github.com/BeichenDream/GodPotato/releases/tag/V1.20) is not evidence of support for every later Windows build.

## Check and interpret

- Record OS build, architecture, .NET runtime, executable hash, and source revision.
- Verify the current process token and effective privileges; a service-account name alone does not establish them. Upstream identifies `SeImpersonatePrivilege` as a prerequisite.
- Match the NET2/NET35/NET4 artifact to its runtime. Do not equate NET4 with a universal .NET 4.8 requirement.
- Separate runtime startup errors, token/privilege failures, RPC failures, process-creation failures, and the resulting process identity.
- Verify the observed result instead of inferring success from tool startup or a generic success message.
- Do not infer Server 2025 support, automatic per-build selection, or a universal replacement for other tools from the README's broad OS range.
- This is a local privilege-escalation tool, not a UAC bypass. Do not use those labels interchangeably.

Source: [GodPotato documentation and source](https://github.com/BeichenDream/GodPotato).
