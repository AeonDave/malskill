# BlueZ Scan, Read & Debug Workflow

## Adapter Bring-Up

Start with controller state, not with random scan commands.

```bash
bluetoothctl list
bluetoothctl show
rfkill list
```

If blocked, unblock before deeper debugging.

## Discovery Workflow

```bash
bluetoothctl
[bluetooth]# power on
[bluetooth]# scan on
```

Look for:
- MAC address
- device type clues
- RSSI / visibility stability
- whether device is advertising only intermittently

## Pair / Trust / Connect Workflow

```bash
bluetoothctl
[bluetooth]# pair AA:BB:CC:DD:EE:FF
[bluetooth]# trust AA:BB:CC:DD:EE:FF
[bluetooth]# connect AA:BB:CC:DD:EE:FF
```

Use trust only where persistent access is intended and authorized.

## Monitor-First Debugging

When something fails unexpectedly, run:

```bash
btmon
```

This helps determine whether failure is due to:
- controller state
- pairing/auth issues
- service discovery failure
- unstable advertisements / signal issues

## BLE Practical Notes

For BLE reconnaissance:
- keep scans long enough for intermittent advertisements
- validate whether the device is connectable or advertisement-only
- use monitor output when service enumeration seems inconsistent

## On Deprecated Tools

Some legacy guides rely on deprecated tools. Prefer current BlueZ client workflows first, and only use older utilities when the environment explicitly requires them.

## Source Pointers

- BlueZ upstream: current maintained stack, tools, client and monitor support
