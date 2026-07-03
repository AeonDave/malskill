# Zigbee, Thread, and Matter (802.15.4) Attacks

**Load when**: Investigating smart home environments, smart door locks, connected lighting, commercial IoT sensors, or when the 2.4 GHz spectrum shows non-Wi-Fi low-energy burst activity (802.15.4 / Zigbee channels 11–26).

## Overview

Mesh protocols underpin the vast majority of "Smart Home" devices.
- **Zigbee**: Ubiquitous but plagued by legacy implementations and standard fallback keys.
- **Thread**: Modern, IPv6-based (via 6LoWPAN), stronger defaults.
- **Matter**: The new unification layer that provides a standardized commissioning model with PKI, but implementations remain vulnerable to downgrade/logic flaws.

## 1. Hardware Requirements

Standard Wi-Fi cards cannot sniff 802.15.4.
- **TI CC2531**: The cheapest and most common (used with Zigbee2MQTT and KillerBee).
- **Sonoff Zigbee Dongle E (CC2652P)**: High power, modern support.
- **ApiMote**: Specifically built for the KillerBee suite and `scapy-dot15d4` development.
- **HackRF**: Used for raw IQ capture when modulation is unknown.

## 2. Discovery & Sniffing

Channel 11, 15, 20, and 25 are the most common Zigbee frequencies because they avoid colliding with primary 802.11 Wi-Fi channels (1, 6, 11).

```bash
# Using the KillerBee suite
zbstumbler -i 0             # Find networks, PAN IDs, and coordinators
zbid                        # Identify coordinator nodes
zbdump -c 11 -w zigbee.pcap # Dump 802.15.4 traffic on Channel 11
```

## 3. The Touchlink Commissioning Attack

Many Zigbee Light Link (ZLL) devices support "Touchlink" to quickly join a new network.
The design flaw: It relies on a well-known, globally published transport key (the Zigbee Alliance Default Key: `5A:69:67:42:65:65:41:6C:6C:69:61:6E:63:65:30:39`).

1. Bring an adapter physically close to the target device.
2. Send a Inter-PAN scan request specifying Touchlink.
3. If the device replies, encrypt a "Network Join" request with the `5A...` default key.
4. The device will sever connectivity with its original hub and join the attacker's simulated network (e.g., via `zigate` or custom `scapy` frame).

## 4. Replay and Injection

Unlike WPA2, Zigbee network keys often remain static for years. If a device has not enabled frame counter (anti-replay) protections on the Application layer:

1. Capture a legitimate command (e.g., "Unlock Door", Cluster ID: `0x0101`).
2. Re-transmit the frame byte-for-byte.
3. Use Wireshark with the Zigbee protocol dissector to isolate the ZCL (Zigbee Cluster Library) payload section to craft custom frames.

## 5. Network Join Key Sniffing

When a new device joins a Zigbee 3.0 network, the Trust Center sends the Network Key encrypted with a "Preconfigured Link Key" or the Default Global Trust Center Link Key.

If this exchange is captured:
1. Load `zigbee.pcap` in Wireshark.
2. Add the Default Link Key (`5A:69:67:42:65:65:41:6C:6C:69:61:6E:63:65:30:39`) to **Preferences > Protocols > ZigBee > Pre-configured Keys**.
3. Wireshark automatically extracts the Network Key from the Transport Key packet.
4. Attackers now have persistent, decrypted access to the entire mesh.

### Install-code path (Zigbee 3.0 default)

Zigbee 3.0 stacks (Silabs EmberZNet, TI Z-Stack, most 2023+ hubs) require a
per-device **install code** printed on the device / QR label; the code is
AES-MMO-hashed into a unique preconfigured link key that replaces the well-known
`ZigbeeAlliance09` key for the join.

- If the install code (6/8/12/16 bytes + 16-bit CRC) is exposed via label,
  packaging, cloud portal, or companion-app leak, derive the link key locally
  (`bellows`, `zigpy`, or Silabs sample code) and load it into Wireshark to
  decrypt the join.
- If the hub allows joining with the default `ZigbeeAlliance09` key (compat
  mode), the classic capture path still works — confirm by inspecting the APS
  Transport-Key frame’s KeyType/`Standard Network Key` field.
- Physical access to the device → dump flash via SPI/JTAG and read the stored
  Trust Center Link Key directly (see `hardware-technique`, `spi-flash`).

## 6. Matter 1.3 commissioning attack surface

Matter uses **PASE (Passcode-Authenticated Session Establishment)** with SPAKE2+
for onboarding, then upgrades to **CASE** with Node Operational Certificates.
Recent published vulnerabilities (2024–2025):

- **CVE-2024-3297** — “Delayed Denial-of-Service” in Matter SDK session handling:
  malformed CASE session establishment leaves stale contexts, exhausting the
  device after N joins. Test: hammer CASE Sigma1 with mismatched destination IDs
  and watch commissioning fail after a threshold.
- **CVE-2024-3454** — Matter SDK PASE handling flaw enabling unauthorized
  interaction during commissioning window (see the Black Hat EU 2024 write-up
  “Breaking Matter”).
- **KU Leuven COSIC “What’s the Matter?” (2025)** — formal analysis flagging PASE
  passcode enumeration surface when Manual Pairing Code is short (11 digits,
  discriminator + passcode) and when the commissioning window stays open past
  spec-mandated timeouts.

Operator checks:
1. Trigger commissioning via a spoofed advertisement / BLE beacon (Matter over
   Wi-Fi devices advertise the Commissionable Node service on mDNS `_matterc._udp`;
   Thread devices announce over 802.15.4 SRP).
2. Verify passcode strength (11-digit vs 27-digit long code), window timeout,
   and rate-limit on failed PASE attempts.
3. Enumerate `_matter._tcp` (already-commissioned) vs `_matterc._udp` (open for
   commissioning) via `avahi-browse -tr _matterc._udp`.
4. Where Multi-Admin is enabled, verify NOC issuance is gated on operator
   consent — CVE-2024-3454 abuses this.

Tooling: `chip-tool` (Matter SDK), `matter-server` (Home Assistant), Wireshark
`matter` dissector (>= v4.2), `openthread-cli` for Thread border-router probing.
