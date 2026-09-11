[中文](README.md) | [English](README.en.md)

# Human observations and coordinate outputs

This module records human demonstrations without controlling a robot, generating robot actions or uploading data. hex_prism_1 maps to left and hex_prism_2 to right by default; verify physical tags, ports and board UIDs. Poses refer to prism centers, not wrists/tools. Raw glove ADC is not accuracy-calibrated by default.

Start with the [capture walkthrough](CAPTURE.en.md). To connect a robot, read the separate [teleoperation integration guide](TELEOP.en.md).

## Sources and episode services

Run start_tracking.bash, optional start_rtabmap.bash, glove.record --ros for each connected hand, and start_collection.bash in separate terminals. Source ROS in terminals using ros2 or the glove publisher. Use different ports/hand labels/new log files for each glove. Live wall-clock serial data cannot be mixed with use_sim_time playback.

```bash
bash start_collection.bash --ros-args -p task:='pick up cup'
ros2 service call /human_recorder/start std_srvs/srv/Trigger '{}'
ros2 service call /human_recorder/stop std_srvs/srv/Trigger '{}'
ros2 service call /human_recorder/discard std_srvs/srv/Trigger '{}'
ros2 param set /human_recorder task 'put down cup'
```

Default output: recordings/date_randomID. Set output_root at startup for another location. config.yaml defines input topics, left/right mapping, queue size, export fps and matching tolerances. The recorder subscribes directly to observations; the coordinate API is optional.

Episodes contain original PNGs, events.jsonl with receive times and metadata.json. They retain Image headers, CameraInfo, hand PoseStamped, raw glove/timing JSON, Odometry, /tf and /tf_static. Known static transforms/intrinsics are copied at episode start. Raw images are not downsampled. The bounded writer queue reports overflow/write errors. Stop drains pending writes; Ctrl+C while recording marks interrupted. A crash can leave recording status and requires review. Discard retains files with discarded status. Missing hands are allowed and never synthesized. DDS loss is not ruled out by successful saving.

## Review and export

```bash
/usr/bin/python3 -B -m collection.review recordings/EPISODE
/usr/bin/python3 -B -m collection.review recordings/EPISODE --play
bash collection/setup_export.bash
.venv-lerobot/bin/python -B -m collection.export recordings/EPISODE --output datasets/demo_new --repo-id local/human-demo
```

Replay follows source image timestamps, q exits, and a graphical desktop is required. It does not publish ROS or robot commands. Reports include event counts, image gaps on the target grid and five observation-validity counts. Episode metadata is loaded into memory; prefer short segments of tens of seconds to a few minutes.

Base Python dependencies are listed in the root `requirements.txt`; ROS messages and `cv_bridge` still come from apt. Recording/review do not require LeRobot. Export installs LeRobot0.4.3 into the separate `.venv-lerobot`, including potentially large PyTorch downloads; python3-venv and suitable FFmpeg/PyAV support are needed. Do not add LeRobot to the base requirements or install it into the system ROS Python. The output path must be new; multiple saved episodes can be supplied. No automatic Hub upload. Real MP4/Parquet export has not been tested end-to-end; a synthetic writer verifies API flow and segmentation.

Default export is30Hz: images and poses use nearby observations within configured tolerances, while glove channels interpolate by channel timestamps without bridging sequence gaps. Missing images split segments rather than compressing elapsed time. Backward clocks or changed coordinate frames reject export. Matching tolerances are not measured absolute clock accuracy.

| Field | Meaning |
|---|---|
| observation.images.camera | RGB image |
| observation.state |65values: left/right camera-frame prism xyz+xyzw (14), left/right22ADC (44), odometry child pose in parent (7) |
| observation.valid |5flags: left_pose/right_pose/left_glove/right_glove/odometry |
| observation.source_time | Grid time in seconds relative to the original first image |
| task | Task label captured at episode start |

Invalid values use zero/identity placeholders, never measurements. Use validity masks in training. human_provenance.json records frames/layout. Original TF remains in raw logs; exported hands are not automatically world-frame poses. There is no action field, so this is not a ready-to-deploy robot ACT dataset.20Hz glove data with a30ms interpolation gap limit yields many invalid observations; do not hide this with arbitrary tolerance increases.

## Coordinate API

```bash
bash start_coordinates.bash --ros-args -p movement_enabled:=false
ros2 param set /human_coordinates movement_enabled true
```

PoseStamped topics: /teleop/left/pose, /teleop/right/pose, /teleop/camera/pose. /teleop/status is String JSON; /teleop/movement_enabled is Bool. false uses camera_color_optical_frame and does not publish camera pose; true uses odom by default with TF queried at the source timestamp. Hands publish independently. Mode changes clear caches and increment mode_epoch. map loop closure and odom restarts may jump.

Stale data (default0.25s), excessive future timestamps, invalid quaternions and missing TF stop new output for that route and set valid=false. Old poses are not repeatedly published. world_frame/camera_frame/max_age_s/future_tolerance_s are startup-only; movement_enabled is runtime-changeable. Consumers need their own freshness checks, enable, watchdog, limits, calibration and emergency stop. The Bool is not robot enable. See [adapter guide](TELEOP.en.md).

Synthetic tests cover saving/discard, PNG writes, gap splitting/masks, exporter calls, TF transforms, mode switches and stale-output stopping. Long real-camera/two-glove/RTAB recording and real LeRobot export remain to be validated.
