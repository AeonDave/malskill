---
name: flipper-zero
description: "Flipper Zero app development (FAP), Sub-GHz scripting, badUSB automation, and GPIO hardware bridging."
---

# flipper-zero

**Goal**: Develop Flipper Application Packages (FAPs) in C, create BadUSB/Ducky scripts, or interface the top GPIO pins with external hardware.

## 1. FAP Development (C API)

Flipper apps are compiled out-of-tree using `ufbt` (Micro Flipper Build Tool).

```c
#include <furi.h>
#include <gui/gui.h>

int32_t my_app_app(void* p) {
    UNUSED(p);
    FURI_LOG_I("MY_APP", "Hello Flipper!");
    // Basic infinite loop until exit
    while(1) {
        furi_delay_ms(1000);
    }
    return 0;
}
```
**Compilation**: Run `ufbt` to build the `.fap`. Run `ufbt launch` to deploy to a USB-connected Flipper.

## 2. GPIO Pinout
- Placed on the top edge. **3.3V Logic** (5V tolerant on most pins).
- **USART**: Pins 13 (TX), 14 (RX).
- **I2C**: Pins 15 (SCL), 16 (SDA).
Use the standard Furi Hal functions (`furi_hal_gpio_write()`) for bit-banging or peripheral API.

## 3. Sub-GHz

Using the CC1101 chip. You can invoke Sub-GHz transmissions directly in firmware, or using `.sub` files.
- `.sub` file format supports raw AM/FM modulation plots (Raw IQ) or pre-parsed protocols like KeeLoq.

## 4. BadUSB / DuckyScript
Drop standard `Ducky Script 1.0/2.0` `.txt` files onto the MicroSD card under `badusb/`.
```text
DELAY 1000
GUI r
DELAY 200
STRING cmd
ENTER
DELAY 500
STRING echo "Hacked" > proof.txt
ENTER
```
