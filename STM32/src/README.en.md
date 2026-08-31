[中文](README.md) | [English](README.en.md)

# STM32F103C8 sources

One USER source set supports6/22channels and configured rates. Linux ARM GCC is the current build path;the Keil project remains,but Linux testing does not prove a new Keil build.

|Path|Role|
|---|---|
|USER|Acquisition,protocol,timers,glove_config.h|
|CMSIS|Cortex-M/STM32 definitions,clock/startup dependencies|
|FWLIB|Standard peripheral library|
|linux|GCC linker script and firmware validation|
|Makefile|Toolchain,sources,PROFILE and output paths|
|DebugConfig|Keil debugger settings|
|build|Generated ELF/BIN/MAP etc.|

From the project root, run `bash STM32/build_linux.bash PROFILE=100 -j4`. For dependencies, flashing and rate profiles, see the [build guide](../BUILD_LINUX.en.md) and [STM32 guide](../README.en.md). When changing glove_config.h, also check the macros passed by Makefile: command-line definitions can override the header defaults.
