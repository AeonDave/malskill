# Wireshark / tshark Wireless 802.11 Workflows

## Why Load This Reference

Load this file when the capture is about Wi‑Fi, EAPOL, WPA/WPA2, or WPA-Enterprise rather than generic TCP/IP traffic.

## Fast Wireless Filters

| Goal | Filter |
|---|---|
| All management frames | `wlan.fc.type == 0` |
| Association request | `wlan.fc.type_subtype == 0` |
| Association response | `wlan.fc.type_subtype == 1` |
| Reassociation request | `wlan.fc.type_subtype == 2` |
| Reassociation response | `wlan.fc.type_subtype == 3` |
| Probe request | `wlan.fc.type_subtype == 4` |
| Probe response | `wlan.fc.type_subtype == 5` |
| Beacon | `wlan.fc.type_subtype == 8` |
| Disassociation | `wlan.fc.type_subtype == 10` |
| Authentication | `wlan.fc.type_subtype == 11` |
| Deauthentication | `wlan.fc.type_subtype == 12` |
| Action frames | `wlan.fc.type_subtype == 13` |
| All control frames | `wlan.fc.type == 1` |
| RTS | `wlan.fc.type_subtype == 27` |
| CTS | `wlan.fc.type_subtype == 28` |
| ACK | `wlan.fc.type_subtype == 29` |
| All data frames | `wlan.fc.type == 2` |
| QoS data | `wlan.fc.type_subtype == 40` |
| Retry frames | `wlan.fc.retry == 1` |
| EAPOL | `eapol` |
| One SSID | `wlan.mgt.ssid == "TargetSSID"` |
| One BSSID | `wlan.bssid == 00:11:22:33:44:55` |
| One station | `wlan.addr == aa:bb:cc:dd:ee:ff` |

## WPA / WPA2 / Enterprise Review

Useful patterns:

```bash
# WPA/WPA2 EAPOL frames
tshark -r wifi.pcap -Y "eapol"

# TLS certificates seen during WPA-Enterprise / EAP-TLS style exchanges
tshark -r wifi.pcap -Y "tls.handshake.certificate"

# dump only the certificate field
tshark -r wifi.pcap -Y "tls.handshake.certificate" -T fields -e tls.handshake.certificate

# verbose plaintext-style decode of matching packets
tshark -nr wifi.pcap -Y "tls.handshake.certificate" -V

# JSON output for downstream processing
tshark -nr wifi.pcap -Y "tls.handshake.certificate" -T json -V
```

## Signal / RF Triage

When radio metadata exists in the capture:

| Goal | Filter |
|---|---|
| Weak signal overall | `wlan_radio.signal_dbm < -67` |
| Weak probe responses | `wlan.fc.type_subtype == 0x05 && wlan_radio.signal_dbm < -75` |
| Weak probe requests | `wlan.fc.type_subtype == 0x04 && wlan_radio.signal_dbm < -75` |

## 802.11k / 11r / 11v Clues

| Goal | Filter |
|---|---|
| 802.11k neighbor request | `wlan.fixed.action_code == 4` |
| 802.11k neighbor response | `wlan.fixed.action_code == 5` |
| 802.11v BSS transition | `wlan.fixed.action_code == 7 || wlan.fixed.action_code == 8` |
| 802.11r auth request | `(wlan.fc.type_subtype == 0) && (wlan.rsn.akms.type == 3)` |
| 802.11r auth response | `(wlan.fc.type_subtype == 1) && (wlan.tag.number == 55)` |

## Decryption Notes

If you recovered the key already:
- in Wireshark GUI: `Preferences -> Protocols -> IEEE 802.11 -> Decryption Keys`
- for WEP, use the hex key form
- or decrypt first with `airdecap-ng` and open the resulting file again

## Practical Interpretation Tips

- Beacons reveal SSID, channel, security advertising, and AP cadence.
- Auth / deauth / disassoc bursts often explain client churn or failed reconnect attempts.
- `eapol` frames are the fast first stop for WPA/WPA2 handshake review.
- `tls.handshake.certificate` is especially useful in WPA-Enterprise certificate-based environments.
- Retries plus weak `wlan_radio.signal_dbm` often point to RF quality issues, not just application problems.

## Source Pointers

- antlarac Wi‑Fi pentesting cheatsheet (`8 - wireshark.md`, `2 - protocols.md`)
- WiFi Professionals wireless display filter list
