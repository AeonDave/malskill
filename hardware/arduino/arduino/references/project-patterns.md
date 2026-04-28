# Arduino Project Patterns

Load this when designing or reviewing a complete Arduino project instead of an isolated snippet.

## Intake checklist

Lock these before writing code:

1. exact board
2. board family and voltage domain
3. toolchain: `Arduino IDE 2`, `Arduino CLI`, or `PlatformIO`
4. required buses: `I2C`, `SPI`, `UART`, `1-Wire`, PWM, interrupts
5. outputs and current draw: LEDs, relays, buzzers, displays, motors, servos
6. runtime needs: response time, debounce, sampling cadence, autonomous boot, logging
7. deliverables: code only, wiring notes, BOM, test plan, debug plan, migration notes

## Toolchain choice

- Choose **Arduino IDE 2** for quick sketches, simple bring-up, or beginner-friendly examples.
- Choose **Arduino CLI** when the task is automation-oriented but still Arduino-native.
- Choose **PlatformIO** for multi-file projects, dependency control, unit tests, source-level debugging, CI, or multiple build environments.
- Choose **Arduino Cloud** when the user needs OTA updates, remote dashboards, or fleet management with minimal infrastructure.

## Recommended output bundles

### Small sketch

- single `.ino`
- pin constants near top
- library list
- wiring bullets
- first power-on steps

### Medium project

- `.ino` plus helper `.h/.cpp` files only where they improve readability
- central config section
- short wiring table
- calibration notes
- serial bring-up procedure

### Professional project

- `PlatformIO` project with `src/`, `lib/`, `include/`, `test/`
- `platformio.ini`
- explicit dependency list
- wiring and power notes
- test plan: smoke, functional, regression
- troubleshooting section for upload/monitor/debug issues

## Architecture patterns to prefer

- centralize pins, timing constants, feature flags, thresholds, and calibration
- isolate pure logic from direct hardware calls
- keep `setup()` for initialization and `loop()` for orchestration
- use `millis()` scheduling, state machines, or small task-style loops for event-driven behavior
- make debug logging easy to enable and disable
- wrap board-specific behavior behind small helpers instead of spreading it everywhere

## Architecture patterns to avoid

- GPIO numbers scattered across files
- hardware assumptions hidden inside generic helper names
- large monolithic `loop()` functions that do everything
- long blocking delays in projects that read inputs, use networking, or drive multiple outputs
- library sprawl for simple peripherals
- portability claims that ignore board-specific voltage, timers, or buses

## PlatformIO migration notes

When translating an Arduino sketch into PlatformIO:

1. move the main entrypoint to `src/main.cpp`
2. add `#include <Arduino.h>`
3. add headers or forward declarations because `.ino` auto-preprocessing is gone
4. move reusable code into `lib/` or `include/`
5. move dependency declarations into `platformio.ini`
6. place tests in `test/`

## First power-on workflow

Use a staged bring-up path:

1. confirm board, cable, port, and power source
2. flash a minimal heartbeat or serial sketch
3. verify serial monitor baud rate and output
4. enable one peripheral at a time
5. only then enable actuators, networking, or advanced features

## OTA considerations

- OTA is practical on boards with a network stack: ESP32, Uno R4 WiFi, MKR WiFi, Nano 33 IoT.
- Always keep a wired upload fallback; a bad OTA push can brick the update path.
- Verify that flash space can hold two firmware images (current + incoming) when using partition-based OTA.
- For `Arduino Cloud`, OTA is built-in; for standalone ESP32, use `ArduinoOTA` or `esp_https_ota`.

## Deliverable checklist

- board and toolchain called out explicitly
- code compiles for the stated target
- wiring notes match the code
- power notes mention current-heavy loads and shared ground
- libraries/dependencies are listed
- serial monitor speed is stated when relevant
- first power-on procedure is included
- likely failure modes are documented
