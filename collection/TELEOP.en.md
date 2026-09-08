[中文](TELEOP.md) | [English](TELEOP.en.md)

# Integrating the pose API with another robot

This project publishes human/camera observations. It does **not** provide a universal robot driver, inverse kinematics or execution enable. Implement a separate robot-specific ROS2 adapter connected to the actual vendor driver/controller. This guide is an integration contract, not executable motion software.

## Start and inspect

Start tracking first; add RTAB for camera motion.

```bash
bash start_coordinates.bash --ros-args -p movement_enabled:=false
# Another sourced ROS terminal:
ros2 topic echo /teleop/left/pose
ros2 topic echo /teleop/status
ros2 param set /human_coordinates movement_enabled true
```

| Topic | Type | Meaning |
|---|---|---|
| /teleop/left/pose, /teleop/right/pose | geometry_msgs/PoseStamped | Prism centers; meters, xyzw quaternion, original time and frame |
| /teleop/camera/pose | geometry_msgs/PoseStamped | Optical camera pose in movement mode; do not compensate hand motion twice |
| /teleop/status | std_msgs/String JSON | stamp_ns, frame_id, mode_epoch, valid, reasons |
| /teleop/movement_enabled | std_msgs/Bool | Coordinate mode, never robot enable |
| /glove/left/sample, /glove/right/sample | std_msgs/String JSON | Optional raw ADC; requires calibration and retargeting |

false defaults to camera_color_optical_frame; true to odom. Read each message header rather than guessing. world_frame and similar parameters are startup-only. Output publishers use the default reliable QoS, depth10. An adapter should avoid accumulating old control targets.

## Adapter and calibration

```text
tracking + optional RTAB → human_coordinates → robot-specific adapter → robot driver/controller
                                             ↑ calibration, enable/clutch, limits, feedback
```

Subscribe to poses and status; obtain fresh robot joint/tool feedback. Relative motion mapping is a useful starting convention. On explicit enable/clutch with valid inputs, capture initial human pose(p_h0,R_h0) and robot end-effector pose(p_e0,R_e0). Let A be a calibrated rotation from human output axes to robot base axes, and s a validated translation scale:

```text
p_target = p_e0 + s * A * (p_h - p_h0)
R_target = A * (R_h * transpose(R_h0)) * transpose(A) * R_e0
```

This specifies one base-expressed relative rotation convention, not a universal robot mapping. Preserve multiplication order; s scales translation only. Verify each axis and rotation in simulation. Absolute mapping requires calibrated base/output-frame and prism/wrist/tool offsets with complete SE(3) composition; renaming an optical frame to base_link or adding a constant is insufficient.

A gripper may use calibrated finger signals mapped to a bounded opening. Dexterous hands require channel zero/range/direction calibration and mechanism-specific retargeting. Raw0–4095 values are not angles; invalid/0xFFFF/unsynchronized/disconnected values must not enter execution targets.

Choose Cartesian poses, velocities or IK/planned joint targets according to the actual controller. Message type and command rate depend on the robot; simply remapping PoseStamped to a command topic is not an integration. Dual arms require coordination and self-collision checks. Hand topics arrive independently and are not guaranteed to be paired in time.

## Required protections

- Start disabled. Independent physical emergency stop and explicit enable/clutch must remain separate from movement_enabled.
- Validate pose and status age, per-hand valid flags and robot feedback freshness. Use an independent watchdog: missing callbacks must still cause a bounded-time stop.
- Validate frame, finite numbers, quaternion and workspace. Stop/re-reference on changed mode_epoch/frame, backward clock or localization discontinuities; never chase a jump automatically.
- Enforce joint limits, velocity/acceleration bounds, collision checks and IK reachability. Reject invalid targets; do not keep sending old commands after lost vision, TF or clock validity.
- The node's default0.25s stale threshold is not a certified robot safety setting. Choose a controller timeout for the real system. A20ms node tick does not guarantee50Hz fresh poses.
- odom can jump on localization restart; map can jump after loop closure. mode_epoch does not detect every localization jump, so the adapter needs independent checks.

Suggested states: DISABLED→ARMED→ACTIVE only after explicit enable and all checks; any failure→STOPPED. Require renewed confirmation/reference before resuming. Use the robot's supported safe-stop mechanism: silence on a command topic does not necessarily stop a robot.

## Validation order

First log/display targets in RViz or simulation with actuators disabled. Test left/right mapping, each axis, scale, initial pose, rotations, occlusion, unplugging, stale status, mode changes and localization restart. Only then should a trained operator test at low speed in a clear workspace with accessible emergency stop.

Human-only demonstrations do not require an adapter. Recording executed robot actions later requires adding actual robot state/action, timestamps and command-latency records; these are not automatically included in the current recorder.
