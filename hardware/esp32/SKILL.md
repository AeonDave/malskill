---
name: esp32
description: "ESP32 programming: Wi-Fi/BLE integration, GPIO muxing, FreeRTOS tasks, and power management."
---

# esp32

**Goal**: Develop embedded applications on ESP32 MCUs, utilizing its dual-core CPU, Wi-Fi/BLE radios, and advanced peripheral matrix.

## 1. Hardware Overview

- **Voltage**: **3.3V Logic**.
- **ADC**: Dual 12-bit ADCs, but ADC2 cannot be used while Wi-Fi is active.
- **Strapping Pins**: Pins 0, 2, 5, 12, 15 must be at specific logic levels during boot. Avoid using them for inputs if possible.
- **Muxing**: Almost any GPIO can be assigned to hardware I2C, SPI, or UART using the ESP32 matrix.

## 2. Radio & Network (Arduino Core)

```cpp
#include <WiFi.h>

void setup() {
  WiFi.mode(WIFI_STA);
  WiFi.begin("SSID", "PASSWORD");
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
}
```

## 3. FreeRTOS Tasks

ESP32 runs FreeRTOS by default. Avoid blocking `loop()`; instead, spawn isolated tasks (especially to pin 0 vs pin 1).

```cpp
void myTask(void * parameter) {
  for(;;) {
    // Task logic
    vTaskDelay(100 / portTICK_PERIOD_MS); 
  }
}

void setup() {
  xTaskCreatePinnedToCore(
    myTask,   /* Function to implement the task */
    "Task1",  /* Name of the task */
    10000,    /* Stack size in words */
    NULL,     /* Task input parameter */
    1,        /* Priority of the task */
    NULL,     /* Task handle */
    0);       /* Core where the task should run */
}
```

## 4. OPSEC & Deployments
- Avoid writing raw credentials to flash without NVS encryption if physical extraction is a threat.
- Deep Sleep reduces draw to ~10µA. Wake via RTC GPIO or Timer.
