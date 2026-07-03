# SDLS, SDLS-EP, and Ground-Segment CVEs

Load when a link is authenticated/encrypted at the data-link layer (SDLS), when key/SA management directives (SDLS-EP) are in play, or when the target is a mission-control server (Yamcs, OpenC3 COSMOS, NASA cFS) rather than the RF link. Pair with `ccsds-frame-construction.md` for where SDLS bytes sit in the frame and with `cop1-and-pus.md` for the COP-1 gaps SDLS deliberately does not cover.

## Contents

- SDLS packet layout (355.0-B)
- Baseline crypto (352.0-B, GCM/CMAC)
- What SDLS does not protect (attacker still-has)
- SDLS Extended Procedures (SDLS-EP, 355.1-B)
- CryptoLib CVEs (2025)
- NASA cFS Aquila CVEs (2025–2026)
- OpenC3 COSMOS CVEs (2025)
- Yamcs / Kubos notes
- Kill-chain patterns

## SDLS packet layout (CCSDS 355.0-B)

Applied to the **Transfer Frame Data Field** of TC / TM / AOS / USLP frames. The primary frame header stays plaintext (SCID, VCID, N(S), FECF still visible).

```
+------------------+------------------------------+------------------+
| Security Header  |   (Encrypted) Data Field     | Security Trailer |
+------------------+------------------------------+------------------+
| SPI (16)         |   application data           | MAC (n)          |
| IV (0..192)      |                              |                  |
| Seq Num ARSN (0..64) |                          |                  |
| Pad Length (0..8)|                              |                  |
+------------------+------------------------------+------------------+
```

- **SPI** — Security Parameter Index → selects the **Security Association (SA)** (key, algorithm, mode, ARSN state).
- **IV** — required by GCM/CTR; length per SA.
- **ARSN** — Anti-Replay Sequence Number (Seq Num field). Receiver drops if `ARSN <= last_seen`.
- **MAC** — CMAC or GCM tag over the authenticated span (header + encrypted data field per the SA).
- **Pad Length** — bytes of fill padding at end of data field (block-mode ciphers).

Three services per SA: **authentication-only**, **encryption-only**, **authenticated-encryption**. A `clear-mode` service is standardized but is a no-op — header present, no crypto. Look for it in mission configs; it is a common misconfiguration.

## Baseline crypto (CCSDS 352.0-B-2)

- **AES-256** in **GCM** for authenticated encryption (baseline; some missions use AES-128).
- IV = 96-bit; MAC = 128-bit; padding never needed in GCM.
- **CMAC (AES)** for authentication-only.
- SDLS itself is agile — the SA carries algorithm/mode/key-length. Attack surface: SA table corruption, algorithm downgrade, IV reuse (see below), key-material exposure.

## What SDLS does NOT protect (CTF-relevant gaps)

Even a fully-enabled SDLS deployment leaves these open:

- **TC COP control commands** (BC frames: Unlock, Set V(R)) — not covered. Attacker can still cause FARM lockout or force retransmit.
- **CLCW in the TM OCF** — not covered. Attacker can flip `Retransmit`/`Lockout` bits to interfere.
- **VC_OCF, VCF, MC_FSH, MC_OCF, MCF services** — no encryption/authentication under SDLS.
- **Encryption-only mode** (no MAC) — no defense against modification of ciphertext.
- **`clear-mode` VCs** — data-link-layer security effectively off.
- **IV reuse** across frames on the same SA → **keystream oracle** (see CryptoLib CVE-2025-46672).

## SDLS Extended Procedures (SDLS-EP, CCSDS 355.1-B)

Adds three in-band services (transported as SDLS-EP PDUs inside protected frames):

- **KMS** — Key Management: **OTAR** (Over-The-Air Rekey) uploads new session keys wrapped with a master key.
- **SAMS** — Security Association Management: create/delete/modify SAs on-board.
- **MCS** — Monitoring & Control: query key inventory, dump security event log, set ARSN.

Standard-defined reserved SPIs for EP PDUs (mission-specific but conventionally):
- **SPI 1** and **SPI 65535** (`0xFFFF`) — dedicated EP command/report channels.
- **SA 0** and **SA (NUM_SA − 1)** — reserved SA slots per spec principle of defense-in-depth.

EP PDU verbs to know:
- **OTAR** — upload session keys.
- **Key Activation / Deactivation / Delete** — rotate active key by ID.
- **Key Verification** — challenge/response to prove key knowledge (crypto method is out of scope of the EP spec — implementation-defined).
- **Set ARSN Command** — force the anti-replay counter.
- **Dump Log Reply** — leaks security events; sensitive if unprotected.

Rule (from the spec): *All EP PDUs must be sent over an SDLS channel with at least authentication (preferably authenticated-encryption) — the whole point is to prevent unauthorized directives.*

## CryptoLib CVEs (NASA reference SDLS implementation, 2025)

Confirmed vulnerabilities from independent review of NASA's open-source `crypto_lib`. Useful both as CTF challenge material and as bug patterns to recognize in mission-specific ports.

### CVE-2025-46672 — Keystream Oracle (IV reuse)

CryptoLib's IV allocation lets a legitimately-issued sender reuse an IV across frames on the same SA. Two ciphertexts under the same (key, IV) leak XOR of plaintexts → **keystream oracle**. Practical impact: recover plaintext of one frame from another, forge frames if MAC keying is separate. Fix in PR365 pre-allocates a shared IV pool.

Attacker check: capture multiple encrypted TC/TM frames on the same VC/SA and inspect the IV in the Security Header — same IV across frames = exploitable.

### CVE-2025-46675 — Spacecraft Hijack via EP Channel Confusion

CryptoLib detects an SDLS-EP PDU by matching **either a configured VCID or a configured APID** in the Space Packet header, rather than the spec-mandated **dedicated SPI 1 / SPI 65535** channels. Any attacker who can land bytes on a VC/APID that CryptoLib maps to EP can now:

1. **Erase existing Security Associations** (SAMS delete).
2. **OTAR upload attacker-controlled keys** (KMS OTAR).
3. Take exclusive control of the spacecraft; deny access to the legitimate operator.

Fix: enforce reserved SPI check on EP PDU entry, plus key-state validation before use (PRs 358–360).

### Related — no CVE, spec-level trap

SDLS is silent on how OTAR wraps master keys; a mission that keys OTAR-wrap with an **HMAC-derived** rather than an authenticated-cipher construction may be forgeable. Check the mission-specific config in the ADD before trusting the wrap.

## NASA cFS Aquila (2019 baseline) — CVEs 2025–2026

VisionSpace (Starcik/Olchawa/Fradique/Boulaich) chain from unauthenticated TC to RCE against the OSAL / MM / SB layers.

| CVE | CVSS | Component | Mechanism |
|-----|------|-----------|-----------|
| **CVE-2025-25373** | 9.8 Critical | Memory Management (MM) module | Insecure permissions → **RCE** on the platform via crafted MM commands |
| **CVE-2025-25371** | 7.5 High | OSAL | Path traversal → overwrite arbitrary files |
| **CVE-2025-25372** | 7.5 High | MM module | Segfault via malicious TC |
| **CVE-2025-25374** | 7.5 High | App loader | Force platform into a state that blocks all future app launches → DoS |
| **CVE-2026-5475** | 5.5 Medium | Software Bus, `CFE_SB_TransmitMsg` in `cfe_sb_priv.c` | CCSDS header size handler missing bounds check → memory corruption. cFS ≤ 7.0.0. Adjacent-network attack vector |
| **CVE-2026-5476** | 4.6 Medium | Pickle module | Unsafe `pickle.load` → deserialization (local, high complexity) |

Typical delivery: TC space packets with an APID mapped to a target cFS app (MM, table services, etc.). The Software Bus is a shared message broker — one poisoned message reaches every subscriber. Watch for the `cf`/`cfdp`/`mm`/`fm` app namespaces in a target's mission config.

Common lab environment: **NOS3** bundles cFS + COSMOS + Yamcs as a full satellite simulator — a single-container attack surface for practice.

## OpenC3 COSMOS CVEs (2025)

### GHSA-w757-4qv9-mghp — **Unauthenticated RCE** via JSON-RPC (5.0.6 – 6.10.1; patched 6.10.2)

- The JSON-RPC API accepts string-form APIs (e.g. `cmd`); parameters are parsed with `String#convert_to_value`. For **array-like inputs**, `convert_to_value` calls **`eval()`** on attacker-controlled Ruby.
- The `cmd` code path parses the payload **before** `authorize()` — so even though the request eventually returns **401**, the Ruby is already executed.
- Impact: arbitrary Ruby code execution in the COSMOS process (network-reachable, no auth). CVSS 10.0.
- PoC shape (send to `POST /openc3-api/api`):
  ```json
  {"jsonrpc":"2.0","method":"cmd","params":["[Kernel.system('id')]"],"id":1}
  ```
- Fix: upgrade to **≥ 6.10.2**.

### Seven-CVE batch (v6.0.0, VisionSpace 2025)

| Class | Detail |
|-------|--------|
| **Plugin RCE** | Plugin install runs `setup.py` — a malicious plugin gets code execution on install (`gem install`/`pip install`-style). |
| **XSS** | Reflected/stored in multiple web tools (Script Runner, Command/Telemetry sender). |
| **Path traversal** | Arbitrary file access via multiple API endpoints. |
| **Credential leakage** | Passwords surface in container env vars (default `OPENC3_REDIS_PASSWORD=openc3password`, `OPENC3_SR_REDIS_PASSWORD=scriptrunnerpassword`, `OPENC3_SERVICE_PASSWORD=openc3service`). |
| **Insecure authentication** | Plaintext passwords; undocumented service accounts. |

### Default-config footprints to check

- Binds `127.0.0.1` only by default; production deployments often expose on all interfaces.
- Redis backend on default creds unless overridden.
- Backend service account `OPENC3_SERVICE_PASSWORD=openc3service` bypasses front-end user auth for internal APIs.

## Yamcs / Kubos notes

- **Yamcs** — VisionSpace 2023–2025 disclosures: **path traversal + XSS** in the web tool. Inspect the **Mission Database (MDB)** for command/parameter definitions the attacker can enumerate before crafting a TC.
- **Kubos** — CubeSat mission-planning framework. Historic Hack-A-Sat challenges (SpaceDB) leaned on **over-the-space update flows** whose "authenticating checksum" turned out to be a well-known algorithm (CRC or fixed key XOR) — always try trivial checksums first before assuming HMAC.

## Kill-chain patterns (recognize in a challenge)

- **Radio-settings scrape → cross-team TC** (HAS 2022 Finals '403 Denied'): compromise the ground-station DB via a webserver bug, exfil radio config (freq/coding/keys), then send commands to another team's satellite.
- **Auth-checksum bypass on config commands**: challenge asks for a "signature" on an ADCS pointing command; the algorithm is a fixed function of the payload with no key. Reverse the client, don't brute the space.
- **CLCW / COP-1 attack while SDLS is on**: SDLS does not cover BC directives or CLCW → send BC Unlock/Set V(R) or flip CLCW Retransmit to disrupt without breaking crypto.
- **EP-channel confusion (CryptoLib CVE-2025-46675)**: if the target uses CryptoLib, forge EP PDUs on an APID/VCID the parser maps to EP rather than the reserved SPI — erase SAs, OTAR your own key, own the bird.
- **cFS MM command RCE (CVE-2025-25373)**: TC into the MM module writes to arbitrary memory → drop a payload / redirect a function pointer.
- **COSMOS JSON-RPC RCE (GHSA-w757-4qv9-mghp)**: land Ruby via array-form `cmd` params before auth runs.
- **cFS + MDB + COSMOS chain (NOS3-style lab)**: use COSMOS to enumerate the MDB, pick an APID mapped to a vulnerable cFS app, deliver the exploit through the standard TC path — no RF needed.

## Sources

- SDLS Blue Book — CCSDS 355.0-B-2, <https://ccsds.org/Pubs/355x0b2.pdf>
- SDLS-EP Green Book — CCSDS 350.11-G-1, <https://ccsds.org/Pubs/350x11g1e1.pdf>
- CryptoLib CVE analysis — <https://securitybynature.fr/post/hacking-cryptolib>
- NASA cFS CVE research (VisionSpace) — <https://andy.codes/blog/security-articles/2025-03-29-nasa-cfs-vulnerability-research.html>
- OpenC3 CVE research (VisionSpace) — <https://andy.codes/blog/security-articles/2025-05-28-openc3-vulnerability-research.html>
- OpenC3 GHSA-w757-4qv9-mghp — <https://github.com/OpenC3/cosmos/security/advisories/GHSA-w757-4qv9-mghp>
- OpenC3 default security — <https://docs.openc3.com/docs/getting-started/security>
- Hack-A-Sat 2022 Finals recap — <https://www.cromulence.com/blog/hack-a-sat-2022-finals-teams-on-the-attack>
