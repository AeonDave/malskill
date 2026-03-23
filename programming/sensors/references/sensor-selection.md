# Sensor Selection Guide

Use this when choosing sensors for Arduino, ESP32, robotics, home automation, or model-making projects.

## Selection workflow

1. Define the event or quantity to detect:
   - distance
   - presence
   - contact
   - vibration/impact
   - motion/orientation
   - temperature/humidity
   - light
   - gas/smoke
2. Define the environment:
   - noisy people nearby
   - dust, sunlight, vibration
   - indoor vs outdoor
   - battery vs mains
3. Define required response:
   - threshold only
   - continuous measurement
   - fast trigger
   - localization across zones
4. Prefer the simplest sensor that directly measures the thing you care about.

## Practical recommendations by problem

### Detecting impacts / collisions
Prefer:
- piezo discs with protection circuitry
- vibration modules
- accelerometers / IMUs on the structure

Do not default to microphones in noisy environments.
Do not default to ultrasonic distance sensors when the real need is impact intensity.

### Detecting passage through an exit / gate
Prefer, in order:
1. IR break-beam
2. microswitch / lever switch if the mechanics are controlled
3. ToF only when geometry supports it and extra complexity is acceptable

### Human presence / room automation
- PIR for simple motion
- mmWave for fine occupancy when budget/complexity allow
- reed switch / Hall sensor for doors and windows
- temp/humidity sensors for climate logic

### Robotics / model-making
- ToF or ultrasonic for obstacle distance
- IMU for orientation and movement
- wheel encoders for actual motion measurement
- limit switches for reliable end-stop detection

## Sensor choice rules of thumb

- If ambient sound is messy, do not use microphones for event detection unless audio itself is the signal.
- If physical interruption is the event, use break-beam or switch before fancy ranging.
- If the structure feels the event, mount the sensor on the structure, not near the audience.
- If two sensors can solve the job, choose the one with easier calibration and clearer failure modes.

## Output expectations for the agent

When recommending a sensor, include:
- what it measures
- why it fits this environment
- why common alternatives are worse here
- wiring type (analog, digital, I2C, etc.)
- likely tuning/calibration needs

## Distilled source notes

This guidance condenses common recommendations from DIY/robotics sensor guides, smart-home sensor patterns, and agent-skill marketplace descriptions focused on Arduino, IoT, and Home Assistant style binary sensors.