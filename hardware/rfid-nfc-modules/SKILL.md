---
name: rfid-nfc-modules
description: "RFID/NFC reading and writing: Mifare Classic, PN532 vs RC522, APDUs, and microcontroller SPI/I2C connections."
---

# rfid-nfc-modules

**Goal**: Read and write 13.56MHz NFC tags (Mifare Classic, NTAG213) and 125kHz RFID fobs using microcontrollers.

## 1. Module Differences

- **RC522**: Strictly 13.56 MHz. Connects via SPI. Restricted 3.3V logic. Good for reading basic UIDs and blocks, but cannot easily emulate cards or read mobile phones.
- **PN532**: 13.56 MHz. Can read, write, and **emulate** cards. Communicates via easily toggled DIP switches for SPI, I2C, or UART (HHSU). Much more robust and widely supported by LibNFC.

## 2. Authentication & Sectors (MIFARE Classic 1K)

A standard Mifare Classic 1K tag has 16 sectors, each with 4 blocks.
- **Block 0 of Sector 0**: Contains the immutable UID and manufacturer data.
- **Block 3 of each Sector**: The "Trailer" block. Stores Key A, Key B, and the access conditions for that sector.
- *Rule*: You must authenticate with the sector's Key A or Key B before you can read or write the data blocks in that sector. The default key shipped from factories is usually `FF FF FF FF FF FF`.

## 3. Programming (Arduino + MFRC522)

```cpp
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9
MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin(); 
  rfid.PCD_Init(); 
}

void loop() {
  // Look for a new card
  if ( ! rfid.PICC_IsNewCardPresent()) return;
  // Verify it has been read
  if ( ! rfid.PICC_ReadCardSerial()) return;

  Serial.print("UID:");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  rfid.PICC_HaltA();
}
```

## 4. OPSEC
- Modern access control systems reject MIFARE Classic due to trivial cloning and nested authentication offline cracking (via Proxmark3). Focus on reading UID for cheap locker systems, but expect DESFire EV1/2/3 for modern corporate badges.
