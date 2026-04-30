# Sparrow-WiFi HackRF, Bluetooth & Agent Workflows

## When Sparrow Is the Right Tool

Use Sparrow when you need more than just AP capture:
- Wi‑Fi + Bluetooth in one workflow
- GUI plus headless remote collection
- HackRF One or Ubertooth-assisted spectrum context
- JSON API integration into other tooling

## HackRF One Notes

HackRF One provides:
- 1 MHz to 6 GHz range overall hardware capability
- useful spectral workflows in Sparrow for 2.4 / 5 GHz overlays
- one band at a time in Sparrow spectrum use

Practical reminder:
- use an antenna appropriate for the target band
- many default antennas are not ideal for Wi‑Fi bands

Quick hardware sanity check outside Sparrow:

```bash
hackrf_sweep
```

## Bluetooth Workflows

Sparrow supports:
- BLE advertisement scanning with standard adapters
- richer Bluetooth visibility with Ubertooth + optional companion tooling
- Bluetooth-related API access via the headless agent

Baseline test before blaming Sparrow:

```bash
bluetoothctl scan on
```

## Remote Agent Workflow

```bash
sudo ./sparrowwifiagent.py --port 8020
```

Useful API examples:

```bash
curl http://sensor:8020/wireless/networks/wlan0
curl http://sensor:8020/gps/status
curl http://sensor:8020/bluetooth/discoverystarta
curl http://sensor:8020/bluetooth/discoverystatus
```

Security note:
- restrict access with `--allowedips`
- do not expose the agent broadly without access controls

## Adapter Guidance

- basic Wi‑Fi scanning: many adapters work
- monitor-mode / raw-frame workflows: validate chipset carefully
- Sparrow DroneID / advanced monitor workflows are stricter than ordinary scans

## Kismet vs Sparrow

| Need | Better fit |
|---|---|
| passive distributed RF logging | Kismet |
| GUI with HackRF/Ubertooth spectrum overlays | Sparrow |
| remote JSON API for Wi‑Fi/BT scans | Sparrow |
| pure Bluetooth stack operations | BlueZ |

## Source Pointers

- Sparrow README (April 2026 updates, agent, DroneID, HackRF, Bluetooth)
- Great Scott Gadgets HackRF One specs and documentation links
