---
name: powerview
description: "Use PowerView's PowerShell functions for AD object, group, trust, and ACL inspection. Resolve command-version differences before querying."
license: BSD-3-Clause
compatibility: "Windows PowerShell; use the requirements of the selected PowerSploit revision."
metadata:
  author: AeonDave
  version: "1.1"
---

# PowerView

Keep the script revision with the results. [PowerSploit](https://github.com/PowerShellMafia/PowerSploit) is archived; this skill covers its PowerShell implementation. Python projects such as [powerview.py](https://github.com/aniqfakhrul/powerview.py) and [pywerview](https://github.com/the-useless-one/pywerview) have separate interfaces and dependencies.

## Query workflow

1. Load a reviewed local copy and inspect the functions actually available.
2. Query a specific object or filter, requesting only the properties needed.
3. Preserve raw objects until selecting an export shape. Formatting commands produce display objects unsuitable for further analysis.
4. Record the queried domain/controller and identity. Access failures and missing attributes are not proof that an object or relationship does not exist.

```powershell
. .\PowerView.ps1
Get-Command Get-Domain* -CommandType Function
Get-Help Get-DomainUser -Full

Get-Domain
Get-DomainUser -Identity audit-user -Properties samaccountname,distinguishedname
Get-DomainGroupMember -Identity 'Audit Readers'
```

## Version and interpretation traps

- The archived source uses `Get-Domain*` names and supplies some `Get-Net*` aliases. An alias does not guarantee that an old example's parameters still exist.
- Check `Get-Help` for the loaded function before using filters, credentials, controller selection, or recursion options.
- Direct membership, nested membership, and effective authorization are different results. State which was queried.
- An ACL entry is evidence to interpret with object type, inheritance, and effective rights; it is not an automatically viable attack path.
- Retain this tool when its PowerShell object pipeline fits the task. Do not assume a Python port is a drop-in replacement.

Source: [PowerView source and embedded help](https://github.com/PowerShellMafia/PowerSploit/blob/master/Recon/PowerView.ps1). For graph analysis, load [BloodHound](../bloodhound/SKILL.md).
