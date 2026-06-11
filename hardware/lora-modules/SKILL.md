---
name: lora-modules
description: "LoRa and LoRaWAN SPI module interfacing (SX1276, SX1262), frequency band tuning, and radio libraries."
---

# lora-modules

**Goal**: Establish long-range, low-power radio communication using Semtech LoRa transceivers (SX1276/SX1278, RFM95, SX1262) via SPI.

## 1. Hardware Interface

LoRa chips communicate via **SPI** and use a few extra interrupt pins to notify the MCU when a packet is received.
- `SCK`, `MISO`, `MOSI` -> Hardware SPI.
- `NSS` (Chip Select).
- `RST` (Reset pin).
- `DIO0`, `DIO1` (Data Input/Output interrupts).

**Logic Level**: Strictly **3.3V**. 

## 2. Point-to-Point vs LoRaWAN

- **LoRa (Physical Layer)**: Two nodes talking directly to each other using the `RadioHead` (RH_RF95) or `LoRa` library. No network joining, no encryption by default.
- **LoRaWAN (MAC Layer)**: Connecting an edge node to public networks like The Things Network (TTN) or Helium. Requires the `LMIC` (LoRaMAC-in-C) library. Uses AES-128 encryption and requires AppSKey/NwkSKey provisioning.

## 3. Simple Point-to-Point Example (Arduino)

```cpp
#include <SPI.h>
#include <LoRa.h>

void setup() {
  Serial.begin(115200);
  // CS=10, reset=9, DIO0=2
  LoRa.setPins(10, 9, 2);

  // Initialize at 868 MHz (Europe) or 915 MHz (US)
  if (!LoRa.begin(868E6)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }
}

void loop() {
  LoRa.beginPacket();
  LoRa.print("Hello from Malskill");
  LoRa.endPacket();
  delay(10000);
}
```

## 4. Spreading Factor (SF)
You can tune the signal using `LoRa.setSpreadingFactor(sf)`. 
- **SF7**: Faster transmission, shorter range, less power consumption.
- **SF12**: Ultra-slow transmission, maximum range, punches through buildings.
