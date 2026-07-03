# MQTT, Mosquitto, IoT, and PLC bridges in ICS/OT CTFs

Reference pack covering MQTT specifically as an ICS/IoT pivot surface. Use after the SKILL.md quick pivot for MQTT once a broker, Sparkplug payload, IoT gateway, or MQTT-to-PLC bridge appears. Authorized labs only.

## 1. Why MQTT shows up in OT scope

MQTT 3.1.1 and 5.0 are the de-facto messaging fabric for IIoT, smart-building, and modern SCADA edge layers. In ICS CTFs and real plants you typically see:

- **Edge sensors / actuators** publishing temperature, level, flow, vibration, door, relay state on per-device topics (`site/area/cell/<id>/<metric>`).
- **MQTT-to-Modbus / S7 / OPC UA gateways** (Advantech WISE, HMS Anybus, Moxa MGate, Red Lion FlexEdge, EMQX Neuron, Cirrus Link MQTT Modules) translating between PLC tags and broker topics in both directions.
- **Sparkplug B** payloads from Ignition (Inductive Automation) edge nodes — a structured MQTT profile that turns the broker into a real-time SCADA bus.
- **Smart-building / HA stacks** (Home Assistant, openHAB, Node-RED, Tasmota, Shelly, Sonoff) bridging consumer IoT into the same VLAN as building-management PLCs.
- **Telemetry brokers** (Mosquitto, HiveMQ, EMQX, VerneMQ, NanoMQ, AWS IoT, Azure IoT Hub) on 1883/8883/9001 (WebSocket) often left wide open.

A read on `#` plus `$SYS/#` is usually enough to map the whole plant; a single write to the right command topic can drive a real actuator. Treat command topics the same way as a Modbus FC 6 — never write unless the lab is explicitly isolated and the objective demands it.

## 2. Broker triage workflow

Order of operations on any newly discovered broker:

1. **Port + transport**: 1883 (plain), 8883 (TLS), 8080/9001 (WS / WSS). Probe with `nmap -p1883,8883,8080,9001 --script mqtt-subscribe`.
2. **Fingerprint**: `mosquitto_sub -h <ip> -t '$SYS/#' -v -W 5` → reveals broker family (`Mosquitto`, `HiveMQ`, `EMQX`, `VerneMQ`), version, uptime, client count, retained-message count, subscription count.
3. **Anonymous read**: `mosquitto_sub -h <ip> -t '#' -v -W 30 -q 1 | tee mqtt.dump`. If allowed, the broker hands you the entire process bus.
4. **Retained snapshot**: `mosquitto_sub -h <ip> -t '#' -v -W 2 -R` (skip retained) vs without `-R` — the diff is the persistent state (last known sensor reading, last command, device birth certificates).
5. **Will / LWT inspection**: subscribe before disconnecting a publisher; the broker pushes the Last Will payload — often a useful failure-state oracle (`offline`, `error`, JSON with PLC tag dump).
6. **ACL probe**: try publishing a benign retained message to `_probe/<rand>` and subscribing back; if accepted, ACL is open or default. Always clear with empty retained payload (`-r -m ''`).
7. **Auth probe**: `mosquitto_sub -h <ip> -t '#' -u admin -P admin -v -W 2`; iterate small vendor-default list (`admin/admin`, `mqtt/mqtt`, `homeassistant/homeassistant`, `ignition/password`). Escalate to `mqtt-pwn bruteforce` with controlled wordlist if scope allows.
8. **Persist + analyze offline**: convert `-v` dump to JSONL and grep for credentials, tag names, setpoints, alarm strings, and JWT/Base64 blobs.

`$SYS/#` keys worth grabbing first:

- `$SYS/broker/version`, `$SYS/broker/uptime`
- `$SYS/broker/clients/connected`, `$SYS/broker/clients/total`
- `$SYS/broker/subscriptions/count`
- `$SYS/broker/retained messages/count`
- `$SYS/broker/messages/{sent,received}`
- `$SYS/broker/bytes/{sent,received}` — sanity-check whether you're seeing all traffic
- HiveMQ-specific: `$SYS/broker/load/...`
- EMQX-specific: `$SYS/brokers/<node>/stats/...`, `$SYS/brokers/<node>/metrics/...`

## 3. Sparkplug B — MQTT as a SCADA bus

Sparkplug B (Eclipse Foundation spec, used by Ignition / Cirrus Link / AVEVA / many DCS edge stacks) is the most important MQTT profile for OT work. Topic namespace is fixed:

```
spBv1.0/<group_id>/<message_type>/<edge_node_id>[/<device_id>]
```

Message types:

| Type   | Direction      | Meaning                                                                 |
|--------|----------------|-------------------------------------------------------------------------|
| NBIRTH | edge → host    | Edge node birth: full metric list with aliases, types, initial values   |
| NDEATH | edge → host    | LWT — edge node lost                                                    |
| NDATA  | edge → host    | Metric updates (delta) by alias                                         |
| NCMD   | host → edge    | Command to edge node (rebirth, reboot, write to metric)                 |
| DBIRTH | edge → host    | Device birth under that edge node                                       |
| DDEATH | edge → host    | Device lost                                                             |
| DDATA  | edge → host    | Device metric updates                                                   |
| DCMD   | host → device  | Write to device metric (this is the actuator-write equivalent)          |
| STATE  | host ↔ broker  | Host application primary state                                          |

Operational facts that matter for CTFs:

- Payloads are **Protobuf** (`org.eclipse.tahu.protobuf.Payload`). Decode with the official `sparkplug_b.proto` or the Python `tahu` / `pysparkplug` packages.
- **Aliases** in NBIRTH/DBIRTH map integer alias → metric name + type. Subsequent NDATA/DDATA only carry the alias, so without the BIRTH you cannot resolve tag names. If you join late, send a `Node Control/Rebirth` boolean = true via NCMD to force a fresh BIRTH — but that's a *write* and an obvious audit event.
- The **Primary Host** field gates whether edge nodes accept commands; spoofing it lets you drive DCMDs against real devices.
- Sparkplug strongly recommends **TLS + per-edge-node credentials**; in practice many deployments still run plain 1883 with shared username.
- A DCMD payload writing to `Outputs/Pump1_Run` is functionally identical to a Modbus FC 5 coil write — same safety implications.

References for the spec and tooling:

- Spec PDF and JSON: <https://sparkplug.eclipse.org/specification/>
- Eclipse Tahu reference impls (Java/Python/C/.NET/JS): <https://github.com/eclipse-tahu/tahu>
- Cirrus Link MQTT Distributor / Engine / Transmission modules for Ignition: <https://docs.chariot.io/display/CLD/>

## 4. Mosquitto-specific notes

Mosquitto is the most common broker in CTF and SMB IoT deployments. Defaults and gotchas:

- Default config historically allowed **anonymous connections** until 2.0; many distros and homelab images still ship `allow_anonymous true`.
- ACL file format is simple and frequently misconfigured: `topic readwrite #` for a single user effectively turns auth into a speed bump.
- `mosquitto_passwd` stores PBKDF2 hashes; if you pull `passwd` and `mosquitto.conf` from a host (e.g. via LFI or SMB share), they are crackable with `hashcat -m 14400` (mode varies — confirm Mosquitto version: 1.x uses `mosquitto1.0` SHA512+salt; 2.x uses PBKDF2-SHA512).
- `mosquitto.conf` keys to grep: `password_file`, `acl_file`, `bridge_*` (broker-to-broker bridges leak data across networks), `psk_file` (PSK auth, rare).
- Bridges are powerful: a `bridge_topic in 2 plant/#` directive on a poorly-configured bridge can pull a remote broker's process data into yours and vice versa — a classic data-flow lateral-movement path.
- Plugin auth (`auth_plugin`) is sometimes wired into Postgres / MySQL / HTTP backends — SQLi or unauth API on the backend == broker auth bypass.
- `$SYS` topics on Mosquitto are emitted by default; disabling requires `sys_interval 0`.
- Known CVEs worth searching against the version string from `$SYS/broker/version`: CVE-2017-7650 (pattern ACL bypass), CVE-2018-12546 / 12550 / 12551 (ACL + persistence bugs), CVE-2021-28166 (will message DoS), CVE-2023-0809 / 3592 (large packet handling), CVE-2024-3935 (TLS handshake DoS), and version-specific advisories at <https://mosquitto.org/security/>. Pin findings to the exact version banner — Mosquitto is widely backported.

## 5. EMQX, HiveMQ, VerneMQ, NanoMQ

- **EMQX**: dashboard on 18083 default `admin/public`; **Rule Engine** can forward MQTT → Kafka, HTTP, Modbus, OPC UA — a rule that bridges `industrial/+/setpoint` to a Modbus FC 16 write is effectively a remote-write primitive. Check `/api/v5/rules` if you have API access. Older versions had ACL + WebHook bypass issues (CVE-2024-43671 family, check banner).
- **HiveMQ**: Control Center on 8080; extensions (`.hmx`) can add SQL/HTTP/Sparkplug processing. CVE-2023-39226 plain-text creds exposure, CVE-2024-32030 control-center SSRF — confirm against advisory list at <https://www.hivemq.com/security/>.
- **VerneMQ**: HTTP admin on 8888; cluster join keys in `vmq.acl` files; metrics on 8888 carry topic counts.
- **NanoMQ**: lightweight C broker for edge; Sparkplug-aware; recent advisories include packet-handling DoS.

Across all brokers, the cheapest win is the dashboard, not the protocol — port 18083 / 8080 / 1880 (Node-RED) / 8123 (Home Assistant) next to 1883 is the actual entry point in most labs.

## 6. MQTT ↔ PLC bridges and gateways

Bridges turn an MQTT write into a real PLC write. Common ones:

- **Cirrus Link MQTT Modules for Ignition**: Distributor (broker), Engine (broker-side rules), Transmission (edge publisher). DCMD on a Sparkplug device metric maps to a tag write inside Ignition → forwarded to the underlying PLC driver (Modbus, OPC UA, Allen-Bradley, Siemens).
- **EMQX Neuron**: industrial gateway with native Modbus TCP/RTU, S7, OPC UA, EtherNet/IP, Mitsubishi, Omron, IEC 60870-5-104, DNP3 drivers. REST API on 7000 (default `admin/0000`) exposes node creation, group config, tag mapping. Rule engine forwards tag writes from MQTT to PLC.
- **Node-RED** (`1880/ui`, `1880/admin`): `mqtt in/out` nodes feeding `modbus-flex-write`, `node-red-contrib-s7`, `opcua-iiot` nodes. Flows are JSON in `~/.node-red/flows.json` — readable and editable. Admin auth often disabled in lab/dev images.
- **Tasmota / ESPHome**: ESP-based smart plugs and relays, command topic `cmnd/<device>/POWER` → publish `ON`/`OFF`. Common in smart-building CTFs and home automation pivots.
- **OpenPLC**: built-in MQTT module bridges `%QX`/`%IX`/`%MD` to MQTT topics; admin web on 8080 (`openplc/openplc`).
- **MQTT-Modbus gateways from Advantech / Moxa / HMS / Red Lion**: typically JSON payload `{ "value": <num>, "ts": <epoch> }` on `gw/<serial>/tag/<name>`; reverse with one capture cycle, then map command topics.

How to recognize a bridge in a capture or broker dump:

1. Topic prefix often encodes site/area/cell (`plant/line1/cell3/...`) followed by tag-like leaves (`temp`, `setpoint`, `runCmd`, `valveA`).
2. JSON payloads with `ts`, `unit`, `quality`, `aliasId`, `tagPath` are bridge-style; raw scalar payloads are device-direct.
3. Mirror pattern: a `state/...` topic that lags a `cmd/...` topic by ~1 s is a bridge round-tripping through a PLC.
4. Sparkplug NBIRTH whose metrics include `Properties/Engine Version` = Ignition gives away the stack.

## 7. Tool chain (CTF-focused)

- [`mosquitto-clients`](../../../offensive-tools/network/mosquitto-clients/SKILL.md) — `mosquitto_pub`/`mosquitto_sub` for verification, TLS handshake details, retained-message cleanup.
- [`mqtt-pwn`](../../../offensive-tools/network/mqtt-pwn/SKILL.md) — interactive shell with persistent topic/message DB, broker fingerprint, credential brute-force, Sonoff/Owntracks/C2 modules.
- **MQTT Explorer** (GUI, free): tree view of retained topics, JSON pretty-print, diff against snapshots — fastest way to map an unknown broker visually.
- **MQTTX** (Emqx, GUI + CLI): scripting, bench mode, Sparkplug decoder (`mqttx sub --format binary`).
- **mqtt-spy / HiveMQ MQTT CLI**: scriptable subscribers, useful in headless containers.
- **Scapy MQTT layer** (`scapy.contrib.mqtt`): hand-craft malformed CONNECT/PUBLISH packets for fuzzing or protocol-state abuse.
- **Cotopaxi** (Samsung): protocol fuzzing/probing for IoT including MQTT, CoAP, AMQP, DTLS.
- **kacper3355/MQTTSA**: Mosquitto/Hive-style broker security audit script (anon read/write, retained, $SYS, ACL probe) — older but still useful for repeatable reports.
- **Sparkplug decoders**: `pysparkplug`, `tahu` Python, `protoc --decode` against `sparkplug_b.proto`, or Wireshark `sparkplug` dissector (Wireshark 4.2+ ships it natively).
- **Wireshark filters**: `mqtt`, `mqtt.msgtype == 3` (PUBLISH), `mqtt.topic contains "spBv1.0"`, `mqtt.willtopic`, `mqtt.username`.
- **nmap NSE**: `mqtt-subscribe` (subscribe to `#` for N seconds), pair with `--script-args mqtt-subscribe.topic='$SYS/#'`.

## 8. Case material and reference sources

Vendor advisories, research reports, and spec docs to pull technique from. Platform-agnostic — use whatever CTF or lab artifact matches the pattern.

- **MQTT-only broker challenge pattern** (recurring in IoT CTFs): `nmap` finds 1883/8883/8080/9001 → `mosquitto_sub -h <ip> -t '#' -v -W 30` harvests retained topics → flag-like strings surface in plaintext or base64 payloads → command topics reveal actuator paths → publishing to a `cmnd/...` / `req/...` topic triggers a transient reply carrying the next artifact. Anonymous-read → cred-harvest → trigger chain is the canonical flow.
- **Home-automation / smart-building pattern**: identical to broker challenge, but retained credentials pivot into the adjacent web UI (Home Assistant 8123, Node-RED 1880, EMQX 18083, HiveMQ 8080) — the dashboard is usually the real objective, not the broker.
- **OWASP IoT Top 10 + MQTT case studies**: <https://owasp.org/www-project-internet-of-things/>.
- **Akamai MQTT-PWN release post** (origin of the framework, attack patterns + Shodan stats): <https://www.akamai.com/blog/security/introducing-mqtt-pwn>.
- **Trend Micro "The Fragility of Industrial IoT's Data Backbone"** report (MQTT + CoAP exposure scan) — solid for prioritization arguments in reports: <https://www.trendmicro.com/vinfo/us/security/news/internet-of-things/data-backbone-of-the-iiot-mqtt-and-coap>.
- **Sparkplug deep-dive**: HiveMQ "MQTT Sparkplug Essentials" series — <https://www.hivemq.com/blog/mqtt-sparkplug-essentials-part-1-introduction/>.
- **Claroty Team82 MQTT broker research** (Mosquitto, EMQX): vendor advisories indexed at <https://claroty.com/team82/research>.
- **CISA ICS Advisories** with MQTT in title: <https://www.cisa.gov/news-events/cybersecurity-advisories?f%5B0%5D=advisory_type%3A95&search_api_fulltext=mqtt>.
- **Shodan dorks for context** (read-only): `port:1883 product:"mosquitto"`, `port:1883 "$SYS/broker"`, `"Sparkplug" port:1883`. Use only within engagement scope.

Default order when an IoT broker appears in scope: anonymous `#` + `$SYS/#` read → broker/version fingerprint → Sparkplug topic detection → bridge / dashboard pivot → command-topic write only after safety gate.

## 9. Reporting checklist for MQTT findings

For a report or CTF flag justification, capture:

- broker family + version (`$SYS/broker/version`)
- transport (plain/TLS/WS) and port
- auth posture (anon allowed? default creds? ACL coverage?)
- retained-message inventory (count + sensitive examples, redacted)
- Sparkplug presence + edge node / device list (NBIRTH-derived)
- bridge / gateway detection (topic patterns, JSON shapes)
- any command topic that influences physical state, with operator-visible effect (HMI banner, historian sample, actuator state)
- safety classification (is this a SIS-adjacent control loop? if yes, stop and report)
- minimal-restore plan if any write was performed (empty retained, original setpoint, mode return)
