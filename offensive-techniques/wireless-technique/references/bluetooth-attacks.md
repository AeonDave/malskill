# Bluetooth and BLE attack methodology

Use this for authorized Bluetooth Classic and BLE assessments. Keep testing scoped by physical location, adapter address, device identity, and permitted interaction level.

## 1) Assessment sequence

Follow a BSAM-style control flow:

1. **Information gathering**: identify device role, firmware, chipset, mobile app, companion cloud/API, advertised names.
2. **Discovery**: passive scan first; capture advertisements, RSSI, MAC behavior, services advertised.
3. **Pairing**: determine Legacy vs LE Secure Connections, Just Works vs Passkey vs Numeric Comparison, bonding behavior.
4. **Authentication**: test whether services require pairing, bonding, app-layer auth, or only connection.
5. **Encryption**: verify sensitive GATT reads/writes require encrypted link after bonding.
6. **Services/Application**: enumerate GATT/SDP, test access control, replay, OTA/DFU, command characteristics.

Stop if interaction would affect out-of-scope nearby devices.

## 2) Discovery and identity checks

Collect:

- Public/static/random MAC, rotation interval, resolvable private address behavior.
- Advertised local name, manufacturer data, service UUIDs, TX power.
- Classic SDP services and BLE GATT services.
- RSSI over time for physical proximity and tracking risk.

Tools: `offensive-tools/wireless/bluez/`, `offensive-tools/wireless/kismet/`, `offensive-tools/wireless/sparrow-wifi/`, `offensive-tools/network/bettercap/`.

## 3) Pairing/security decision matrix

| Observed pairing | Risk | Test focus |
|---|---|---|
| Just Works | No MITM protection | MITM feasibility, unauthenticated GATT access |
| Passkey Entry | MITM-resistant if displayed/input correctly | Brute-force lockout, replay, UI phishing |
| Numeric Comparison | MITM-resistant with user verification | Downgrade prompts, user-consent bypass |
| Legacy pairing | Weaker key agreement | Downgrade, sniffing, key reuse |
| LE Secure Connections | Strong ECDH base | App-layer auth and GATT authorization |
| No pairing required | High risk for sensitive services | Direct read/write, replay, OTA abuse |

LE Secure Connections improves key exchange, but it does not fix unauthenticated characteristics or weak application authorization.

## 4) BLE 5.4 (Core Spec Jan 2023) surface

When the target advertises `LE Features` bits for EAD or PAwR, extend the workflow:

- **Encrypted Advertising Data (EAD)**: adverts/scan responses are AES-CCM’d with a
  Key Material blob exchanged over an authenticated GATT link. Check for KM read
  without bonding, KM re-use across resets, and replay of the encrypted advert
  block when the device omits the `Randomizer` update.
- **Periodic Advertising with Responses (PAwR)**: bidirectional connectionless
  transport (ESL, sensor swarms). Sniff subevent + response slots with nRF
  Sniffer + Wireshark 4.2+, verify EAD is applied, and test whether response
  slot timing lets an attacker inject before the legitimate peripheral.
- Deprecation reminder: `hcitool`, `hciconfig`, `gatttool`, `sdptool`, `hcidump`
  are in BlueZ’s `bluez-deprecated` subpackage. Prefer `bluetoothctl`, `btmgmt`,
  `btmon`, `btgatt-client` for anything new.

## 5) GATT exploitation workflow

1. Enumerate services, characteristics, descriptors, properties.
2. Label each handle: readable, writable, notify/indicate, authenticated, encrypted, application-sensitive.
3. Read harmless characteristics first: Device Name, Manufacturer, Model, Firmware Revision.
4. Test writes only on scoped, non-destructive handles; prefer toggles/status fields over actuators.
5. Replay captured writes and compare device/app state.
6. For OTA/DFU services, verify signature, rollback, downgrade, and auth gates before any firmware transfer.

Interesting bug classes:

- Sensitive read without pairing or app auth.
- Write without bonding to command/control handles.
- App-layer auth token accepted over unencrypted link.
- Static MAC or stable advertisement payload enabling tracking.
- OTA firmware accepted unsigned, downgraded, or replayed.
- Notifications leak sensitive data before authentication.

## 6) MITM and downgrade paths

Try MITM only after passive + authorization gates:

- Just Works devices are the easiest MITM candidates because there is no authenticated user verification.
- Legacy pairing may allow downgrade or weaker key handling.
- Re-pairing behavior matters: devices that allow unauthorized re-pairing can overwrite trust relationships.
- Mobile apps may trust device name/service UUID instead of cryptographic identity.

Evidence should show both sides' view: central/app, peripheral/device, and captured link behavior.

## 7) Classic Bluetooth notes

Classic Bluetooth still appears in embedded, automotive, audio, and legacy industrial devices.

Assess:

- Discoverability and pairing mode exposure.
- SDP service exposure: OBEX, serial port profile, HID, audio profiles.
- Default PINs or weak pairing UX.
- Stored link key handling on host.
- Unauthorized OBEX file access on old devices.

Most modern phones are hardened; focus Classic testing on scoped embedded/legacy targets rather than random nearby consumer devices.

## 8) Evidence package

- Adapter and tool used, scan window, channel/interface, device MAC/name/UUIDs.
- Passive evidence before active interaction.
- Pairing method and whether MITM protection exists.
- GATT/SDP table with access requirements.
- Reproduction transcript for each read/write issue.
- Impact classification: privacy leak, auth bypass, command execution, tracking, firmware tamper.
