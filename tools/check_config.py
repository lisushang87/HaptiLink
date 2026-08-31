"""Validate both configuration files without starting ROS or hardware."""
import argparse
from pathlib import Path
from tracking.calibration import load_calibration
from tracking.config import DEFAULT_CONFIG, load_config
from rtabmap.settings import DEFAULT_SHARED_CONFIG, load_shared_config


def main():
    parser = argparse.ArgumentParser(description='离线校验跟踪和空间定位配置')
    parser.add_argument('--tracking-config', default=str(DEFAULT_CONFIG))
    parser.add_argument('--shared-config', default=str(DEFAULT_SHARED_CONFIG))
    args = parser.parse_args()
    cfg = load_config(args.tracking_config)
    camera = cfg['camera']
    if camera.get('backend') == 'opencv':
        path = Path(camera['calibration_file']).expanduser()
        if not path.is_absolute():
            path = Path(args.tracking_config).resolve().parent / path
        load_calibration(path, camera['width'], camera['height'])
    load_shared_config(args.shared_config)
    print('两份配置校验通过；此检查不验证硬件支持的分辨率和帧率。')


if __name__ == '__main__':
    main()
