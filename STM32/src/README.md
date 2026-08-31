[中文](README.md) | [English](README.en.md)

# STM32F103C8固件源码

同一套USER源码支持6路/22路和不同采样配置。当前推荐Linux ARM GCC构建；保留Keil工程用于原IDE开发，但Linux验证不代表Keil也已重新验证。

| 目录/文件 | 作用 |
|---|---|
| USER | 应用、采样、串口协议、定时器与glove_config.h配置 |
| CMSIS | Cortex-M/STM32定义、系统时钟与启动代码 |
| FWLIB | STM32标准外设库依赖 |
| linux | GCC链接脚本和产物校验工具 |
| Makefile | 工具链、源文件、PROFILE和输出路径 |
| DebugConfig | Keil调试器配置 |
| build | 自动生成的ELF/BIN/MAP等，可重新构建 |

从项目根目录运行`bash STM32/build_linux.bash PROFILE=100 -j4`。完整依赖、烧录和档位见[构建文档](../BUILD_LINUX.md)与[STM32说明](../README.md)。修改glove_config.h时也要检查Makefile传入宏；命令行宏可能覆盖头文件默认值。

