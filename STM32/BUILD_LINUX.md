[中文](BUILD_LINUX.md) | [English](BUILD_LINUX.en.md)

# Ubuntu编译与烧录手套固件

Linux构建和Keil工程共用USER/CMSIS/FWLIB源码。目标为STM32F103C8（64KiB Flash、20KiB RAM），外部晶振8MHz，系统时钟72MHz；请核对实物。

## 安装工具链

```bash
sudo apt update
sudo apt install --no-install-recommends gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi libnewlib-dev make python3 stlink-tools
```

使用ARM交叉编译器，不能用电脑本机的普通gcc。以下命令从项目根目录执行；也可使用构建脚本绝对路径。

## 编译默认配置

```bash
bash STM32/build_linux.bash PROFILE=100 -j4
```

默认22路100Hz，数据波特率921600。脚本清理可能干扰交叉编译的Conda环境变量，优先使用系统工具链。输出在`STM32/src/build/linux/22ch/100/`：

| 文件 | 用途 |
|---|---|
| glove_22ch_100hz.elf | 含调试符号的ARM固件 |
| glove_22ch_100hz.hex | Intel HEX地址格式 |
| glove_22ch_100hz.bin | 原始固件，烧录起点0x08000000 |
| glove_22ch_100hz.map | 链接与内存占用 |

构建会校验ARM ELF、固件大小、初始栈和TIM2/TIM3/USART1/DMA1_Channel4中断向量。链接器预留至少4KiB栈空间，不代表实测最大栈深度。`src/linux/verify_firmware.py`属于构建流程，仍然保留；它不依赖已删除的tests目录。

**构建脚本不会烧录设备。** 编译成功后还需烧录和实机检查。

## ST-Link烧录

核对芯片、供电和SWD接线：SWDIO→PA13，SWCLK→PA14，GND共地；按板卡要求供电，BOOT0设置为正常Flash启动。烧录会替换板上固件。

```bash
st-info --probe
st-flash --reset write STM32/src/build/linux/22ch/100/glove_22ch_100hz.bin 0x08000000
```

检查写入和校验结果。ST-Link不是数据串口；USB-TTL需TX→PA10、RX→PA9、GND共地，信号电平匹配3.3V。不要并接两个TX驱动同一个RX。

```bash
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 --duration 60 --output /tmp/glove_check_new.jsonl
/usr/bin/python3 -B -m glove.report /tmp/glove_check_new.jsonl
```

端口以实际枚举结果为准，输出使用新文件名。

## 更改频率

常规使用100Hz原始采样，再按视频时间戳对齐。采样频率、相机频率和导出fps是三个独立设置；同频不等于同步。使用限制见[STM32说明](README.md)。

| 配置 | 构建参数 | 波特率 |
|---|---|---:|
| 22路20/100/200/400/500Hz | PROFILE=20/100/200/400/500（选一个数值） | 921600 |
| 22路500Hz快速ADC | PROFILE=500 ADC_MODE=fast | 921600 |
| 22路1000Hz实验档位 | PROFILE=1000 ADC_MODE=fast | 1500000 |
| 6路100Hz | CHANNELS=6 PROFILE=100 | 115200 |
| 6路1000Hz | CHANNELS=6 PROFILE=1000 | 921600 |

例如：

```bash
bash STM32/build_linux.bash PROFILE=200 -j4
```

22路普通产物在`src/build/linux/22ch/频率/`；快速ADC增加`adc_fast/`目录及`_adc_fast`文件名后缀；6路产物在`src/build/linux/频率/`。选择正确BIN重新烧录，并同步修改接收端波特率。

参数定义在`src/USER/glove_config.h`，Linux默认值和支持列表在`src/Makefile`。PROFILE同时选择节拍和复用器稳定等待，不要只删除delay。当前没有30/60Hz档位；需要另外实现并验证。视频30/60fps可保持手套100Hz，通过[采集流程](../collection/CAPTURE.md)对齐。

## 清理与自备工具链

只清理所选配置的构建目录：

```bash
bash STM32/build_linux.bash PROFILE=100 clean
bash STM32/build_linux.bash PROFILE=100 -j4
```

使用自备工具链：

```bash
ARM_TOOLCHAIN_BIN=/absolute/path/to/toolchain/bin bash STM32/build_linux.bash PROFILE=100 -j4
```

也支持`CROSS_COMPILE=/absolute/path/to/arm-none-eabi-`。正常apt安装不需要额外库路径；自行解压的Debian工具链可能需要NEWLIB_INCLUDE和NEWLIB_LIB。不要长期依赖/tmp临时工具链。

Linux使用GCC的medium-density启动文件，Keil保留ARMCC版本。仅链接所需外设源文件，但供应商依赖仍保留。Linux编译验证不代表Keil也已重新编译验证；不同编译器的镜像大小可能不同。
