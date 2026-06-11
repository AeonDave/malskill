---
name: gsm-lte-modules
description: "GSM, LTE, and NB-IoT module interfacing: SIM800/SIM7000 AT commands, logic shifting, and power constraints."
---

# gsm-lte-modules

**Goal**: Interface cellular modems (SIM800L, SIM7000G, A7670) with microcontrollers to send text messages, perform HTTP(s) requests, or establish PPP TCP/IP bridges.

## 1. Power Requirements (Crucial)

Cellular modems emit bursts of RF transmission that pull **up to 2A peaks**. 
- Connecting the VCC of a SIM800L directly to a 3.3V or 5V pin of an Arduino/Raspberry Pi will cause a **brownout** and infinite reboot loops.
- **Rule**: Use an external 3.7V - 4.2V LiPo battery or a beefy Buck Converter capable of 3A sustained, wired in parallel to the MCU.

## 2. UART and Logic Levels

- Modems usually operate at **2.8V logic**. 
- If using a 5V Arduino, you must use a logic level shifter or a resistor voltage divider on the `RX` pin of the modem string.

## 3. The AT Command Sequence

Modems are driven via serial AT commands. Terminate all commands with `\r\n`.

```text
AT                  // Check communication. Expect: OK
AT+CPIN?            // Check if SIM is unlocked. Expect: +CPIN: READY
AT+CSQ              // Check Signal Quality. (0-31, 99 is no signal).
AT+CGATT?           // Check GPRS attachment. Expect: +CGATT: 1
```

### Making an HTTP GET Request (SIM800)
```text
AT+SAPBR=3,1,"Contype","GPRS"
AT+SAPBR=3,1,"APN","internet"   // Set APN of your carrier
AT+SAPBR=1,1
AT+HTTPINIT
AT+HTTPPARA="URL","http://example.com/api"
AT+HTTPACTION=0                 // 0 = GET
AT+HTTPREAD                     // Read the response payload
AT+HTTPTERM
```

## 4. OPSEC & Triangulation
- Connecting to a cell tower registers the SIM and the module's IMEI on the Mobile Network Operator (MNO) logs.
- The location is known to the MNO via triangulation. 
