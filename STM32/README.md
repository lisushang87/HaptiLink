[中文](README.md) | [English](README.en.md)

# 手套硬件与固件

## 正式采集如何选频率

常规采集使用22路100Hz（921600 baud），按相机时间戳对齐数据。**22路1000Hz可尝试用于正式采集，但数据准确性不能保证。**

数据集通常按相机频率或任务所需频率输出。区分三个频率：STM32原始采样频率、相机实际图像频率、collection/config.yaml中的导出fps。**同频不等于同一时刻采样**，仍需板端时间戳、时钟映射和逐通道对齐。

当前22路固件仅支持20/100/200/400/500/1000Hz，没有30或60Hz档位。若相机为30/60fps，现阶段保持手套100Hz，导出时设fps为30或60（需实际图像足够、重新核对时间容差与有效性）。修改导出fps不会改相机或固件，也不会恢复缺失的观测。视觉位姿另受update.interval节流，当前0.02秒，不能假定60fps视频就有60Hz独立位姿。

如果要让板子真正以30/60Hz采样，需要另行增加Makefile和glove_config.h支持、核对定时器周期及模拟稳定时间，再编译、烧录和实测。本次文档整理没有新增这些固件档位。优先按[采集流程](../collection/CAPTURE.md)使用100Hz原始数据对齐视频。


当前业务源码在[src/USER](src/USER/)，Linux构建入口为build_linux.bash。默认22路100Hz，921600 baud。不是原先延时333ms的文本发送程序。

| 内容 | 如何使用 |
|---|---|
| [BUILD_LINUX.md](BUILD_LINUX.md) | 安装ARM GCC、配置编译、ST-Link烧录和故障排查 |
| [PCB](PCB/README.md) | 原理图、BOM、PCB、Gerber与设计源文件 |
| bluetooth.py | 两个HC-05的USB-TTL AT配置与配对 |
| serialport_data_get.py | 历史文本协议/机器人SDK控制脚本，新固件不使用 |

在项目根目录：

```bash
bash STM32/build_linux.bash PROFILE=100 -j4
st-info --probe
st-flash --reset write STM32/src/build/linux/22ch/100/glove_22ch_100hz.bin 0x08000000
```

先核对目标芯片、SWD接线及供电。烧录会替换板上固件。切换频率通过PROFILE；200/400/500等参数和对应波特率见[主说明](../README.md#自己切换帧率)。1000Hz需设置ADC_MODE=fast，接收端使用1500000波特率。

不要仅删除delay：PROFILE同时影响采样周期和模拟复用器稳定等待，TIM2记录时间、TIM3调度采集。使用glove.record/glove.report检查实物，时钟同步在采样运行中进行，不需要停采样。

蓝牙先运行`/usr/bin/python3 STM32/bluetooth.py --list`，核对端口，再按主README进入AT配对。AT模式速率与数据速率不同。优先有线验证，不能把有线吞吐视为无线保证。
