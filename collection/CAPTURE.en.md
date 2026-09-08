[中文](CAPTURE.md) | [English](CAPTURE.en.md)

# Capture a human demonstration, step by step

No robot is required. Run commands from the repository root. Source /opt/ros/humble/setup.bash in every terminal using ros2 or glove.record --ros. Use new output names.

## Prepare

Verify printed tag size/order, camera intrinsics, physical left/right tag groups and board UIDs. IDs0–5 map to left by default;6–11 to right. Serial numbering can change. The usual setting is 22 channels at 100 Hz / 921600 baud; the 1000 Hz configuration may be tried for production data collection, but data accuracy cannot be guaranteed. Equal frame rates do not ensure synchronized acquisition; see the [rate guidance](../STM32/README.en.md).

```bash
/usr/bin/python3 -m serial.tools.list_ports -v
/usr/bin/python3 -B -m tools.check_config
```

Reserve enough disk space for raw PNGs. Record a10-second pilot before real demonstrations. Wait for valid glove clock mapping and check sensors;100Hz is not an analog accuracy certificate.

## Start separate terminals

Terminal A:

```bash
bash start_tracking.bash
```

Optional terminal B, if camera motion is needed:

```bash
bash start_rtabmap.bash
```

The current RTAB pipeline requires RGB-D, not just an ordinary monocular camera. Terminal C and D use distinct glove ports:

```bash
# Terminal C
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 --ros --output /tmp/left_session_v1.jsonl
# Terminal D
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB1 --hand right --baud 921600 --ros --output /tmp/right_session_v1.jsonl
```

One hand is allowed; the other remains missing. For vision-only capture, omit the glove receivers, but ADC observations will be invalid. Do not mix live serial clocks with use_sim_time.

Terminal E:

```bash
bash start_collection.bash --ros-args -p task:='pick up cup'
```

The default output is recordings; optionally add `-p output_root:=/absolute/path` at startup. The coordinate API node is not required for recording: the recorder directly subscribes to tracking, gloves, odometry and TF.

## Start, save and repeat

In another ROS terminal:

```bash
ros2 service call /human_recorder/start std_srvs/srv/Trigger '{}'
# Perform one continuous demonstration.
ros2 service call /human_recorder/stop std_srvs/srv/Trigger '{}'
```

stop returns the episode directory and waits for queued writes. The next start creates another episode. To reject the active or most recently stopped episode, or change the next task:

```bash
ros2 service call /human_recorder/discard std_srvs/srv/Trigger '{}'
ros2 param set /human_recorder task 'put down cup'
```

Discard marks files for review rather than deleting them. Stop successfully before Ctrl+C; quitting while recording marks the episode interrupted.

## Review and export

```bash
/usr/bin/python3 -B -m collection.review recordings/EPISODE
/usr/bin/python3 -B -m collection.review recordings/EPISODE --play
/usr/bin/python3 -B -m glove.report /tmp/left_session_v1.jsonl
```

Inspect metadata status/write errors/overflow, image gaps, hand validity, clock validity, sequence gaps and ADC anomalies. Replay follows original RGB timing; q exits. It does not replay ROS or robot commands.

Optional export:

```bash
bash collection/setup_export.bash
.venv-lerobot/bin/python -B -m collection.export recordings/EPISODE --output datasets/demo_v1 --repo-id local/human-demo
```

Default export is30Hz. Set fps in collection/config.yaml to a supported target, such as the actual video rate, and review validity/timing tolerances. Retain100Hz raw glove samples and align per-channel timestamps. Export settings cannot change firmware/camera rates or recover missing observations; broad tolerances do not prove accurate synchronization.

The output contains RGB, two hand poses, 22 ADC channels per hand, odometry and validity masks. See the [module documentation](README.en.md) for fields, alignment rules and limitations.
