#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
exec /usr/bin/python3 -B -m collection.coordinates "$@"
