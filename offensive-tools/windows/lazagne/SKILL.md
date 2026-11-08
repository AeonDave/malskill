---
name: lazagne
description: "Assess LaZagne module compatibility and interpret local application secret-exposure results, including incomplete or unsupported recovery."
license: MIT
compatibility: "Windows, Linux, and macOS implementations have different module coverage; match the release and execution identity."
metadata:
  author: AeonDave
  version: "1.1"
---

# LaZagne

Use the selected release's module list and help. The presence of an application in the support table does not establish support for every version or protection scheme.

```cmd
lazagne.exe -h
lazagne.exe browsers -h
```

## Result review

- Record the tool revision, OS, application version, and user context with each result.
- Distinguish a missing artifact, access failure, unsupported format, decryption error, and recovered value. Empty output is not proof that no stored secrets exist.
- Output-format switches and output paths are separate concepts; inspect the release's help before building automation. Quiet output can hide useful diagnostics.
- Treat exported results as sensitive evidence. Reports should identify the affected application and remediation without repeating recovered values.
- Chrome 127 introduced App-Bound protection for **cookies on Windows**. That announcement does not establish universal password coverage, Edge behavior, or support by LaZagne; verify the specific application and module.
- Use native package/runtime instructions. A Python source file cannot be executed as PowerShell with `Invoke-Expression`.

Sources: [upstream usage and coverage](https://github.com/AlessandroZ/LaZagne), [v2.4.7 release](https://github.com/AlessandroZ/LaZagne/releases/tag/v2.4.7), [Chrome 127 changes](https://support.google.com/chrome/a/answer/10314655).
