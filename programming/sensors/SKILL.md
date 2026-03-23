---
name: sensors
description: "Select, compare, and integrate sensors for Arduino, ESP32, robotics, model-making, and home automation with focus on signal quality, false positives, debounce, and practical wiring. Use when asked which sensor to choose, how to detect an event reliably, how to map signals into code, or how to design sensor-driven systems such as break-beams, PIR, vibration, IMU, climate, occupancy, or binary-sensor style automations."
license: MIT
metadata:
  author: Astrid
  version: "1.0"
---

# Sensors

This skill is for picking the right sensor and making it behave in the real world, not just on paper.

Use it when the hard part is reliability: noisy rooms, bounce, bad mounting, false triggers, threshold tuning, or choosing between several sensor types.

## Workflow

1. Define the event or quantity.
   - presence, passage, open/closed, impact, orientation, distance, climate, occupancy, leak, smoke

2. Define the environment.
   - indoor/outdoor
   - noisy people nearby
   - vibration, dust, sunlight, reflective surfaces
   - battery vs mains

3. Prefer the sensor that directly measures the thing that matters.
   - impact -> piezo / vibration / accelerometer, not microphone
   - path crossing -> break-beam or switch, not generic ranging by default
   - open/closed -> reed / Hall / microswitch

4. Specify the signal model.
   - digital or analog
   - active-low or active-high
   - debounce, hysteresis, cooldown, baseline drift, edge detection

5. Describe failure modes and fallback options.
   - false positives from noise
   - missed triggers due to blocking code
   - calibration drift
   - ambiguous multi-sensor events

## Decision rules

- If the environment is noisy, avoid microphones unless audio itself is the signal.
- If the event is a physical crossing, start with break-beam.
- If the structure feels the event, mount the sensor on the structure.
- If two sensors are viable, prefer the one with easier calibration and clearer failure modes.

## Output rules

When recommending a sensor or architecture, include:
- why this sensor fits the environment
- why common alternatives are worse here
- wiring/interface type
- tuning notes: debounce, threshold, cooldown, sampling
- whether the project needs edge-based logic, not just level polling

## When to load references

- Load `references/sensor-selection.md` when choosing among sensor families.
- Load `references/signal-quality.md` when debugging false triggers, debounce, or noisy data.
- Load `references/home-automation.md` when the task is about domotica, occupancy, binary sensors, or practical monitoring.

## Resources

### references/

- `references/sensor-selection.md` — selection workflow and concrete recommendations by use case.
- `references/signal-quality.md` — debounce, hysteresis, cooldown, mounting, and ambiguous-event handling.
- `references/home-automation.md` — binary-sensor style thinking and practical smart-home sensor patterns.
