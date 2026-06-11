---
name: raspberry-pi
description: "Raspberry Pi hardware interfacing: GPIO, I2C, SPI, UART, and Python programming for SBC hardware."
---

# raspberry-pi

**Goal**: Interface hardware peripherals (sensors, actuators, radios) with a Raspberry Pi running a standard Linux OS (Raspberry Pi OS).

## 1. Pinout & Buses

The 40-pin GPIO header provides multiple buses. 
- **Levels**: GPIO logic is **3.3V**. Connecting 5V signals directly will destroy the Pi.
- **I2C**: Pins 3 (SDA) and 5 (SCL). Requires enabling via `raspi-config`. Built-in pull-up resistors (1.8kΩ) exist on these pins.
- **SPI**: Pins 19 (MOSI), 21 (MISO), 23 (SCLK), 24 (CE0), 26 (CE1).
- **UART**: Pins 8 (TX) and 10 (RX). Usually mapped to `/dev/serial0` (disables Bluetooth console on Pi 3/4).

## 2. Software Interfacing (Python)

Prefer `gpiozero` for simple UI/sensors and `smbus2` or `spidev` for deep bus control.

### I2C Scanner
```bash
sudo apt install i2c-tools
i2cdetect -y 1
```

### Python I2C Example
```python
from smbus2 import SMBus
with SMBus(1) as bus:
    # Read a byte from device 0x48, register 0x00
    b = bus.read_byte_data(0x48, 0)
```

## 3. Production Rules
- **Power**: The 5V pins bypass the polyfuse. Modulating heavy loads (motors) requires an external relay/MOSFET and separate power supply.
- **Real-Time Limits**: Linux is not a Real-Time OS. Fast bit-banging (like NeoPixels or strict timing protocols) will jitter unless offloaded to the PWM/DMA controllers or a co-processor (like an Arduino/Pico).
