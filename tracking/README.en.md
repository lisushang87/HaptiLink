[中文](README.md) | [English](README.en.md)

# Hexagonal-prism visual tracking

Run `bash start_tracking.bash` from the root;settings are in config.yaml. Shared camera launch logic lives in rtabmap.

|Modules|Role|
|---|---|
|config,calibration|Settings and intrinsics|
|geometry,pose|Tag-face geometry and prism center|
|processor|Detection pipeline|
|one_euro,filtering|Position/rotation smoothing|
|ros_node,ros_input|Image subscriptions,poses/TF|
|usb_camera|Ordinary camera publisher|
|rendering,scene_markers|Overlays and RViz|
|network|Optional legacy-structure TCP output|

IDs0–5/6–11 map to hex_prism_1/2. Pose topics are /tracking/hex_prism_1/pose and2/pose. They represent prism centers,not wrists. collection defines left/right mapping. One Euro beta changes response/jitter tradeoffs,not geometry/calibration errors. See[root workflow](../README.en.md) and[calibration](../calibration/README.en.md). Do not use old main.py or open the camera twice.
