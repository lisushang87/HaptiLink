"""Load and validate configuration before opening any hardware or sockets."""
import math
from pathlib import Path
import cv2
import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'config.yaml'


def load_config(path=DEFAULT_CONFIG):
    with Path(path).open(encoding='utf-8') as stream:
        cfg = yaml.safe_load(stream)
    validate_config(cfg)
    return cfg


def validate_config(cfg):
    if not isinstance(cfg, dict):
        raise ValueError('配置必须是 YAML 映射')

    def get(path):
        value = cfg
        for key in path.split('.'):
            if not isinstance(value, dict) or key not in value:
                raise ValueError(f'缺少配置: {path}')
            value = value[key]
        return value

    def number(path, minimum=0, inclusive=False, integer=False):
        value = get(path)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or (integer and not isinstance(value, int))
                or (value < minimum if inclusive else value <= minimum)):
            raise ValueError(f'无效数值配置: {path}={value!r}')
        return value

    camera = get('camera')
    if camera.get('backend', 'realsense') not in ('realsense', 'opencv'):
        raise ValueError('camera.backend 只支持 realsense/opencv')
    if camera.get('backend') == 'opencv':
        if not isinstance(camera.get('calibration_file'), str) or not camera['calibration_file'].strip():
            raise ValueError('普通相机需要camera.calibration_file，不能使用占位内参')
        device = camera.get('device', '/dev/video0')
        if not ((isinstance(device, str) and device) or (type(device) is int and device >= 0)):
            raise ValueError('camera.device必须为设备路径或非负整数')

    for path in ('camera.width', 'camera.height', 'camera.fps', 'display.line_thickness'):
        number(path, integer=True)
    for path in ('tags.hexagon_tag_black_size', 'hexagon.hexagon_size',
                 'hexagon.hexagon_height', 'display.axis_length', 'update.interval',
                 'filter.reset_after', 'tcp_server.send_timeout'):
        number(path)
    for name in ('position', 'rotation'):
        number(f'filter.{name}.min_cutoff')
        number(f'filter.{name}.beta', inclusive=True)
        number(f'filter.{name}.d_cutoff')
    if number('tcp_server.port', integer=True) > 65535:
        raise ValueError('tcp_server.port 不能超过65535')
    if get('hexagon.face_direction') not in (-1, 1) or isinstance(get('hexagon.face_direction'), bool):
        raise ValueError('hexagon.face_direction 必须为 1 或 -1')
    for path in ('tcp_server.enabled', 'display.enabled', 'display.show_markers',
                 'display.show_axes', 'display.show_prism', 'display.show_info'):
        if not isinstance(get(path), bool):
            raise ValueError(f'{path} 必须为 true/false')
    for path in ('camera.serial_number', 'tcp_server.host', 'display.window_name'):
        if not isinstance(get(path), str):
            raise ValueError(f'{path} 必须为字符串')
    if not get('tcp_server.host') or not get('display.window_name'):
        raise ValueError('TCP host 和窗口名称不能为空')
    dictionary = get('tags.dictionary')
    if not isinstance(dictionary, str) or not dictionary.startswith('DICT_') or not hasattr(cv2.aruco, dictionary):
        raise ValueError(f'不支持的 ArUco 字典: {dictionary}')
    size = len(cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary)).bytesList)
    ids = []
    for group in ('hexagon_1_ids', 'hexagon_2_ids'):
        values = get(f'tags.{group}')
        if not isinstance(values, list) or len(values) != 6:
            raise ValueError(f'tags.{group} 必须包含按侧面顺序排列的6个ID')
        if any(type(v) is not int or not 0 <= v < size for v in values):
            raise ValueError(f'tags.{group} 的ID必须在0～{size - 1}之间')
        ids.extend(values)
    if len(set(ids)) != 12:
        raise ValueError('两组六棱柱的12个标签ID必须互不重复')
    for name in ('prism_1_color', 'prism_2_color'):
        color = get(f'display.{name}')
        if not isinstance(color, list) or len(color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
            raise ValueError(f'display.{name} 必须为3个0～255的BGR整数')
