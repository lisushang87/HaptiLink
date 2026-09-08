#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/python3 /opt/ros/humble/bin/ros2 launch "$project_dir/rtabmap/shared_camera.launch.py" start_tracking:=true start_rtabmap:=false "$@"
