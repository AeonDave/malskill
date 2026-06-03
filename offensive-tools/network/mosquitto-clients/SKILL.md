---
name: mosquitto-clients
description: "Auth/lab ref: Mosquitto client tools, primarily `mosquitto_pub` and `mosquitto_sub`, for interacting with MQTT brokers."
compatibility: "Linux, Windows, macOS; mosquitto client package installed."
metadata:
  author: AeonDave
  version: "1.0"
---

# Mosquitto Clients

Small, sharp MQTT tooling for quick broker interaction without writing a custom client first.

## When to use mosquitto-clients

Use these tools when you need to:

- subscribe to MQTT topics and observe message flow
- publish controlled messages to a topic
- validate broker auth, TLS, or topic structure quickly

## Quick Start

```bash
# Subscribe to everything verbosely
mosquitto_sub -h broker.local -t '#' -v

# Publish a test message
mosquitto_pub -h broker.local -t test/topic -m 'hello'
```

## High-Value Workflows

### Authenticated subscribe/publish

```bash
mosquitto_sub -h broker.local -p 1883 -u user -P pass -t 'sensors/#' -v
mosquitto_pub -h broker.local -p 1883 -u user -P pass -t 'actuators/cmd' -m 'on'
```

### TLS example

```bash
mosquitto_sub -h broker.local -p 8883 --cafile ca.pem -t '#' -v
```

## Practical Notes

- Start with a broad read-only subscription pattern like `#` only in controlled environments.
- Use `-v` so topic names and payloads stay paired in output.
- Pair with packet capture or device docs when topic semantics are unclear.

## Caveats

- Publishing to a live broker can trigger real actions.
- Some brokers enforce ACLs, retained messages, or TLS requirements that change what you see.
- Topic wildcards are powerful and noisy; use them intentionally.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the Mosquitto man pages for TLS, session, retained-message, and last-will options.
