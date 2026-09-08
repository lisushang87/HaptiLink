[中文](README.md) | [English](README.en.md)

# 六棱柱视觉跟踪

启动入口：在项目根目录执行`bash start_tracking.bash`。配置在根目录config.yaml；相机启动与ROS共享逻辑在rtabmap目录。

| 模块 | 作用 |
|---|---|
| config.py、calibration.py | 配置和相机内参 |
| geometry.py、pose.py | 标签面几何与六棱柱中心位姿 |
| processor.py | 识别和处理流程 |
| one_euro.py、filtering.py | One Euro位置/旋转滤波 |
| ros_node.py、ros_input.py | 图像输入、ROS位姿/TF输出 |
| usb_camera.py | 普通USB相机ROS发布 |
| rendering.py、scene_markers.py | 图像叠加和RViz标记 |
| network.py | 可选TCP输出，历史协议结构保留 |

默认ID0–5与6–11分别对应hex_prism_1/2。输出`/tracking/hex_prism_1/pose`和`/tracking/hex_prism_2/pose`，姿态是六棱柱中心而非手腕。显示左右手映射由collection配置决定。调整滤波beta会改变动态跟随与抖动折中，不能修复贴码/内参错误。

[贴码与启动流程](../README.md)，[相机标定](../calibration/README.md)。不再通过旧main.py启动，不要重复打开同一相机。
