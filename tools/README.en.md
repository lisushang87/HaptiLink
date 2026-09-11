[中文](README.md) | [English](README.en.md)

# Offline tools

Run from the root using /usr/bin/python3;no camera or glove is needed.

For the system ROS environment, install dependencies through apt as documented in the root README. For non-ROS tools only, create a Python virtual environment and run `.venv/bin/python -m pip install -r requirements.txt`; then replace `python3` below with `.venv/bin/python`. The requirements use `opencv-contrib-python` to provide `cv2.aruco`.

|Command|Purpose|
|---|---|
|python3 -B -m tools.check_config|Validate tracking/shared settings,not hardware stream support|
|python3 -B -m tools.generate_aruco_tags --output /tmp/tags_new|Generate configured PNG tags,A4 SVGs and print dimensions|
|python3 -B -m tools.generate_calibration_board --output /tmp/board_new|Generate the configured ChArUco board|

Use --help for options. Output directories must be new. Measure prints and keep physical/configured dimensions consistent. Calibration and tracking dictionaries differ. print_svg.py is an internal layout helper,not a CLI. See[calibration](../calibration/README.en.md) and[serial tools](../glove/README.en.md).
