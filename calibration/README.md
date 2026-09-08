[中文](README.md) | [English](README.en.md)

# 普通相机标定、参数更新与客户打印

这套标定用于普通针孔/常规镜头的彩色相机，求解内参K和五个畸变系数D；不设置桌面原点，不做机器人手眼标定，也不把单目相机变成深度相机。鱼眼、强广角镜头需要另外适配鱼眼模型。

## 1. 打印标定板和六棱柱标签

可直接给客户以下文件：

- `calibration/printable/charuco_board_A4.svg`：标定板，一张A4。
- `aruco_tags/printable/hand_1_A4.svg`：第一组六棱柱ID 0～5，一张A4。
- `aruco_tags/printable/hand_2_A4.svg`：第二组六棱柱ID 6～11，一张A4。

用浏览器或矢量绘图软件打开SVG打印，设置 **A4、100%/实际大小**，关闭“适应页面”、页眉页脚。若打印预览裁切，使用支持该打印区域的设备，或用更大纸张按100%打印，不能缩小来适应纸张。标定板仅有5毫米左右页边距，务必检查打印机是否支持。

打印后必须用直尺复核：

| 项目 | 默认实际尺寸 |
|---|---|
| 标定板单个棋盘格 | 40×40毫米 |
| 标定板内部ArUco黑色区域 | 20×20毫米 |
| 标定板整个有效区域 | 200×280毫米（5列7行） |
| 六棱柱标签黑色区域 | 48×48毫米，不包括白边 |
| 每个标签的灰色虚线裁剪框 | 60×60毫米，取自hexagon.hexagon_size |

标定板固定在平整硬板上，不可弯曲，避免反光膜。六棱柱标签沿灰色虚线剪下，得到60×60毫米的正方形，内部48毫米码居中，四周各保留6毫米白边。裁剪框随配置中的六棱柱截面边长变化，不随标签黑色区域尺寸变化；请勿沿ArUco黑边裁剪。六棱柱标签保留白色边缘，按各组ID列表的顺序绕侧面贴，所有标签方向保持一致。

原文件 `calibration/charuco_board.png` 已从备份原样恢复。PNG缺少可靠的打印物理尺寸信息，建议客户使用SVG。恢复板子的字典为 **DICT_6X6_250**，而六棱柱是 **DICT_4X4_250**，两者用途不同，不要混用。

如果要调整尺寸或重新生成，在项目根目录执行：

```bash
# 标定板定义来自 calibration/board.yaml
/usr/bin/python3 -B -m tools.generate_calibration_board --output /tmp/new_calibration_board
# 六棱柱标签定义来自 config.yaml 的 tags；同时输出PNG和两页SVG
/usr/bin/python3 -B -m tools.generate_aruco_tags --output /tmp/new_prism_tags
```

输出目录必须尚不存在，防止覆盖旧打印资料。自定义标定板生成与标定必须使用同一份 `--board /path/board.yaml`；打印文件旁会保存生成时的board.yaml。若实际格子尺寸改变，修改用于标定的定义，不能继续使用错误尺寸。换打印标签尺寸后，同步修改跟踪配置 `tags.hexagon_tag_black_size`。

## 2. 普通USB相机采集与标定

关闭占用该设备的跟踪、视频通话、预览程序。在项目根目录使用系统Python；需要OpenCV（含aruco）、NumPy、PyYAML。

下面以设备 `/dev/video0`、实际支持的640×480/30FPS为例；这不是所有相机都支持的保证。设备节点也可使用稳定的 `/dev/v4l/by-id/...` 路径。

```bash
/usr/bin/python3 -B -m calibration.camera_calibration \
  --device /dev/video0 --width 640 --height 480 --fps 30 \
  --capture-dir calibration/captures_usb_v1 \
  --output calibration/usb_640x480_v1.yaml
```

窗口中 `c` 保存一帧，`q` 结束采集并求解。至少15张有效照片，建议20～30张；多拍并不等于精度自动更好。

采集要点：

1. 使用以后跟踪时的分辨率、裁剪/缩放模式、镜头和对焦设置。尽可能锁定对焦；自动对焦变化可能使内参变化。不要只看软件界面请求的分辨率，要确认实际输出。
2. 让标定板覆盖中央、四角和边缘，改变距离、水平/竖直倾角；不要全部正对相机，或重复拍同一姿态。
3. 拍摄时保持板子静止、清晰、曝光适当；角点在预览中以绿色显示。至少6个非共线ChArUco角点才能作为有效照片。
4. 采集的是原图，不能提前去畸变；程序保存原图，预览上的绿色点不会写入标定照片。

如果已有照片，可以离线重新计算，不打开相机：

```bash
/usr/bin/python3 -B -m calibration.camera_calibration \
  --images calibration/captures_usb_v1 \
  --output calibration/usb_640x480_v2.yaml
```

旧结果不会被覆盖，输出文件必须是新文件名。所有照片必须来自同一相机、相同镜头/对焦和分辨率。程序拒绝混用不同尺寸图像；同尺寸但不同相机的图片仍需使用者自行区分。

结果采用ROS CameraInfo常用YAML结构，包含图像宽高、K、D、R、P；另附总体和逐帧重投影RMS（像素）、有效照片名及标定板定义。重投影误差是拟合指标，不能单独证明实际测距准确。检查异常照片、边缘位置与独立已知距离；不要仅为降低训练误差而删除所有边缘或大倾角照片。

## 3. 更新参数并用于六棱柱跟踪

保留原 `config.yaml` 作为RealSense配置，复制一份用于普通相机：

```bash
cp config.yaml config_usb.yaml
```

编辑 `config_usb.yaml` 中的camera分组（其他分组保留）：

```yaml
camera:
  backend: opencv
  device: /dev/video0
  calibration_file: calibration/usb_640x480_v1.yaml
  serial_number: ""
  width: 640
  height: 480
  fps: 30
```

`calibration_file` 相对这份配置文件所在目录解析，也可以填绝对路径。分辨率必须与标定文件一致；代码不自动缩放K，也不使用假内参兜底。

```bash
/usr/bin/python3 -B -m tools.check_config --tracking-config config_usb.yaml
bash start_tracking.bash tracking_config:="$PWD/config_usb.yaml"
```

普通相机节点通过OpenCV/V4L2读原始彩色图，加载YAML并发布具有完全相同时间戳/光学frame的 `Image` 和 `CameraInfo`。六棱柱节点按原有链路读取K、D并传给solvePnP，原来的滤波、TCP和手部RViz窗口继续使用。时间戳为软件读取完成时间，不是硬件曝光时间；高速运动或严格多传感器同步应改用提供硬件时间戳的驱动。

**不要再次对输入图像去畸变后仍使用原始K、D，否则会重复补偿。** 这套普通相机节点输出原图，PnP自行使用畸变参数。

更新标定时，生成新版本YAML，独立验证后修改 `camera.calibration_file`，关闭并重新启动第一终端。运行中不热加载；旧YAML保留便于回退。相机型号、镜头、对焦、裁剪或分辨率变化后，应重新验证或标定。

默认 `config.yaml` 仍为 `backend: realsense`，继续使用RealSense驱动发布的CameraInfo；普通相机YAML不会覆盖其内参。RealSense重新标定及RGB/深度外参更新需另走与驱动一致的流程，不能只替换彩色K就假定深度对齐也正确。

## 4. 验证与限制

```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /camera/camera/color/camera_info --once --qos-reliability best_effort
ros2 topic echo /tracking/hex_prism_1/pose --once
```

检查CameraInfo的宽高、K、D与文件一致，再检查已知距离下的六棱柱中心坐标。Z是光轴方向距离，欧氏距离为sqrt(X²+Y²+Z²)；不能把标签表面到相机外壳的尺量值直接当作六棱柱中心到光学中心的真值。

普通单目相机只支持本项目的手部跟踪。当前RTAB需要彩色和对齐深度；若以同一 `config_usb.yaml` 启动第二终端，程序会明确拒绝。不要单独用默认RealSense配置启动第二终端来绕过限制，它只会等待缺失的深度数据。

原USB/蓝牙脚本与标定无关，不需要运行。标定、采集和视觉验证不启动机器人。

参考：[OpenCV标定图案](https://docs.opencv.org/4.13.0/da/d0d/tutorial_camera_calibration_pattern.html)、[OpenCV标定示例](https://github.com/opencv/opencv/blob/4.x/samples/python/calibrate.py)、[ROS CameraInfo管理](https://docs.ros.org/en/rolling/p/camera_info_manager/)。本项目兼容系统OpenCV 4.5与新版接口，并保持旧标定板图案约定。
