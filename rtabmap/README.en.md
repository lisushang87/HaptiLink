[中文](README.md) | [English](README.en.md)

# Shared camera, localization and 3D views

Use start_tracking.bash first;start_rtabmap.bash in another terminal for RGB-D localization. Only tracking owns the camera. The hand RViz frame is camera_color_optical_frame. Camera trajectory RViz uses camera_start initialized from the first valid map-frame camera pose.

```text
map
├── odom → camera_link → camera_color_optical_frame → hand_1 / hand_2
└── camera_start
```

|Topic|Content|
|---|---|
|/camera/camera/color/image_raw|Shared RGB|
|/camera/camera/color/camera_info|Matching intrinsics|
|/camera/camera/aligned_depth_to_color/image_raw|Aligned depth|
|/tracking/hex_prism_1/pose,/tracking/hex_prism_2/pose|Camera optical-frame prism poses|
|/tracking/hand_markers|Hand display markers|
|/rtabmap/odom|Odometry|
|/rtabmap/camera_pose|Pose bridge preserving odometry header|
|/rtabmap/camera_motion_markers|Initial-reference camera/trajectory display|

motion_view queries map TF at the pose timestamp;it never relabels odom as map. Tracking TCP/poses remain camera-relative. shared_camera.launch.py owns launch branches;launch_config.py driver settings;get_pose.py validity/age filtering and optional8889TCP snapshots (off by default);motion_scene.py trajectory math;motion_view.py TF/display;rviz_config.py temporary view files;settings.py/config.yaml configuration.

views.hands/camera configure frames,timeouts,markers/windows. Trail defaults:3000points,5mm minimum movement. Update topics/frames together when renaming cameras. Image/CameraInfo synchronization is exact;images older than0.25s are dropped. Lost localization hides the current model while retaining the trail and showing TRACKING_LOST. Restarting the second terminal resets display origin/trail,not the stored map.

The trail records incoming poses,not a globally reoptimized loop-closed path. Map corrections can jump. Displayed displacement is straight-line distance from origin,not cumulative distance. Console odom values may differ from map-transformed display after loop closure. Default map:~/.ros/rtabmap.db;never open the same database in two RTAB instances.

```bash
source /opt/ros/humble/setup.bash
ros2 topic hz /camera/camera/color/image_raw
ros2 topic hz /camera/camera/aligned_depth_to_color/image_raw
ros2 topic echo /tracking/hex_prism_2/pose --once
ros2 topic echo /rtabmap/odom --once --qos-reliability best_effort
```

Rotate/zoom in RViz;TF display can be enabled manually. No camera trajectory without the optional localization source is expected. See[root launch table](../README.en.md).
