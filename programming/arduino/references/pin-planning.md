# Arduino Pin Planning

Load this when the task involves GPIO assignment, wiring tables, buses, or bring-up.

## Pin planning workflow

1. Identify the exact board, not just the family.
2. Mark the board voltage domain before assigning peripherals.
3. Reserve fixed-function or fragile pins first:
   - UART / USB-related pins
   - `I2C`, `SPI`, `UART` buses
   - native LEDs, built-in peripherals, and board-only features
   - interrupt-sensitive or timing-sensitive inputs
4. Place always-on sensors on stable, boring pins.
5. Put current-heavy loads behind drivers, not MCU pins.
6. Put the final mapping in both code and human-readable wiring notes.

## Voltage-domain guardrails

- `5V` AVR and many classic Arduino boards can often read and drive `5V` logic directly.
- `3.3V` boards and modules must not be treated as `5V` tolerant unless documentation explicitly says so.
- For mixed-voltage designs, mention level shifting and common ground explicitly.
- External power for motors, servos, relay coils, and LED strips is the default expectation, not an optional footnote.

## Board-family cautions

### Classic AVR (`Uno`, `Nano`, `Mega`)

- Treat `D0` and `D1` as serial-sensitive pins.
- Document PWM and analog assumptions; do not imply every digital pin can do PWM.
- Keep RAM limits in mind when choosing displays, buffers, and protocol stacks.

### `Uno R4 WiFi`

- GPIO reference voltage is `5V`.
- `D0`/`D1` are UART pins; avoid using them casually.
- `A4`/`A5` are on the primary `I2C` bus.
- The Qwiic/STEMMA connector uses the secondary `I2C` bus and `Wire1`, and is `3.3V` only.
- Built-in features such as the LED matrix, DAC, RTC, CAN, and HID can consume pins, buses, or debugging attention; mention them when relevant.

### ESP32-based boards

- Prefer ADC-safe choices for analog sensors when Wi-Fi is active.
- Treat boot-sensitive pins carefully.
- Do not assume an ESP32 pin map is universal across every dev board variant.

### Native USB boards

- Keep UART pins separate from USB serial assumptions.
- Document which serial object is intended for debug output when the board exposes more than one path.

### RP2040-based boards (`Nano RP2040 Connect`, `Pico`)

- ADC available only on GPIO `26`–`29`.
- All GPIO pins support PWM.
- `I2C`, `SPI`, and `UART` can be remapped to multiple pin sets via hardware peripherals.
- `3.3V` logic; no `5V` tolerant pins.

### SAMD-based boards (`Zero`, `MKR` family, `Nano 33 IoT`)

- Native 12-bit ADC; call `analogReadResolution(12)` to use it.
- True DAC output on `A0` (on `Zero` and some MKR boards).
- `3.3V` logic; treat all I/O as `3.3V` unless documentation says otherwise.
- EEPROM is emulated in flash; avoid frequent writes in loops.

## Pin-constant format in code

Centralize all pin assignments so they match the wiring table:

```cpp
// — pin assignments (match wiring table) —
constexpr uint8_t PIN_BUTTON    = 2;   // digital input, INPUT_PULLUP, active-low
constexpr uint8_t PIN_LED       = 9;   // PWM output
constexpr uint8_t PIN_RELAY     = 7;   // digital output, active-high, via transistor
// I2C on default bus (SDA/SCL)
```

## Wiring output format

Use a compact table or bullet list with:

- function
- board pin / GPIO
- voltage domain
- direction
- note: pull-up, pull-down, PWM, bus role, input-only, current draw, or boot sensitivity

Example:

- button -> `D2` -> `5V` digital input -> `INPUT_PULLUP`, active-low
- OLED SDA -> `A4` / `SDA` -> `5V` or shifted bus -> primary `I2C`
- Qwiic sensor SDA -> Qwiic / `Wire1` -> `3.3V` only -> secondary `I2C`

## Mapping heuristics

- analog sensor -> ADC-capable pin
- switch / PIR / break-beam -> stable digital input with explicit pull-up or pull-down
- `I2C` sensors -> shared bus with address notes
- `SPI` display or radio -> reserve the whole bus before assigning convenience pins elsewhere
- servo, buzzer, dimmable LED -> PWM-capable output

## Documentation rule

Never ship code with pin constants only. Always include matching human wiring notes and power assumptions.