[中文](README.md) | [English](README.en.md)

# 手套二进制数据与时间同步

protocol.py解析CRC、序号、UID、ADC及时间戳；clock.py估计板端到主机时间映射；record.py录制并可发布ROS；report.py统计帧率/丢失/同步；align.py对齐辅助；compare.py用于读数对照。

在项目根目录：

```bash
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 --duration 60 --output /tmp/glove_check_new.jsonl
/usr/bin/python3 -B -m glove.report /tmp/glove_check_new.jsonl
```

双手分别运行，使用不同串口、hand值和输出文件。启用ROS先source /opt/ros/humble/setup.bash，再给record加`--ros`。发布/glove/left/sample和/glove/left/timing，右手对应right。录制服务不会自动打开串口。

先等待同步valid，再开始episode；检查序号缺口、设备missed_ticks/tx_drops/rx_errors、CRC错误和同步年龄。ADC是原始值，不是关节角；RTT/2和拟合残差都不能证明绝对同步误差。详见[采集与对齐说明](../collection/README.md)和[数据采集](../collection/README.md)。
