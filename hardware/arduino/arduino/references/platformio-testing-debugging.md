# Arduino + PlatformIO, Testing, and Debugging

Load this when the task mentions `PlatformIO`, tests, upload failures, serial monitor issues, or debugging.

## When PlatformIO is the right answer

Prefer `PlatformIO` when the user needs:

- multi-file firmware
- dependency management in config instead of manual library installs
- multiple environments or boards
- unit tests
- source-level debugging
- CLI-friendly build/upload flows

## Standard PlatformIO project shape

- `src/` — application entrypoint such as `main.cpp`
- `lib/` — reusable project libraries
- `include/` — headers
- `test/` — unit and on-device tests
- `platformio.ini` — board, framework, monitor, upload, debug, and dependency config

### Minimal `platformio.ini` examples

```ini
; Arduino Uno (classic AVR)
[env:uno]
platform = atmelavr
board = uno
framework = arduino
monitor_speed = 9600

; Arduino Uno R4 WiFi (Renesas)
[env:uno_r4_wifi]
platform = renesas-ra
board = uno_r4_wifi
framework = arduino
monitor_speed = 115200

; ESP32 Dev Module
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
    bblanchon/ArduinoJson@^7.0.0
```

## Migration checklist from Arduino sketches

When converting a sketch:

1. move the sketch entrypoint into `src/main.cpp`
2. add `#include <Arduino.h>`
3. add forward declarations or headers because `.ino` preprocessing is gone
4. move reusable code into `lib/` and `include/`
5. declare dependencies in `platformio.ini`
6. place tests under `test/`

## Verification ladder

For a real PlatformIO deliverable, the agent should usually specify this order:

1. build
2. upload
3. monitor serial output
4. run tests if present
5. debug only after the simplest serial smoke test works

## Unit testing guidance

PlatformIO supports unit testing on the host machine, on embedded targets, or both.

Prefer this split:

- pure logic, parsers, state transitions, math, and scheduling helpers -> host-testable
- bus wrappers, sensor drivers, and board integration -> on-device smoke or integration tests

For Arduino-on-device tests, `Unity` is a strong default. Structure tests so that hardware-free logic can be exercised without requiring a board.

## Debugging guidance

- If the board has an onboard debug probe, say so and use it.
- Otherwise, call out the need for an external probe instead of pretending breakpoints are free.
- If source-level debugging is impractical, fall back to staged bring-up and serial tracing.

### Verified `Uno R4 WiFi` notes

- PlatformIO board ID: `uno_r4_wifi`
- Platform: `renesas-ra`
- Framework: `arduino`
- Default upload protocol: `sam-ba`
- Supported upload/debug options include `cmsis-dap`, `jlink`, and `sam-ba`
- `Uno R4 WiFi` is listed as ready for debugging with an onboard debug probe in PlatformIO

## Upload and serial troubleshooting checklist

Check these first, in order:

1. exact board target
2. correct board package or PlatformIO board ID
3. correct port
4. working data cable, not charge-only cable
5. correct monitor baud rate
6. driver visibility on the host OS
7. native USB disconnect/reconnect behavior after reset or upload

## Common failure modes to call out

- wrong board or port selected
- serial monitor opened at the wrong baud rate
- `while (!Serial) {}` blocking unattended startup on native-USB boards
- USB port changing after HID activation or reset
- using UART pins for peripherals while also expecting clean serial upload or monitor behavior
- forgetting that `.ino` auto-prototypes do not exist in `main.cpp`
- choosing a `PlatformIO` board ID by guesswork instead of verification

## Windows-specific reminder

On Windows, serial ports appear as `COM` devices. If upload or monitor fails, tell the user to verify the active port in Device Manager and confirm that connecting the board adds a new port.