[中文](README.md) | [English](README.en.md)

# ROS 2空间定位与三维显示

启动方法统一见[项目说明](../README.md)。本目录负责共享相机启动编排、RTAB定位、里程计桥接和两个RViz窗口的配置。

## 坐标与话题

```text
map
├── odom → camera_link → camera_color_optical_frame → hand_1 / hand_2
└── camera_start
```

只启动手部跟踪时不需要map/odom；RViz固定在 `camera_color_optical_frame`。相机运动视图固定在 `camera_start`，其位置和朝向来自首次有效map相机位姿。两种视图互不改变对方的输出坐标。

| 话题 | 内容 |
|---|---|
| `/camera/camera/color/image_raw` | 两个功能共享的彩色图 |
| `/camera/camera/color/camera_info` | 对应分辨率和帧的真实内参 |
| `/camera/camera/aligned_depth_to_color/image_raw` | RTAB使用的对齐深度 |
| `/tracking/hex_prism_1/pose`、`/tracking/hex_prism_2/pose` | 相机光学系中的六棱柱位姿 |
| `/tracking/hand_markers` | 手部三维模型、轴和坐标文字 |
| `/rtabmap/odom` | RTAB里程计 |
| `/rtabmap/camera_pose` | 保留里程计header的PoseStamped，通常在odom系 |
| `/rtabmap/camera_motion_markers` | 初始相机参考系中的相机模型与轨迹 |

`motion_view.py` 按位姿时间查询map变换，再转换到初始相机参考系；缺少有效TF时等待，不把odom位姿冒充map位姿。手部TCP和PoseStamped始终保留相机光学坐标，不自动补偿相机移动。

## 模块与参数

- `shared_camera.launch.py`：供两个shell入口使用，只有跟踪分支启动相机。
- `launch_config.py`：构造RealSense及RTAB驱动参数。
- `get_pose.py`：过滤无效/过期里程计，转发位姿并打印位置；保留默认关闭的8889 TCP快照接口，开启后每次连接只返回一次新鲜位姿。
- `motion_scene.py`：初始参考系、相对位姿及有界轨迹采样。
- `motion_view.py`：TF转换、轨迹更新及RViz标记发布。
- `rviz_config.py`：生成两个窗口配置，退出launch时清理临时文件。
- `settings.py` / `config.yaml`：共享配置加载与校验。

`views.hands` / `views.camera` 可设置窗口开关、参考系、标记话题、失效时间、轴长等。轨迹默认最多3000点，每移动0.005米采样一次。更改相机namespace/name时，同时调整话题和光学frame配置。

图像与CameraInfo精确同步，默认超过0.25秒的图像丢弃。相机运动丢失时保留历史轨迹、隐藏当前模型并显示 `TRACKING_LOST`。重启第二终端会重新建立显示原点、清空本次轨迹，但不删除地图。

轨迹为收到位姿时的采样结果，不是回环后重新优化的完整SLAM轨迹；map回环修正可能造成跳变。显示的位移是相对起点的直线距离，不是累计路程。终端文字基于odom，三维视图经map转换，两者在回环后可能不同。

地图默认保存在 `~/.ros/rtabmap.db`，不会自动删除；不要同时让两个RTAB实例打开同一数据库。

## 实机观察

```bash
source /opt/ros/humble/setup.bash
ros2 topic hz /camera/camera/color/image_raw
ros2 topic hz /camera/camera/aligned_depth_to_color/image_raw
ros2 topic echo /tracking/hex_prism_2/pose --once
ros2 topic echo /rtabmap/odom --once --qos-reliability best_effort
```

RViz可拖动旋转、滚轮缩放。左侧TF显示默认关闭，可手动启用查看TF轴。只有手部跟踪时，相机运动窗口没有定位数据属于预期；需要先运行两个终端并等待有效里程计和TF。
