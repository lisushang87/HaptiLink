[中文](README.md) | [English](README.en.md)

# 人手示范采集与坐标输出

按步骤操作：[采集指南](CAPTURE.md) · [机器人遥操作接入](TELEOP.md)。

不控制机器人、不生成机器人action、不上传数据。默认手套原始ADC标为未完成准确性标定。hex_prism_1默认映射left，hex_prism_2映射right：使用前务必确认实物标签/设备UID与左右手的对应关系。位姿是六棱柱中心，不是手腕或机器人末端。

## 启动现有数据源

所有命令在项目根目录，ROS命令终端先运行 `source /opt/ros/humble/setup.bash`。

```bash
# 终端1：共用相机与手部跟踪
bash start_tracking.bash
# 可选终端2：相机移动定位
bash start_rtabmap.bash
# 左手，当前板上默认22路100Hz为921600；端口按实际修改
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 \
  --ros --output /tmp/glove_left_session.jsonl
# 右手另一个终端，不要复用左手端口或日志文件
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB1 --hand right --baud 921600 \
  --ros --output /tmp/glove_right_session.jsonl
```

串口接收器的ROS发布和本地JSONL同时保留，输出文件必须不存在。单手时只运行一份接收器；未接右手会被标记为缺失，不会伪造观测。开启use_sim_time的ROS回放不能混用实时串口壁钟数据。

## 录制episode

```bash
bash start_collection.bash --ros-args -p task:='拿起杯子'
# 另一个终端：开始一段
ros2 service call /human_recorder/start std_srvs/srv/Trigger '{}'
# 做完动作后保存；返回该episode的目录
ros2 service call /human_recorder/stop std_srvs/srv/Trigger '{}'
# 丢弃当前段，或刚停止的上一段（只标记discarded，保留文件可审查）
ros2 service call /human_recorder/discard std_srvs/srv/Trigger '{}'
# 修改下一段的任务名称
ros2 param set /human_recorder task '放下杯子'
```

默认输出到项目 `recordings/日期_随机ID/`，可在启动时通过 `-p output_root:=/绝对路径` 修改。配置见config.yaml，包括主题、左右手映射、队列长度、导出帧率及时间容差。

每段保存原始PNG、带接收时间的events.jsonl、metadata.json。记录图像原始header、CameraInfo、左右手PoseStamped、glove原始JSON/同步日志、Odometry、/tf、/tf_static；段开始复制已收到的静态TF和相机内参。原始图像不降帧；后台有界队列写盘，溢出/写盘错误进入metadata。SIGINT时当前段标为interrupted，不当作正常保存；崩溃时status仍为recording，需人工审查。PNG占空间较大，录制前留足磁盘空间。

保存前不会强制要求双手齐全，适合单手示范；正式数据需先确认同步和标定。保存完成会等待写盘队列排空。不能保证DDS完全无丢包，需结合原始时间戳、手套序号与质量报告检查。

## 质量检查和回放

```bash
/usr/bin/python3 -B -m collection.review recordings/实际episode目录
/usr/bin/python3 -B -m collection.review recordings/实际episode目录 --play
```

回放按图像原始时间戳播放RGB，q退出，需要图形桌面；不会重发ROS消息、更不会控制机器人。报告事件计数、30Hz网格图像缺失及五种观测有效帧数。完整原始信息可重新对齐；回放/导出目前将单个episode的元数据读入内存，建议每段控制在数十秒至数分钟。

## LeRobot观察数据导出

基础Python依赖见根目录`requirements.txt`，ROS消息和`cv_bridge`仍通过apt安装。录制/回放不依赖LeRobot。导出在独立的`.venv-lerobot`中安装，可能下载较大的PyTorch等依赖，需要网络和足够磁盘。系统需python3-venv；图像视频编码依赖环境中的FFmpeg/PyAV支持。不要把LeRobot加入基础requirements或安装进系统ROS Python。

```bash
bash collection/setup_export.bash
.venv-lerobot/bin/python -B -m collection.export \
  recordings/实际episode目录 \
  --output datasets/human_demo_v1 --repo-id local/human-demo
```

输出路径必须不存在；可以同时传多个已保存的episode。不自动上传Hub。适配官方LeRobot 0.4.3的create/add_frame/save_episode/finalize API，参考 https://huggingface.co/docs/lerobot/lerobot-dataset-v3 。当前主机尚未安装LeRobot，实际视频/Parquet读写未端到端验证；导出器已使用测试写入器验证段分割和字段传递。

导出默认30Hz：从实际图像选邻近帧，位置/姿态取容差内最近观测（不是机器人控制指令），手套按各通道时间戳离线插值，不跨序号缺口。缺失图像会结束当前段，后续从新段开始，不把缺失时间压缩进连续段。时钟倒退或坐标frame变化会拒绝导出。时间容差见config.yaml；这些只是匹配限制，不是绝对同步精度保证。

字段：
- observation.images.camera：RGB。
- observation.state：65维，左/右六棱柱相机系位姿各7维(xyz+xyzw)，左/右原始ADC各22维，里程计child在parent中的位姿7维。
- observation.valid：5维，顺序left_pose/right_pose/left_glove/right_glove/odometry；0表示缺失/无效。缺失值是0/单位四元数占位，不能当作测量。
- observation.source_time：统一网格相对原始段首张图像的秒数。精确图像header仍在原始日志。
- task：段开始时的任务名称。

不含action，因此不是开箱即用的机器人ACT训练集。人手ADC不是关节角，里程计child也不一定是光学坐标系；human_provenance.json记录frame及状态布局。TF原始链保留在原始日志，导出当前不把左右手转换成世界坐标。观测缺失掩码必须在后续训练预处理中使用；当前导出不自动丢弃单手或未接手套的帧。原始20Hz手套配默认30ms插值窗口时会有大量无效帧，不能盲目增大窗口掩盖问题。

## 提供给遥操作适配器的ROS坐标节点

```bash
# 相机坐标系中的左右手
bash start_coordinates.bash --ros-args -p movement_enabled:=false
# 或启用RTAB后，输出包含相机移动的odom系位姿
bash start_coordinates.bash --ros-args -p movement_enabled:=true
# 运行时切换。切换会清空缓存并增加mode_epoch，等待新的输入。
ros2 param set /human_coordinates movement_enabled true
ros2 param set /human_coordinates movement_enabled false
```

输出：
| 主题 | 类型 | 含义 |
|---|---|---|
| /teleop/left/pose | geometry_msgs/PoseStamped | 左六棱柱位姿 |
| /teleop/right/pose | geometry_msgs/PoseStamped | 右六棱柱位姿 |
| /teleop/camera/pose | geometry_msgs/PoseStamped | 移动模式下光学相机在world_frame中的位姿 |
| /teleop/movement_enabled | std_msgs/Bool | 是否包含相机移动；不是机器人使能 |
| /teleop/status | std_msgs/String JSON | 各路valid、原因、frame、mode_epoch |

false：默认camera_color_optical_frame，双手相对相机；不发布camera位姿。true：默认odom，通过输入时间戳查询TF，不使用最新TF冒充过去时刻。world_frame可启动时设成其他已有TF坐标系，但map回环可能跳变，默认odom也可能因定位重启跳变。双手不强制成对发布，各自保留来源时间戳。

过期（默认0.25秒）、明显未来时间、非法四元数、缺失TF时不发布该路新坐标，并通过status置valid=false。发布器不会重复发送旧坐标来保持控制；消费者自身也必须检查时间戳和超时。world_frame/camera_frame/max_age_s/future_tolerance_s为启动时参数；movement_enabled可运行时切换。

**这不是机器人控制器或安全使能节点。** 消费者必须实现人手到机器人基座/末端的标定、尺度/工作空间映射、限速限位、失联停止、独立急停和显式使能。movement_enabled只选择坐标模式。使用前先在仿真或禁用执行器的环境验证，不能把相机系坐标直接作为机器人基座指令。

## 验证范围

合成测试覆盖录制写盘/保存/丢弃，缺帧分段与缺失掩码，导出器接口，旋转平移TF，实时ROS坐标模式切换和过期停止输出。真实相机+双手+RTAB的联合长时间录制尚未实测，LeRobot依赖未安装，不宣称完整数据集已导出通过。
