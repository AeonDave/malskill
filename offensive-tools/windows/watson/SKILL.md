---
name: watson
description: "Interpret Watson's legacy Windows missing-patch checks for reproducible older-build labs. Use current patch inventories for newer systems."
license: BSD-3-Clause
compatibility: "Legacy .NET Windows tool; upstream lists Windows 10 1507–2004 and Server 2016/2019."
metadata:
  author: AeonDave
  version: "1.2"
---

# Watson

Use only when reproducing a build covered by its fixed checks. [Upstream](https://github.com/rasta-mouse/Watson) was archived in September 2021; it is not a current vulnerability feed.

```powershell
.\Watson.exe > watson-output.txt
```

1. Record the OS edition, build, architecture, and Watson source revision.
2. Check that the build and CVE are present in that revision's code. Unsupported builds are **not assessed**.
3. Treat `VULNERABLE` as a patch-based candidate. Verify the affected component and superseding cumulative updates against the vendor advisory.
4. Preserve the output and applicability conclusion. A missing KB identifier alone does not establish vulnerability.

For newer systems, use an updated patch-inventory workflow such as [WES-NG](https://github.com/bitsadmin/wesng) and verify its suggestions against [Microsoft's update guide](https://msrc.microsoft.com/update-guide). Configuration checks belong in [PrivescCheck](../privesccheck/SKILL.md).
