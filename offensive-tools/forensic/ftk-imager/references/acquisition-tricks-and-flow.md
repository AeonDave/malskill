# FTK Imager acquisition tricks and flow

## Collection strategy

- Default to full-disk image when legal/operationally possible.
- Use targeted logical collection for early triage or constrained windows.
- Capture volatile memory early in live incidents when malware is active.

## Defensibility checklist

1. Record source device identifiers and timestamps.
2. Record tool version and acquisition mode.
3. Save hash verification outputs.
4. Preserve acquisition logs with case file.
5. Keep originals read-only and analyze from copies.

## Operational tricks

- Keep a prepared external toolkit drive for rapid on-site collection.
- Predefine folder naming: `<case>/<host>/<timestamp>/<artifact-type>`.
- Validate destination free space before starting acquisition.
- If acquisition must be interrupted, document exact stop condition and elapsed time.

## Escalation path

- Disk/image artifacts -> Autopsy or Sleuth Kit.
- Memory image -> Volatility3.
- Network artifacts -> Zeek/Wireshark/tcpdump chain.
