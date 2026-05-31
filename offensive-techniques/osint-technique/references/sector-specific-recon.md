# Sector-Specific Recon — Healthcare, Finance, ICS, IoT, Gov, Maritime/Aviation/Auto

Most recon generalizes; some sectors expose unique protocols/vendors worth flagging. **Universal caveat:** OSINT methodology is identical — only the targeted services differ.

---

## Healthcare

- **DICOM** (medical imaging) — port `11112`, sometimes `4242` (testing).
- **HL7 v2** (clinical messaging) — port `2575/tcp`, often plaintext.
- **HL7 FHIR** (modern REST) — `/fhir/R4/<resource>` paths; OAuth / SMART-on-FHIR posture varies.
- **PACS / RIS / EHR vendors:** Epic (`*.epic.com` SaaS), Cerner/Oracle Health, Allscripts/Veradigm, Athenahealth, NextGen, Meditech, eClinicalWorks. Each has known CVE history.
- **Dorks:** `site:{domain} ("EHR" OR "PACS" OR "PHI" OR "HIPAA")`, `intitle:"Epic Systems" "{target}"`.
- **Severity:** any PHI exposure → CRITICAL (regulatory + reputational); HL7/DICOM open without auth → CRITICAL.

## Finance

- **SWIFT terminals** — typically internal-only; external-facing → CRITICAL. Look for SWIFT Alliance Web Platform.
- **FIX protocol** (electronic trading) — port `9876` (common), cleartext.
- **Bloomberg terminals** — typically VDI; check `bloomberg.com`-related auth surfaces.
- **Trading vendors:** Fidessa, Charles River, Eze Software, Aladdin (BlackRock).
- **Core banking middleware:** Temenos T24, Finacle (Infosys), FIS, Jack Henry, Fiserv. Each has known CVE history.
- **Dorks:** `site:{domain} ("PCI" OR "SOX" OR "GLBA" OR "MAS")`, `intitle:"Temenos" "{target}"`.
- **Severity:** account/balance exposure → CRITICAL; SWIFT exposure → CRITICAL; trade-execution surface → CRITICAL.

## ICS / SCADA / OT

> **Caution:** ICS/SCADA assets often run on legacy systems where even passive probing can disrupt operations. **Do NOT actively probe without explicit RoE coverage and OT-team coordination.**

| Protocol | Port | Notes |
|---|---|---|
| Modbus | `502/tcp` | Read coils/regs unauth common |
| BACnet | `47808/udp` | Building automation; point list often readable |
| Siemens S7 | `102/tcp` | ISO-TSAP |
| DNP3 | `20000/tcp` | Energy/utility |
| EtherNet/IP | `44818/tcp` | Allen-Bradley / Rockwell |
| Niagara | `1911`, `4911`, `5011`, `502` | Tridium framework |

- **HMI vendors:** Honeywell EBI, GE Proficy/iFIX, Wonderware, Schneider EcoStruxure.
- **Common findings:** unauth BACnet point list, Modbus register read, default HMI creds, public-facing engineering workstations.
- **Sources:** Shodan (`port:502`, `tag:ics`), Censys, Onyphe.
- **Detectability:** medium-to-high; ICS networks have low background traffic + heavy monitoring.
- **OSINT scope:** stop at passive discovery (Shodan/Censys/Onyphe banner queries, public vendor portals, procurement records). Active protocol probing is OT/red-team scope, not OSINT.

## IoT / Consumer / SOHO

- **MQTT** — `1883/tcp` (cleartext), `8883/tcp` (TLS). Topics often readable without auth.
- **CoAP** — `5683/udp`.
- **UPnP / SSDP** — `1900/udp`; discloses internal device map.
- **Router admin patterns:** `/cgi-bin/`, `/setup.cgi`, `/admin/index.html`. Default creds the norm.
- **Camera DVRs/NVRs:** Hikvision, Dahua, Axis — multiple CVEs.
- **Smart-home hubs:** exposed APIs sometimes leak auth tokens.

## Government

- **`.gov` / `.mil`** require special scope discipline.
- **FedRAMP / FISMA / DoD CMMC** — defensive posture above commercial baseline.
- **Sources:** USAspending.gov, SAM.gov (System for Award Management), procurement records.
- **Findings:** vendor of record disclosed in public contracts → adjacent-vendor pivot.
- **Severity:** as high or higher than commercial; political sensitivity layered on technical impact.

## Maritime / Aviation / Automotive

- **Maritime:** AIS (Automatic Identification System) — vessel positions; MarineTraffic, VesselFinder. Engine telemetry sometimes exposed via VSAT.
- **Aviation:** ADS-B (see [image-and-geospatial-osint.md](image-and-geospatial-osint.md)); operator/airline OPS data sometimes exposed.
- **Automotive:** OEM telematics backends (Tesla, GM OnStar, etc.) — typically authenticated, but APIs leak via mobile-app RE.

## Universal caveat

Most external recon techniques apply universally. Sector-specific protocols **add** attack surface; sector compliance regimes add reporting requirements. Don't assume "healthcare/finance OSINT is different" — the OSINT is identical; the targeted services differ.
