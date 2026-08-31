[中文](BUILD_LINUX.md) | [English](BUILD_LINUX.en.md)

# Build and flash glove firmware on Ubuntu

Linux and Keil share USER/CMSIS/FWLIB sources. Target: STM32F103C8 (64 KiB Flash, 20 KiB RAM), 8 MHz external crystal and 72 MHz system clock. Verify the actual hardware.

## Install the toolchain

```bash
sudo apt update
sudo apt install --no-install-recommends gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi libnewlib-dev make python3 stlink-tools
```

Use the ARM cross-compiler, not the host gcc. Run commands from the project root, or invoke the build script by absolute path.

## Build the default configuration

```bash
bash STM32/build_linux.bash PROFILE=100 -j4
```

Default: 22 channels at 100 Hz, data baud 921600. The script clears interfering Conda cross-build environment variables and prefers the system toolchain. Output directory: `STM32/src/build/linux/22ch/100/`.

| File | Purpose |
|---|---|
| glove_22ch_100hz.elf | ARM firmware with debug symbols |
| glove_22ch_100hz.hex | Intel HEX address format |
| glove_22ch_100hz.bin | Raw firmware, flash address 0x08000000 |
| glove_22ch_100hz.map | Linker and memory report |

Build checks validate ARM ELF, firmware size, initial stack and TIM2/TIM3/USART1/DMA1_Channel4 interrupt vectors. The linker reserves at least 4 KiB of stack, not a measured worst-case depth. `src/linux/verify_firmware.py` remains part of the build and does not depend on the removed tests directory.

**The build script does not flash hardware.** A successful build still requires programming and hardware checks.

## Flash with ST-Link

Verify MCU, power and SWD wiring: SWDIO→PA13, SWCLK→PA14, shared GND. Use board-appropriate power and normal Flash boot settings for BOOT0. Flashing replaces the installed firmware.

```bash
st-info --probe
st-flash --reset write STM32/src/build/linux/22ch/100/glove_22ch_100hz.bin 0x08000000
```

Check write and verification results. ST-Link is not the data serial interface. USB–TTL needs TX→PA10, RX→PA9, shared GND and compatible 3.3 V logic. Never connect two TX drivers to one RX.

```bash
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 --duration 60 --output /tmp/glove_check_new.jsonl
/usr/bin/python3 -B -m glove.report /tmp/glove_check_new.jsonl
```

Use the actual enumerated port and a new output filename.

## Change the rate

Normally retain 100 Hz raw acquisition and align to video timestamps. Acquisition rate, camera rate and export fps are independent; equal rates do not synchronize acquisition. See [STM32 usage limits](README.en.md).

| Configuration | Build arguments | Baud |
|---|---|---:|
| 22 channels, 20/100/200/400/500 Hz | PROFILE=20/100/200/400/500 (choose one value) | 921600 |
| 22 channels, 500 Hz fast ADC | PROFILE=500 ADC_MODE=fast | 921600 |
| 22 channels, experimental 1000 Hz | PROFILE=1000 ADC_MODE=fast | 1500000 |
| 6 channels, 100 Hz | CHANNELS=6 PROFILE=100 | 115200 |
| 6 channels, 1000 Hz | CHANNELS=6 PROFILE=1000 | 921600 |

Example:

```bash
bash STM32/build_linux.bash PROFILE=200 -j4
```

Normal 22-channel outputs use `src/build/linux/22ch/RATE/`; fast ADC adds `adc_fast/` and the `_adc_fast` filename suffix. Six-channel outputs use `src/build/linux/RATE/`. Flash the correct BIN and update receiver baud accordingly.

Definitions are in `src/USER/glove_config.h`; Linux defaults and allowed profiles are in `src/Makefile`. PROFILE selects both cadence and mux settling delay; do not just remove delay calls. No 30/60 Hz firmware profiles currently exist; they require implementation and validation. For 30/60 fps video, keep the glove at 100 Hz and follow the [capture workflow](../collection/CAPTURE.en.md).

## Clean and use another toolchain

Clean only the selected build configuration:

```bash
bash STM32/build_linux.bash PROFILE=100 clean
bash STM32/build_linux.bash PROFILE=100 -j4
```

Use another toolchain:

```bash
ARM_TOOLCHAIN_BIN=/absolute/path/to/toolchain/bin bash STM32/build_linux.bash PROFILE=100 -j4
```

`CROSS_COMPILE=/absolute/path/to/arm-none-eabi-` is also supported. Normal apt installs need no extra library paths; unpacked Debian toolchains may need NEWLIB_INCLUDE and NEWLIB_LIB. Do not depend on temporary /tmp installations long-term.

Linux uses the GCC medium-density startup; Keil retains ARMCC startup. Only required peripheral sources are linked, but vendor dependencies remain. Linux verification does not establish a fresh Keil build; compiler versions can change image size.
