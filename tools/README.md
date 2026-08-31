[中文](README.md) | [English](README.en.md)

# 离线工具

命令从项目根目录执行，普通工具不需要相机或STM32连接。

| 命令 | 用途 |
|---|---|
| `python3 -B -m tools.check_config` | 校验跟踪/共享相机配置；不验证硬件支持的流组合 |
| `python3 -B -m tools.generate_aruco_tags --output /tmp/tags_new` | 根据config.yaml生成两组标签、A4页及尺寸说明 |
| `python3 -B -m tools.generate_calibration_board --output /tmp/board_new` | 根据calibration/board.yaml生成ChArUco标定板 |

使用系统/usr/bin/python3；各命令`--help`查看完整参数。输出目录必须为新目录。修改标签几何后重新打印并量尺，不能只改配置不改实物。标定板与跟踪标签使用不同字典。

print_svg.py是内部SVG排版辅助模块，不是独立CLI。普通相机标定入口在[calibration](../calibration/README.md)，串口记录在[glove](../glove/README.md)。
