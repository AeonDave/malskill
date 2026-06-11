---
name: gps-modules
description: "GPS/GNSS module interfacing: UART baud rates, NMEA sentence parsing, and PPS timing synchronization."
---

# gps-modules

**Goal**: Interface GPS/GNSS receivers (NEO-6M, NEO-M8N, ATGM336H) with microcontrollers to parse location, speed, and precision timing.

## 1. Hardware Connection

- **Interface**: UART / Serial.
- **Default Baud Rates**: Usually 9600 bps (NEO-6M) or 38400 bps (NEO-M8N).
- **Wiring**: `TX (GPS) -> RX (MCU)`, `RX (GPS) -> TX (MCU)`.
- **PPS Pin**: Pulse Per Second. Rises exactly on the UTC second boundary. Essential for NTP stratum-1 servers.

## 2. NMEA Parsing (Arduino/C++)

GPS modules constantly stream ASCII NMEA sentences over UART.
- `$GPRMC`: Minimum Recommended Specific GPS/Transit data (Time, Lat, Lon, Speed).
- `$GPGSV`: Satellites in view.

**Library**: Use `TinyGPSPlus` for easy C++ parsing.

```cpp
#include <TinyGPS++.h>
#include <SoftwareSerial.h>

TinyGPSPlus gps;
SoftwareSerial gpsSerial(4, 3); // RX=4, TX=3

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(9600);
}

void loop() {
  while (gpsSerial.available() > 0) {
    if (gps.encode(gpsSerial.read())) {
      if (gps.location.isValid()) {
        Serial.print("Lat: "); Serial.println(gps.location.lat(), 6);
        Serial.print("Lng: "); Serial.println(gps.location.lng(), 6);
      }
    }
  }
}
```

## 3. Antenna & Cold Starts
- **Cold Start**: A GPS module without a battery backup can take 30s to 5 minutes to get a "fix" on satellites.
- Always test GPS devices outside or near a large window. Concrete buildings block the faint L1-band signals completely.
