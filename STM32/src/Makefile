# Linux ARM GCC build; the existing Keil project remains independent.
CROSS_COMPILE ?= arm-none-eabi-
CC := $(CROSS_COMPILE)gcc
OBJCOPY := $(CROSS_COMPILE)objcopy
SIZE := $(CROSS_COMPILE)size
CHANNELS ?= 22
PROFILE ?= 100
ifeq ($(CHANNELS),22)
VALID_PROFILES := 20 100 200 400 500 1000
BUILD := build/linux/22ch/$(PROFILE)
TARGET := $(BUILD)/glove_22ch_$(PROFILE)hz
else ifeq ($(CHANNELS),6)
VALID_PROFILES := 100 1000
BUILD := build/linux/$(PROFILE)
TARGET := $(BUILD)/glove_$(PROFILE)hz
else
$(error CHANNELS must be 6 or 22)
endif
ifeq ($(filter $(PROFILE),$(VALID_PROFILES)),)
$(error Unsupported PROFILE for selected CHANNELS)
endif
ADC_MODE ?= normal
ifeq ($(ADC_MODE),fast)
ifneq ($(CHANNELS),22)
$(error ADC_MODE=fast supports CHANNELS=22 only)
endif
BUILD := $(BUILD)/adc_fast
TARGET := $(BUILD)/glove_22ch_$(PROFILE)hz_adc_fast
ADC_FAST := 1
else ifeq ($(ADC_MODE),normal)
ADC_FAST := 0
else
$(error ADC_MODE must be normal or fast)
endif
ifeq ($(CHANNELS)-$(PROFILE)-$(ADC_MODE),22-1000-normal)
$(error 22ch 1000Hz requires ADC_MODE=fast)
endif
CPU := -mcpu=cortex-m3 -mthumb -mfloat-abi=soft
CPPFLAGS := -DGLOVE_ADC_FAST=$(ADC_FAST) -DGLOVE_CHANNELS=$(CHANNELS) -DGLOVE_PROFILE_HZ=$(PROFILE) -DSTM32F10X_MD -DUSE_STDPERIPH_DRIVER -DHSE_VALUE=8000000 -ICMSIS -IFWLIB -IUSER
# Optional only for an unpacked/relocated Debian toolchain. Normal apt installs need neither.
ifneq ($(NEWLIB_INCLUDE),)
CPPFLAGS += -isystem $(NEWLIB_INCLUDE)
endif
CFLAGS := $(CPU) -std=c99 -O2 -g3 -ffunction-sections -fdata-sections -fno-common -Wall -Wextra -MMD -MP
LDFLAGS := $(CPU) -nostartfiles -Tlinux/stm32f103c8.ld -Wl,--gc-sections,-Map=$(TARGET).map,--print-memory-usage
ifneq ($(NEWLIB_LIB),)
LDFLAGS += -L$(NEWLIB_LIB)
endif
SOURCES := USER/main.c USER/stm32f10x_it.c USER/system_stm32f10x.c CMSIS/core_cm3.c \
 FWLIB/misc.c FWLIB/stm32f10x_rcc.c FWLIB/stm32f10x_gpio.c FWLIB/stm32f10x_tim.c \
 FWLIB/stm32f10x_adc.c FWLIB/stm32f10x_dma.c FWLIB/stm32f10x_usart.c
STARTUP := CMSIS/startup/gcc_ride7/startup_stm32f10x_md.s
OBJECTS := $(patsubst %.c,$(BUILD)/%.o,$(SOURCES)) $(BUILD)/startup.o

.PHONY: all clean
all: $(TARGET).elf $(TARGET).hex $(TARGET).bin
	$(SIZE) $(TARGET).elf
	python3 linux/verify_firmware.py --prefix "$(CROSS_COMPILE)" $(TARGET).elf $(TARGET).bin

$(TARGET).elf: $(OBJECTS) linux/stm32f103c8.ld
	$(CC) $(LDFLAGS) $(OBJECTS) -Wl,--start-group -lc -lgcc -Wl,--end-group -o $@

$(BUILD)/%.o: %.c Makefile
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD)/startup.o: $(STARTUP) Makefile
	@mkdir -p $(dir $@)
	$(CC) $(CPU) -g3 -x assembler-with-cpp -c $< -o $@

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD)

-include $(OBJECTS:.o=.d)
