---
name: sharphound
description: "Auth/lab ref: Collect Active Directory data with SharpHound CE for import into BloodHound CE."
license: GPL-3.0
compatibility: "Windows; .NET Framework 4.7.2; use the SharpHound version compatible with the BloodHound CE instance."
metadata:
  author: AeonDave
  version: "2.0"
---

# SharpHound CE

Obtain the compatible collector from BloodHound CE's **Download Collectors** or check the deployed instance's compatibility against [SharpHound releases](https://github.com/SpecterOps/SharpHound/releases). Run in the context of a domain user with approved collection scope. On a domain-joined Windows system:

```powershell
.\SharpHound.exe
.\SharpHound.exe -c DCOnly -d example.test --outputdirectory C:\Collected
```

The first command uses the default collection, which queries the domain and attempts local group and session collection from domain-joined computers. `DCOnly` collects domain-controller data and omits direct member-computer collection. Consult `SharpHound.exe --help` and the [official flags](https://bloodhound.specterops.io/collect-data/ce-collection/sharphound-flags) for the installed version. Output defaults to a ZIP containing JSON; import it in BloodHound CE and verify ingestion.

Load [references/bloodhound-collection-strategy.md](references/bloodhound-collection-strategy.md) when choosing coverage or interpreting missing data. Preserve collection time, methods, scope and errors with the results.
