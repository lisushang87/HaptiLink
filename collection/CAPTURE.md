[中文](CAPTURE.md) | [English](CAPTURE.en.md)

# 从开机到保存一段示范

这是“人手＋视频”的采集流程；不需要连接机器人。所有命令从项目根目录执行。每个使用ros2或glove.record --ros的终端先执行`source /opt/ros/humble/setup.bash`。文件名使用新名字，不覆盖已有记录。

## 1. 准备与验收

确认标签尺寸/顺序、相机内参、左右手标签组及板卡UID。默认组0–5为left、6–11为right，端口编号可能因插拔改变。22路通常使用100Hz/921600；1000Hz可尝试用于正式采集，但数据准确性不能保证。相机和手套即使同频也需要时间戳对齐，见[频率说明](../STM32/README.md)。

```bash
/usr/bin/python3 -m serial.tools.list_ports -v
/usr/bin/python3 -B -m tools.check_config
```

留足磁盘空间：原始图像逐帧存PNG。先录10秒小样，确认信号/通道有效，再录正式动作。准备每次动作前的静止阶段，等待手套同步valid；100Hz只表示采样节拍，不保证ADC已标定。

## 2. 分终端启动

终端A：相机、标签跟踪和手部RViz。

```bash
bash start_tracking.bash
```

终端B（可选）：需要相机在环境中的移动路径时启动。普通单目USB相机不能直接使用当前RGB-D链路。

```bash
bash start_rtabmap.bash
```

终端C：左手套。终端D：右手套，端口必须不同。

```bash
# Terminal C
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 --ros --output /tmp/left_session_v1.jsonl
# Terminal D
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB1 --hand right --baud 921600 --ros --output /tmp/right_session_v1.jsonl
```

单手可以只开一份接收器；另一手会标记缺失。若只采视觉可不启动手套，但导出ADC将无效。左右端口/UID需实物核对。不要启用use_sim_time混用实时串口。

终端E：录制服务。

```bash
bash start_collection.bash --ros-args -p task:='拿起杯子'
```

默认存入recordings。可在启动时加`-p output_root:=/绝对路径`。坐标输出节点不是录制前置条件，录制器直接订阅跟踪、手套、里程计和TF。

## 3. 开始、保存与重做

另一个已加载ROS环境的终端：

```bash
ros2 service call /human_recorder/start std_srvs/srv/Trigger '{}'
# Perform one demonstration, then save it.
ros2 service call /human_recorder/stop std_srvs/srv/Trigger '{}'
```

stop返回episode目录。一个episode对应一段连续动作；下一次start创建新段。做错了可执行以下命令标记当前段或刚停止的上一段为discarded（保留文件供审查）：

```bash
ros2 service call /human_recorder/discard std_srvs/srv/Trigger '{}'
ros2 param set /human_recorder task '放下杯子'
```

先stop确认写盘完成，再Ctrl+C退出。正在录制时Ctrl+C会标记interrupted，不能当正常保存段。

## 4. 检查与导出

```bash
/usr/bin/python3 -B -m collection.review recordings/实际episode目录
/usr/bin/python3 -B -m collection.review recordings/实际episode目录 --play
/usr/bin/python3 -B -m glove.report /tmp/left_session_v1.jsonl
```

检查metadata中的状态、队列溢出/写盘错误；检查图像缺帧、左右手有效性、同步有效帧、序号缺口和ADC异常。回放按原时间播放RGB，q退出；不重发ROS或机器人指令。

导出可选，不影响原始数据：

```bash
bash collection/setup_export.bash
.venv-lerobot/bin/python -B -m collection.export recordings/实际episode目录 --output datasets/demo_v1 --repo-id local/human-demo
```

默认30Hz。要随相机输出频率调整，修改collection/config.yaml的fps，保持目标频率不高于有用图像供给并审查有效性；手套保留100Hz，通过逐通道时间戳对齐。容差不是绝对同步误差保证，不应无限放大以掩盖丢帧。

输出包含RGB、两手位姿、两手各22路ADC、里程计和缺失掩码。字段、对齐规则与限制见[模块说明](README.md)。
