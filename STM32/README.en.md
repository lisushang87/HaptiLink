[中文](README.md) | [English](README.en.md)

# Glove firmware and hardware

Application sources are in src/USER; build_linux.bash is the Linux entry point. The default is22channels,100Hz,921600baud, using timestamped binary packets rather than the old333ms text sender.

## Choose a capture rate

Use 22 channels at 100 Hz / 921600 baud for normal capture and align measurements to camera timestamps. **The 22-channel 1000 Hz configuration may be tried for production data collection, but data accuracy cannot be guaranteed.**

The raw glove rate, actual camera rate and export fps are different settings. Equal rates do not synchronize acquisition. Current22-channel firmware supports20/100/200/400/500/1000Hz, not30/60Hz. Keep100Hz glove acquisition and align channel timestamps to video; select a target export fps in collection/config.yaml. Changing export fps does not change the board/camera or recover observations. Visual update.interval currently limits processing cadence to0.02s.

A true30/60Hz board mode needs new Makefile/header support, timer/settling checks, compilation, flashing and hardware validation. It was not added in this documentation update. Follow the [capture guide](../collection/CAPTURE.en.md).

## Build and flash

```bash
bash STM32/build_linux.bash PROFILE=100 -j4
st-info --probe
st-flash --reset write STM32/src/build/linux/22ch/100/glove_22ch_100hz.bin 0x08000000
```

Run from the project root. Verify MCU/SWD/power first; flashing replaces firmware. PROFILE selects cadence and settling delay, not just transmit rate. 1000 Hz requires ADC_MODE=fast and 1500000 receiver baud. TIM2 timestamps, TIM3 schedules; synchronization runs alongside acquisition. Do not simply remove delays.

| File/directory | Purpose |
|---|---|
| [BUILD_LINUX](BUILD_LINUX.en.md) | Toolchain, output paths and programming |
| [PCB](PCB/README.en.md) | Schematic, layout, BOM, fabrication/design files |
| bluetooth.py | Configure/pair two HC-05 modules in AT mode |
| serialport_data_get.py | Historical text-protocol robot-control code; not the current receiver |

Use glove.record/glove.report for current firmware. For Bluetooth, list ports first, identify each module, enter AT mode and follow the root guide. AT/data baud differ; wired results do not prove wireless performance.
