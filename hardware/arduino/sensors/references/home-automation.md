# Sensors for Home Automation and Practical Monitoring

Use this when the task is closer to domotica, environment sensing, or binary sensor logic.

## Common home-automation sensor classes

- `binary_sensor` style events: door, motion, leak, smoke, vibration alarm
- environmental sensors: temperature, humidity, pressure, CO2, light
- presence/occupancy sensors: PIR, mmWave, Bluetooth-derived presence
- utility sensors: power, water flow, energy pulses

## Good automation design

- model simple states first
- trigger on clean transitions
- add cooldowns and quiet periods where needed
- keep fail-safe behavior obvious
- distinguish sensing from actuation

## Preferred simple hardware

- reed switch or Hall sensor for open/closed
- PIR for basic motion
- DHT22/BME280-class sensors for climate
- leak probe for water detection
- break-beam only when a path crossing truly matters

## Agent guidance

When asked to design a sensor-based home automation setup:
1. identify whether the user needs measurement, occupancy, or event detection
2. choose the simplest reliable sensor per zone
3. specify wiring and power domain
4. describe debounce, polling interval, and failure modes
5. if using Home Assistant semantics, name likely entities as `sensor.*` or `binary_sensor.*`

## Distilled source notes

This reference borrows the most reusable patterns from Home Assistant binary-sensor conventions and practical smart-home project writeups: clean state transitions, explicit entity meaning, and preference for robust low-complexity hardware.