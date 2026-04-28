# Sensor Signal Quality and Reliability

Load this when the task involves debounce, false positives, threshold tuning, or noisy real-world signals.

## Core principle

A project fails less often when the sensor choice, mechanical mounting, and signal interpretation all agree.

## Reliability workflow

1. Check whether the sensor measures the target event directly.
2. Inspect the mounting and mechanical coupling.
3. Confirm voltage levels and pull-up/pull-down assumptions.
4. Add debounce / hysteresis / cooldown appropriate to the signal.
5. Test with realistic disturbances, not only bench conditions.

## Common fixes by signal type

### Digital trigger sensors
Examples: break-beam, switches, reed sensors, PIR modules
- use edge-based detection, not repeated level triggering
- debounce switches
- document whether the signal is active-low or active-high
- if needed, require inactive recovery before allowing another event

### Analog threshold sensors
Examples: piezo front-end, FSR, LDR, analog vibration modules
- maintain baseline or rolling average when drift exists
- use threshold + cooldown
- consider hysteresis to avoid chatter
- calibrate per sensor if mounting differs

### Multi-sensor zone detection
- ensure the same rule selects both event strength and winning zone
- document tie-breaking behavior
- log ambiguous frames when two zones fire together

## Mechanical guidance

- isolate from the table when the arena/device should sense local events only
- hard-mount to the structure when the event propagates through the structure
- test placement before changing code

## Home automation note

For binary sensors and room automations, reliable state transitions matter more than high sample rate. Favor clear `on/off`, `open/closed`, `occupied/vacant` semantics and explicit recovery timing.
