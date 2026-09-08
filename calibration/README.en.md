[中文](README.md) | [English](README.en.md)

# Ordinary camera calibration and print assets

This calibrates a conventional pinhole/color camera: K and five distortion coefficients. It does not set a tabletop origin, perform robot hand–eye calibration or turn monocular imagery into depth. Fisheye lenses require another model.

## Print and measure

Use printable/charuco_board_A4.svg, mounted flat without reflective film. Print A4 at100%, no fit-to-page or headers/footers. The roughly5mm margins require a printer supporting that area; otherwise use larger paper without scaling. Defaults:5×7 squares,40mm square size,20mm black markers,200×280mm active area,DICT_6X6_250. Prism sheets useDICT_4X4_250 and48mm black squares/60mm cut guides; do not confuse them. PNGs lack reliable physical scale; prefer SVG.

```bash
/usr/bin/python3 -B -m tools.generate_calibration_board --output /tmp/board_new
/usr/bin/python3 -B -m tools.generate_aruco_tags --output /tmp/tags_new
```

New directories prevent overwriting prints. Custom board generation/calibration must use the same --board YAML and measured square dimensions. Printed tags require matching tags.hexagon_tag_black_size.

## Capture and solve

Close other camera users. Use system Python with OpenCV aruco,NumPy,PyYAML:

```bash
/usr/bin/python3 -B -m calibration.camera_calibration --device /dev/video0 --width 640 --height 480 --fps 30 --capture-dir calibration/captures_new --output calibration/usb_new.yaml
```

c captures,q solves. At least15valid views are required;20–30varied views can help. Use the actual tracking resolution,crop,lens and focus. Cover center/corners/edges with varied distance and tilt; avoid blurred/repeated views. At least6non-collinear ChArUco corners are needed. Captures save raw images without preview overlays. Lock focus when possible.

Offline recalculation:

```bash
/usr/bin/python3 -B -m calibration.camera_calibration --images calibration/captures_new --output calibration/usb_recomputed.yaml
```

The output must be new. All images must be from the same camera/settings; different sizes are rejected, but users must prevent mixing same-size images from different cameras. Output includes ROS-style width/height,K,D,R,P,per-frame/global reprojection RMS,filenames and board definition. Low fit error alone does not prove physical distance accuracy; validate independently.

## Use the calibration

Copy config.yaml to config_usb.yaml and set camera.backend=opencv,device=/dev/video0,width=640,height=480,fps=30,calibration_file=calibration/usb_new.yaml,serial_number empty. Preserve other sections. Launch with the tracking_config argument described in the shared launch configuration, for example:

```bash
bash start_tracking.bash tracking_config:=config_usb.yaml
```

Keep calibration and stream dimensions consistent. Recalibrate/recheck after lens,focus,crop or resolution changes. RealSense normally supplies matching factory CameraInfo; ordinary USB cameras need measured intrinsics. The current RGB-D RTAB path is not supported by an ordinary single color camera. Metric tag pose also requires the true black marker size.

## Parameter loading and physical verification

The calibration_file path is resolved relative to the tracking configuration file, or may be absolute. Resolution must match; the code neither rescales K automatically nor substitutes fabricated intrinsics.

```bash
/usr/bin/python3 -B -m tools.check_config --tracking-config config_usb.yaml
bash start_tracking.bash tracking_config:="$PWD/config_usb.yaml"
```

The USB node reads raw color frames through OpenCV/V4L2 and publishes Image and CameraInfo with identical timestamps/optical frames. Tracking passes K and D to solvePnP, retaining filtering, TCP and hand RViz. USB timestamps mark software read completion, not hardware exposure; strict synchronization requires an appropriate timestamp-capable driver. Do not undistort first and then apply the original distortion parameters again.

For updates, save a new calibration YAML, validate it, change camera.calibration_file and restart the first terminal. There is no hot reload; retain old calibration files for rollback. RealSense continues to use driver CameraInfo. Updating color K alone does not validate RGB/depth extrinsics or aligned depth.

```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /camera/camera/color/camera_info --once --qos-reliability best_effort
ros2 topic echo /tracking/hex_prism_1/pose --once
```

Verify dimensions/K/D, then test known distances. Z is optical-axis distance; Euclidean range is sqrt(X²+Y²+Z²). A ruler measurement from the camera casing to the tag face is not the prism-center-to-optical-center distance. Ordinary USB cameras support hand tracking only in this pipeline. The RTAB branch rejects an ordinary-camera configuration; using a default RealSense configuration instead will not supply the missing depth. Calibration does not require the old serial/Bluetooth scripts or start robot control.
