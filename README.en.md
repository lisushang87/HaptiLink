[中文](README.md) | [English](README.en.md)

# Dual-hand demonstration capture and hexagonal-prism tracking

| Hand-mounted prism tracking | Camera motion and localization |
|:---:|:---:|
| ![Hand-mounted prism tracking](doc/media/tracking-demo.gif) | ![Camera motion and localization](doc/media/movement-demo.gif) |

Live demonstrations: left, ArUco prism detection and camera-frame hand poses; right, camera motion and 3D coordinates relative to its initial pose. The clips were recorded independently and are not synchronized. Together with STM32 glove data, the project records human demonstrations and publishes ROS 2 poses for external robot adapters.

This project combines ArUco prisms, STM32 sensor gloves and ROS 2. It provides one/two-hand visual poses, optional RGB-D camera localization, timestamped glove measurements, demonstration episodes and pose topics for external teleoperation adapters.

The tracked point is the prism center, not the wrist or robot tool. Glove values are raw ADC counts, not joint angles. This project does not command a robot. 

![Printed parts](doc/pictrue/enhanced/04-printed-parts.png)

Only the latest seven retouched photographs are retained in the [image directory](doc/pictrue/enhanced/). Photos are illustrative; use the original electrical design and measured dimensions for assembly.

## Recommended workflow

Print and measure the parts → print and attach tags → verify camera calibration → build/flash and check the glove → start tracking → optionally start localization → publish glove data → record, review and optionally export an episode.

Run commands from the repository root. Use new output names. Replace placeholder paths and serial ports with actual values.

## Printing and tag placement

[3Dprint](3Dprint/README.en.md) contains STL files: hex-hand.stl (hand prism), handBand.stl (wrist mounting part), hex-hand-camera.stl (camera mounting variant), and hex-robot-arm.stl (robot-side variant). STL does not encode units. Verify fit and scale in your slicer before printing. The robot-side file has raw bounds about12×10.392×6, unlike the hand prism; do not assume all models use the same scale. No load-bearing certification is supplied.

Print [hand 1](aruco_tags/printable/hand_1_A4.svg) and [hand 2](aruco_tags/printable/hand_2_A4.svg) at A4 actual size/100%, with fit-to-page and headers/footers disabled. Measure the result: black outer square48mm; cut guide60×60mm; white margin6mm. Dictionary: DICT_4X4_250. Hand1 uses IDs0–5; hand2 uses6–11. Historical top-level PNGs include unused IDs and are not the current print set.

![Tag order](doc/diagrams/marker_placement.svg)

Center one tag on each outer side face, including along the prism axis. All printed top edges must face the same rim. Looking from that rim toward the opposite end, IDs advance clockwise for the current face_direction=1:0→5 or6→11. Choose the initial face consistently on both assemblies. Do not mirror tags, rotate one tag independently, bridge edges or trim black borders. Keep a stationary prism visible one face at a time: its estimated center/orientation should remain consistent. Update config.yaml if physical geometry changes. See [tag instructions](aruco_tags/README.en.md).

## Environment and camera

The current target is Ubuntu22.04 / ROS2 Humble with /usr/bin/python3. Install/configure ROS2 Humble separately before installing these dependencies; do not mix Conda packages into the ROS system Python.

```bash
sudo apt update
sudo apt install ros-humble-realsense2-camera ros-humble-rtabmap-ros ros-humble-rviz2 \
  ros-humble-cv-bridge ros-humble-message-filters ros-humble-tf2-ros ros-humble-tf2-geometry-msgs \
  python3-opencv python3-numpy python3-scipy python3-yaml python3-serial
source /opt/ros/humble/setup.bash
/usr/bin/python3 -c 'import cv2; print(cv2.__version__); print(hasattr(cv2, "aruco"))'
/usr/bin/python3 -B -m tools.check_config
```

RealSense RGB is requested at424×240/60fps; shared depth settings are in rtabmap/config.yaml. Only the tracking launch owns the camera; other nodes subscribe to the same stream. Intrinsics come from matching CameraInfo. A configuration check cannot guarantee the device supports a stream combination.

For an ordinary USB camera, calibrate at the actual working resolution/focus, then set camera.backend=opencv and the device, size, fps and calibration_file in config.yaml. The current RGB-D localization pipeline cannot run directly on an ordinary monocular camera.

```bash
/usr/bin/python3 -B -m tools.generate_calibration_board --output /tmp/board_new
/usr/bin/python3 -B -m calibration.camera_calibration --device /dev/video0 \
  --width 640 --height 480 --fps 30 --capture-dir calibration/captures_new \
  --output calibration/usb_new.yaml
```

Press c to capture, q to solve. The ChArUco dictionary is DICT_6X6_250, different from prism tags. Recheck calibration after lens, focus, crop or resolution changes. See [calibration](calibration/README.en.md).

## STM32: build, flash and choose a rate

Target: STM32F103C8,64KiB Flash/20KiB RAM,8MHz external crystal and72MHz system clock. Verify the actual board first.

```bash
sudo apt install --no-install-recommends gcc-arm-none-eabi binutils-arm-none-eabi \
  libnewlib-arm-none-eabi libnewlib-dev make stlink-tools
bash STM32/build_linux.bash PROFILE=100 -j4
st-info --probe
st-flash --reset write STM32/src/build/linux/22ch/100/glove_22ch_100hz.bin 0x08000000
```

The build does not flash. Flashing replaces the installed firmware; check the write/verification result. ST-Link SWDIO→PA13, SWCLK→PA14, shared GND, board-appropriate power and normal Flash boot configuration. NRST is optional for some operations; a missing reset wire is unrelated to a missing USB serial port. USB–TTL TX→PA10, RX→PA9, shared GND and compatible3.3V logic. Never connect two TX drivers to the MCU RX.

**Use22-channel100Hz/921600baud as the normal starting point**, then validate your sensors and link. 100Hz also requires analog accuracy validation.

| Build parameters | Baud | Purpose/status |
|---|---:|---|
| PROFILE=20 |921600| Slow relative reference, not ground truth |
| PROFILE=100 |921600| Normal starting configuration |
| PROFILE=200 /400 |921600| Experimental, build-checked |
| PROFILE=500 |921600| Throughput tested, analog accuracy not certified |
| PROFILE=500 ADC_MODE=fast |921600| Independent short ADC-window experiment |
| PROFILE=1000 ADC_MODE=fast |1500000| Experimental; see STM32 usage limits |
| CHANNELS=6 PROFILE=100 |115200| Legacy six-channel baseline |
| CHANNELS=6 PROFILE=1000 |921600| Six-channel experiment, not evidence for22channels |

Append parameters to build_linux.bash, then flash the corresponding image. Normal22-channel images are under src/build/linux/22ch/RATE/. Fast ADC adds adc_fast/ and the _adc_fast filename suffix. Six-channel images are under src/build/linux/RATE/.

Parameters are in src/USER/glove_config.h and Linux defaults/allowed profiles in src/Makefile. PROFILE selects both cadence and multiplexer settling delay. Do not remove waits just to raise throughput. TIM2 timestamps acquisition; TIM3 schedules it.

Sampling at the camera rate does **not** synchronize exposure and ADC. Current22-channel profiles are20/100/200/400/500/1000Hz, not30/60Hz. For30/60fps video, retain100Hz raw glove data and align it to video timestamps; choose export fps in collection/config.yaml. Changing export fps does not change hardware rates or create missing observations. Visual poses are also throttled by update.interval (currently0.02s). True30/60Hz firmware requires another implementation and hardware validation.

See [STM32 guide](STM32/README.en.md), [build instructions](STM32/BUILD_LINUX.en.md), and [PCB](STM32/PCB/README.en.md). U10 sends6channels to PA0; U6/U7 send8each to PB0/PB1. Address lines are PA1/2/3 for U10 and shared PA5/6/7 for U6/U7. Capacitors and source impedance constrain settling time.

## Serial and Bluetooth

```bash
/usr/bin/python3 -m serial.tools.list_ports -v
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 \
  --duration 60 --output /tmp/glove_check_new.jsonl
/usr/bin/python3 -B -m glove.report /tmp/glove_check_new.jsonl
/usr/bin/python3 -B STM32/bluetooth.py --list
/usr/bin/python3 -B STM32/bluetooth.py --master /dev/ttyUSB0 --slave /dev/ttyUSB1 --data-baud 921600
```

Test wired first. For pairing, connect each HC-05 through its own USB–TTL and enter AT mode; AT baud and data baud differ. Accepted AT settings do not prove wireless throughput. Do not run serialport_data_get.py for new firmware: it is historical text-protocol robot-control code.

## Launch only the functions you need

| Function | Command | Prerequisite |
|---|---|---|
| RGB tracking, poses/TF and hand RViz | bash start_tracking.bash | Camera and correctly attached tags |
| Camera localization and trajectory RViz | bash start_rtabmap.bash | Shared RealSense RGB-D already running |
| Camera-relative pose API | bash start_coordinates.bash --ros-args -p movement_enabled:=false | Tracking |
| Motion-inclusive pose API | bash start_coordinates.bash --ros-args -p movement_enabled:=true | Tracking, RTAB and valid TF |
| Episode service | bash start_collection.bash --ros-args -p task:='pick up cup' | Desired data sources |

Scripts source ROS. Other terminals using ros2 or glove.record --ros must source /opt/ros/humble/setup.bash. Optional headless launch: `bash start_tracking.bash show_3d:=false show_window:=false tcp_enabled:=false`. Optional database: `bash start_rtabmap.bash database_path:=/tmp/demo_map.db`. Stop each terminal with Ctrl+C; closing RViz alone does not stop the data source.

## Capture, review and export

Follow the complete [capture checklist](collection/CAPTURE.en.md). Start tracking, optional RTAB, one receiver per glove and the recorder. Each glove uses a different port, hand name and output file.

```bash
source /opt/ros/humble/setup.bash
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 \
  --ros --output /tmp/left_session_new.jsonl
# After starting the recorder in another terminal:
ros2 service call /human_recorder/start std_srvs/srv/Trigger '{}'
ros2 service call /human_recorder/stop std_srvs/srv/Trigger '{}'
/usr/bin/python3 -B -m collection.review recordings/EPISODE
/usr/bin/python3 -B -m collection.review recordings/EPISODE --play
```

The saved episode contains PNGs, events.jsonl and metadata.json: original image headers, CameraInfo, hand poses, glove data/timing, odometry and TF. Missing hands remain invalid. Queue overflow/write failures must be inspected. Stop and wait for saving before quitting; interrupted segments are not normal saved episodes.

```bash
bash collection/setup_export.bash
.venv-lerobot/bin/python -B -m collection.export recordings/EPISODE \
  --output datasets/demo_new --repo-id local/human-demo
```

Export dependencies are isolated and may be large. Real LeRobot MP4/Parquet end-to-end export remains unverified; the adapter has synthetic tests. Default export is30Hz, with image gaps split into separate segments and validity masks retained. This is human observation data, **without robot action**, not a deployable ACT dataset. See [collection details](collection/README.en.md).

## Connect another robot

Use a separate robot-specific adapter, described in [teleoperation integration](collection/TELEOP.en.md). Subscribe to /teleop/left/pose and/or right/pose, plus fresh /teleop/status. PoseStamped uses meters, xyzw quaternions and source timestamps. false mode defaults to camera_color_optical_frame; true mode to odom. /teleop/movement_enabled selects coordinates, not robot enable.

Calibrate axes and offsets, map relative motion, enforce limits/collision checks and use the actual robot controller API. Implement independent enable/clutch, watchdog and emergency stop. Stale data, changed mode_epoch/frame or localization jumps must stop execution and require a new reference. Do not directly remap human poses into an actuator command topic. Start with simulation/disabled actuators.

Glove time is mapped from the board clock; images retain acquisition headers and TF must be queried at the appropriate time. RTT/2 and fit residuals are diagnostics, not measured absolute synchronization error.

## Tools and directory map

```bash
/usr/bin/python3 -B -m tools.check_config
/usr/bin/python3 -B -m tools.generate_aruco_tags --output /tmp/tags_new
/usr/bin/python3 -B -m tools.generate_calibration_board --output /tmp/board_new
```

Generators require new output directories. print_svg.py is an internal helper, not a printing CLI.

| Directory | Purpose |
|---|---|
| [3Dprint](3Dprint/README.en.md) | STL parts and scale checks |
| [aruco_tags](aruco_tags/README.en.md) | Tags and print sheets |
| [STM32](STM32/README.en.md) | Firmware, PCB and Bluetooth |
| [tracking](tracking/README.en.md) | Detection, geometry, filtering, ROS outputs |
| [rtabmap](rtabmap/README.en.md) | Shared camera, localization and RViz |
| [glove](glove/README.en.md) | Protocol, clock mapping, recording and alignment |
| [collection](collection/README.en.md) | Episodes, export and pose API |
| [calibration](calibration/README.en.md) | Camera calibration and board generation |
| [tools](tools/README.en.md) | Offline checks and printing assets |
| [doc](doc/) | Current photos and assembly diagram |

build and __pycache__ are generated; recordings/datasets/.venv-lerobot appear during use. Version-control/development metadata is not required to operate hardware.

## Troubleshooting and limits

Missing ttyUSB: inspect actual ports and ch341/BRLTTY logs rather than assuming port0. Do not remove accessibility services blindly. Invalid serial frames: check firmware baud, wiring, binary protocol and AT/data mode. Camera errors: check device capabilities and competing programs. Pose jumps between faces: check tag sizes/order/orientation and calibration. No teleop pose: inspect status, TF and source age. Missing export observations: inspect source visibility, clock warm-up and gaps rather than filling with stale values. Validate camera→one tag group→one glove→two hands→optional motion→capture in that order.
