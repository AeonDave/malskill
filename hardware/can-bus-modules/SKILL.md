---
name: can-bus-modules
description: "CAN Bus interfacing for automotive/industrial networks using MCP2515 over SPI, baud rates, reading OBD-II frames."
---

# can-bus-modules

**Goal**: Interface microcontrollers with automotive and industrial Controller Area Networks (CAN) using transceivers to read and spoof packets.

## 1. Hardware Stack

- **MCU**: e.g., Arduino or ESP32.
- **Controller**: MCP2515 (Translates SPI from MCU into CAN format). Maintains transmit buffers and acceptance filters.
- **Transceiver**: TJA1050 or MCP2551 (Translates logic-level CAN from the MCP2515 into the differential `CAN_H` and `CAN_L` analog voltages required by the physical bus).
- **Physical Bus**: `CAN_H` and `CAN_L` twisted pair. Requires 120-ohm termination resistors at both ends of the bus.

## 2. Setting Baud Rates & Oscillators

The CAN bus relies entirely on timing. Connecting with the wrong speed brings down the bus (`Error Passive`).
- Standard OBD-II in vehicles uses **500 kbps**.
- Slower comfort buses (doors, windows) might use **125 kbps** or **250 kbps**.
- Make sure you initialize the library with the exact crystal oscillator speed attached to your MCP2515 board (commonly 8 MHz or 16 MHz).

## 3. Standard vs Extended Frames

- **Standard Frame**: 11-bit ID. (e.g., `0x7DF`). Used heavily in standard automotive.
- **Extended Frame**: 29-bit ID. (e.g., `0x18DAF100`). Often seen in heavy duty (J1939) or specialized sensors.
- Payload is always 0 to 8 bytes.

## 4. Code Snapshot (mcp_can library)

```cpp
#include <SPI.h>
#include <mcp_can.h>

const int spiCSPin = 10;
MCP_CAN CAN(spiCSPin);

void setup() {
    Serial.begin(115200);
    // Initialize exactly for 500k baud and 8MHz crystal
    while (CAN_OK != CAN.begin(CAN_500KBPS, MCP_8MHz)) {
        Serial.println("CAN init fail, retry...");
        delay(100);
    }
    Serial.println("CAN init ok!");
}

void loop() {
    long unsigned int rxId;
    unsigned char len = 0;
    unsigned char rxBuf[8];

    if (CAN_MSGAVAIL == CAN.checkReceive()) {
        CAN.readMsgBuf(&rxId, &len, rxBuf);
        Serial.print("ID: "); Serial.print(rxId, HEX);
        Serial.print(" Data: ");
        for(int i = 0; i<len; i++) {
            Serial.print(rxBuf[i], HEX); Serial.print(" ");
        }
        Serial.println();
    }
}
```
