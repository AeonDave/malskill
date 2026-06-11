# CH341A 5V data-line modifier

**Load when**: The target SPI flash is 1.8V or 3.3V, and a standard (black) CH341A programmer is used for dumping.

## The hardware bug

The standard black CH341A programmer has a design flaw: the 3.3V/5V jumper only changes the voltage supplied to the `VCC` pin, not the logic level on the `MOSI`, `CLK`, and `CS` data lines. The core IC remains powered at 5V, meaning it pushes 5V logic onto the SPI bus.

**Impact**: This will destroy 1.8V flash chips instantly, and can degrade or damage 3.3V flash chips and parallel SoCs when dumping in-circuit.

## The hardware fix

To safely perform in-circuit flash reads/writes with a CH341A on 3.3V chips:

1. **Cut the 5V trace**: Lift pin 28 (VCC_IN) of the CH341A chip entirely off the pad.
2. **Bridge to 3.3V**: Solder a jumper wire from the lifted pin 28 directly to pin 9 (V3) or to the 3.3V output side of the voltage regulator.

## 1.8V targets

Even with the 3.3V fix above, 1.8V flash chips (often found in newer motherboards and mobile devices) require an additional step.

- **Adapter required**: You must use a dedicated **1.8V SPI adapter** sitting between the CH341A and the SOIC clip/socket. The adapter contains level shifters.
- Attempting to read a 1.8V chip with a 3.3V CH341A will either return garbage or permanently damage the chip matrix.
