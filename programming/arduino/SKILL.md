---
name: arduino
description: "Build, review, debug, and scaffold professional Arduino projects across classic AVR boards (`Uno`, `Nano`, `Mega`), Renesas-based R4 boards (`Uno R4 Minima`, `Uno R4 WiFi`, `Nano R4`), ESP32-based Arduino boards, and other common Arduino-family targets. Use when asked for sketches, `.ino` files, Arduino IDE 2, Arduino CLI, PlatformIO, or Arduino Cloud workflows, board-specific pin maps, wiring/BOM notes, unit tests, debug plans, upload/serial monitor troubleshooting, or refactors that must stay practical on real hardware."
license: MIT
metadata:
  author: Astrid
  version: "2.0"
---

# Arduino

This skill is for end-to-end Arduino work that must survive contact with real hardware: board selection, wiring, firmware structure, PlatformIO, testing, debugging, and troubleshooting.

If the task is mainly about choosing sensors or dealing with noisy detection in robotics/domotica, also load `sensors`.

## Workflow

1. Lock the target board, toolchain, and capability profile.
   - Prefer exact names: `Arduino Uno`, `Uno R4 WiFi`, `Nano ESP32`, `ESP32 Dev Module`, etc.
   - Lock the toolchain: `Arduino IDE 2`, `Arduino CLI`, `PlatformIO`, or `Arduino Cloud`.
   - If the target is unknown, state assumptions and choose the narrowest safe target.
   - Immediately note: board family, voltage domain, resource limits, reserved pins, wireless stack.

2. Plan hardware and wiring before code structure.
   - Separate inputs, outputs, buses, interrupts, and high-current loads.
   - Document pull-up or pull-down assumptions, current draw, and shared grounds.
   - Call out when motors, relays, LEDs, displays, or radio modules need external power, drivers, transistors, or level shifting.

3. Choose the right project shape.
   - Use a single `.ino` only for small sketches or fast experiments.
   - For reusable or testable firmware, split pure logic from hardware access.
   - For professional or multi-file work, prefer `PlatformIO` with `src/`, `lib/`, `include/`, and `test/`.
   - When migrating from Arduino sketches to PlatformIO, remember that `.ino` preprocessing disappears: add `#include <Arduino.h>`, proper headers, and forward declarations.

4. Write firmware for bring-up, maintenance, and testability.
   - Keep pin constants, feature flags, calibration values, and timing constants centralized.
   - Prefer `millis()` scheduling, finite-state machines, or task-style loops over long blocking `delay()` chains.
   - Isolate pure logic so it can be unit-tested without hardware.
   - Add serial diagnostics that help first power-on, but avoid unbounded serial spam.
   - Use compile-time flags or config constants for optional hardware and verbose logging.

5. Define a verification ladder before finishing.
   - Smoke test: compile, upload, and confirm a minimal heartbeat or serial log.
   - Functional test: verify each sensor, bus, actuator, and failure path.
   - For PlatformIO projects, include `build`, `upload`, `monitor`, and `test` steps.
   - If the board supports debugging, include a debug plan and probe assumptions.
   - If the board does not support practical source-level debugging, fall back to serial tracing, staged bring-up, and smaller test sketches.

6. Deliver complete output.
   - firmware files
   - wiring table / pin map
   - library or dependency list
   - board/toolchain assumptions
   - first power-on checklist
   - test plan
   - troubleshooting notes for the most likely failure modes

## Board-family rules

Load `references/board-families.md` for full details. Minimum awareness without loading the reference:

- **Classic AVR**: tight RAM/flash; avoid `String` abuse and large buffers; `D0`/`D1` are serial-sensitive.
- **Renesas R4**: not a faster AVR; check USB behavior, timers, analog resolution, and extra peripherals.
- **ESP32-based**: `3.3V` logic; be explicit about radio constraints and boot-sensitive pins.
- **Native USB**: `while (!Serial) {}` blocks autonomous boot; serial port can disappear on reset.

## Review checklist

- board target is explicit
- toolchain is explicit (`Arduino IDE 2`, `Arduino CLI`, or `PlatformIO`)
- pin map in code matches pin map in docs
- analog/digital assumptions are documented
- power and voltage-domain notes are present
- blocking `delay()` use is justified or removed
- optional hardware is behind flags or clearly separated
- first bring-up and troubleshooting path exists
- `PlatformIO` config, if present, matches the board and monitor assumptions
- library and dependency versions are pinned when reproducibility matters

## Output rules

- Do not claim portability across boards when using board-specific pins.
- Do not invent a `PlatformIO` board ID, upload protocol, or debugger choice.
- Do not scatter GPIO numbers through the code.
- Do not leave voltage-domain assumptions implicit.
- Do not recommend powering motors, servos, relays, or LED strips directly from a board pin.
- Call out when serial debugging may fail because of board/port selection, driver issues, baud mismatch, native USB resets, or `while (!Serial) {}`.
- For `Uno R4 WiFi`, mention board-specific caveats when they matter: Qwiic is `3.3V` on `Wire1`, HID can change the USB port, and direct ESP32 programming can break the default bridge firmware.
- If a sensor needs protection or signal conditioning, say so clearly.
- Pin library versions in dependency lists and `lib_deps` when the project needs reproducibility.

## When to load references

- Load `references/project-patterns.md` for project shape, architecture, OTA guidance, bring-up flow, and deliverables.
- Load `references/pin-planning.md` when assigning GPIOs, documenting wiring, or checking bus and voltage constraints.
- Load `references/board-families.md` when selecting a board, comparing families, or explaining board-specific caveats.
- Load `references/platformio-testing-debugging.md` when the request mentions `PlatformIO`, tests, upload issues, serial monitor issues, or debugging.

## Resources

### references/

- `references/project-patterns.md` — project intake, architecture, deliverable bundles, and first-power-on workflow.
- `references/pin-planning.md` — GPIO planning, voltage-domain checks, bus mapping, and wiring-output format.
- `references/board-families.md` — practical differences between AVR, R4, ESP32-based, and native-USB Arduino targets.
- `references/platformio-testing-debugging.md` — PlatformIO structure, migration guidance, unit testing, debugging, and troubleshooting.
