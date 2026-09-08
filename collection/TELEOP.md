[中文](TELEOP.md) | [English](TELEOP.en.md)

# 将坐标输出接入其他机器人

本工程只提供人手/相机观测，**没有通用机器人驱动、逆运动学或执行使能**。不同机器人需单独编写ROS 2适配节点，并连接厂商驱动或经过配置的控制器。以下是接入约定，不是可以直接使机器人运动的程序。

## 1. 开启与查看接口

先启动跟踪；要包含相机移动，再启动RTAB。

```bash
bash start_coordinates.bash --ros-args -p movement_enabled:=false
# In another ROS terminal:
ros2 topic echo /teleop/left/pose
ros2 topic echo /teleop/status
```

移动模式可启动时设true，或运行时切换：

```bash
ros2 param set /human_coordinates movement_enabled true
```

| 话题 | ROS类型 | 适配器如何使用 |
|---|---|---|
| /teleop/left/pose、/teleop/right/pose | geometry_msgs/PoseStamped | 两个六棱柱中心，xyz米、四元数xyzw，header保存来源时刻与坐标系 |
| /teleop/camera/pose | geometry_msgs/PoseStamped | 仅移动模式下的相机光学系位姿；手位姿已包含相机移动时，不要再补偿一次 |
| /teleop/status | std_msgs/String，JSON | 检查stamp_ns、frame_id、mode_epoch、valid、reasons |
| /teleop/movement_enabled | std_msgs/Bool | 坐标模式提示，绝不是机器人使能 |
| /glove/left/sample、/glove/right/sample | std_msgs/String，JSON | 可选手套ADC；须自行标定、重定向到机器人手，不能直接发布JointState目标 |

false默认输出camera_color_optical_frame，true默认输出odom。遵从每条消息的header.frame_id，不靠硬编码猜测。world_frame等参数只能启动时配置。发布器使用深度10的默认可靠QoS；建议适配器只保留最新待处理目标，避免积压控制命令。

## 2. 实现一个独立适配器

适配器订阅位姿与status，获取机器人当前关节/末端反馈，再产生该机器人控制器支持的目标。连接结构：

```text
tracking + optional RTAB → human_coordinates → robot-specific adapter → robot driver/controller
                                             ↑ calibration, enable/clutch, limits, feedback
```

建议先用相对运动映射。在操作者显式按下使能/离合按钮且数据有效时，记录人手起始位姿(p_h0,R_h0)和机器人当前末端位姿(p_e0,R_e0)。令A为人手输出坐标轴到机器人基座轴的标定旋转，s为经过验证的位移缩放：

```text
p_target = p_e0 + s * A * (p_h - p_h0)
R_target = A * (R_h * transpose(R_h0)) * transpose(A) * R_e0
```

这是基座表达的相对旋转映射约定，不是所有机器人的唯一映射。旋转次序必须一致；s只缩放平移。先在仿真逐轴检查方向，再测试旋转。若要绝对映射，应标定基座到输出frame的变换及六棱柱到手腕/工具的刚性偏置，用完整SE(3)变换组合；不能仅给坐标加常量或把光学系改名为base_link。

夹爪可以在完成ADC标定后将确定的手指信号映射为限幅开合值。多指灵巧手需要每路零点、量程、方向及机构重定向，原始0–4095不是角度。0xFFFF/无效同步/断线值不能进入执行目标。

根据机器人接口选择笛卡尔目标、速度目标，或经过IK与轨迹规划的关节目标。ROS消息类型和控制频率由实际驱动决定，不能把本工程PoseStamped随意重映射到机器人指令话题就认为可用。双臂必须有协调控制和自碰撞检查；两只手独立发布，不保证同一时刻成对到达。

## 3. 必须在适配器和控制器落实的保护

- 启动默认禁止执行；物理急停与显式使能/离合独立于movement_enabled。
- 检查位姿时间、status时间和各路valid，机器人反馈也必须新鲜；消息不再到达时，用独立看门狗在限定时间内停止，不能等待下一条回调才发现失联。
- 校验frame、有限值、四元数和工作空间；mode_epoch变化、frame变化、时间倒退或检测到定位跳变时停止并重新建立起始参考，不能自动追赶跳变。
- 检查关节限位、速度/加速度、碰撞和IK可达性；拒绝非法目标。丢失视觉、TF或时钟同步后不得继续发送旧目标维持运动。
- 坐标节点默认0.25秒过期阈值不是机器人安全认证值；控制器超时按实际机器人与任务确定。节点20ms检查一次，不保证输出50Hz，也不保证每路输入持续有数据。
- RTAB里程计重启可能跳变，map回环也可能跳变；mode_epoch只表示节点检测到的模式/时间变化，不替代对所有定位跳变的检查。

建议状态机：DISABLED→（显式使能且全部检查通过）ARMED→ACTIVE；任意失效进入STOPPED，需重新确认和设定参考，不自动恢复运动。停止方式使用机器人厂商支持的安全停止接口，不能假设“停止发布”会让机器人自动停下。

## 4. 验收顺序

先只打印目标或在RViz/仿真显示，执行器保持禁用。验证左右映射、每轴方向、比例、零位、旋转、遮挡、拔线、status超时、模式切换和定位重启。再由熟悉该机器人的人员在急停可达、低速、空旷工作区测试。没有完成这些步骤前，不把数据节点直接接到真实机器人执行口。

记录人手示范时不需要此适配器。如果后续同时记录机器人执行动作，还需增加实际机器人state/action、时间戳和控制延迟记录；当前采集器并未自动包含这些字段。
