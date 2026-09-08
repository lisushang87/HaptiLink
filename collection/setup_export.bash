#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
/usr/bin/python3 -m venv "$project_dir/.venv-lerobot"
"$project_dir/.venv-lerobot/bin/python" -m pip install 'lerobot==0.4.3' pyyaml
