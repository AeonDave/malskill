# Arduino Board Families

Load this when choosing a board, comparing targets, or explaining why a solution changes across Arduino families.

## Family buckets

Use these buckets early. They predict both firmware style and troubleshooting.

### Classic AVR

Examples: `Uno`, `Nano`, `Mega`, `Pro Mini`

- Strengths: simple bring-up, huge example base, predictable GPIO behavior
- Constraints: tight RAM/flash, limited concurrency, no built-in Wi-Fi/BLE
- Good default for: buttons, relays, simple sensors, displays, classroom projects
- Watch for: `String` overuse, large buffers, heavy libraries, and pin conflicts on `D0`/`D1`

### Renesas-based Arduino R4 class

Examples: `Uno R4 Minima`, `Uno R4 WiFi`, `Nano R4`

- Strengths: more capable MCU, richer peripherals, more headroom than AVR
- Constraints: not all legacy AVR assumptions carry over
- Good default for: projects that still want Arduino ergonomics but need more peripherals, resolution, or modern USB features
- Watch for: board-specific USB behavior, timer differences, and extra built-in hardware that changes wiring or debugging decisions

#### `Uno R4 WiFi` specifics

- Main MCU: `RA4M1`, `48 MHz`, `256 KB flash`, `32 KB SRAM`
- Logic level: `5V`
- Built-in extras: `12x8` LED matrix, DAC, RTC, CAN, HID support
- Wireless: provided by onboard `ESP32-S3` connectivity module, not by the main RA4M1 itself
- Qwiic/STEMMA: secondary `I2C` bus via `Wire1`, `3.3V` only
- USB caveat: HID use can make the board enumerate differently; direct ESP32 programming can disrupt the default bridge firmware

### ESP32-based Arduino targets

Examples: `Nano ESP32`, `ESP32 Dev Module`, `ESP32-S3` boards used with the Arduino framework

- Strengths: Wi-Fi/BLE, more RAM/flash, strong ecosystem, good fit for networking and richer peripherals
- Constraints: `3.3V` logic, board-specific boot/USB quirks, more complex debugging stories
- Good default for: networking, BLE, dashboards, OTA, richer web or protocol stacks
- Watch for: reset/monitor timing, radio interactions, and board-specific pin restrictions

### Other native-USB Arduino families

Examples: SAMD, RP2040, nRF52, some newer Arduino boards

- Strengths: better tooling, modern USB, often more RAM than AVR
- Constraints: serial device can disappear during reset/upload; peripheral layout varies a lot
- Good default for: sensor hubs, USB projects, moderate-complexity firmware
- Watch for: `while (!Serial) {}` blocking autonomous boot and confusion between USB serial and UART pins

## How to choose quickly

- Choose **AVR** when simplicity and compatibility matter more than resources.
- Choose **R4** when the user wants Arduino familiarity with more modern peripherals and headroom.
- Choose **ESP32** when connectivity or higher-complexity application logic is core to the task.
- Choose **native-USB ARM/RP2040/nRF52** when USB features, better resources, or specific onboard peripherals matter.

## Output rule

When the user says only "Arduino", do not answer with board-specific pins or voltage claims until the board family is narrowed down.