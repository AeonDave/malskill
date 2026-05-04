# Source Coverage

This dedicated skill fills the hardware and embedded gap in the private challenge-solving collection.

## Local and imported coverage used

- Preserved hardware/signal source material: VGA, HDMI TMDS, DisplayPort 8b/10b, analog scanline audio, power side-channel traces, Saleae UART, I2C, WAV UART, USB MIDI, logic-analyzer CSV, and keyboard/LED side channels.
- Preserved peripheral capture material: USB HID mouse/keyboard, LED Morse, Bluetooth RFCOMM, USB MIDI, and framebuffer-style peripheral reconstruction.
- Preserved RF/SDR material: IQ formats, FFT/spectrum inspection, basebanding, filtering, symbol recovery, and QAM-style demodulation.
- Preserved 3D-printing material: binary G-code, compression, metadata, thumbnails, coordinate projection, and printer-video nozzle tracking.
- Preserved hardware-reversing material: HD44780 LCD GPIO reconstruction, RISC-V extension cues, privileged-mode/CSR pivots, and architecture-aware firmware debugging.
- Imported firmware/security material: SPI flash, UEFI, chipsec, flashrom, UEFITool, firmware extraction, boot chain, and hardware-backed persistence analysis.
- Repository skills: `forensic-technique`, `reversing-technique`, `wireless-technique`, `network-technique`, and `hardware/arduino/arduino`.

## Coverage checklist

- [x] Logic analyzer and Saleae/sigrok captures
- [x] UART, I2C, SPI, CAN, JTAG, and SWD pivots
- [x] USB HID, USB MIDI, Bluetooth, and peripheral PCAPs
- [x] HD44780-style LCD GPIO reconstruction and display DDRAM mapping
- [x] RF/SDR/IQ workflows
- [x] Firmware and SPI flash analysis
- [x] RISC-V custom-extension and privileged-mode cues for firmware reversing
- [x] UEFI/BIOS blob triage
- [x] Side-channel traces and acoustic/LED channels
- [x] Display and video signal reconstruction
- [x] CAD, G-code, and 3D-printing artifacts
- [x] 3D printer video nozzle/bed tracking for reconstructing printed text
- [x] Microcontroller/Arduino-oriented bring-up routing

## Explicit non-goals

- No unsafe probing or flashing without explicit isolated-lab context.
- No real device identifiers, workstation-specific paths, or challenge/platform branding.
- No duplicate long tool manuals; tool syntax belongs in dedicated tool skills.
