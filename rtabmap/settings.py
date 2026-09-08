"""Non-ROS loader for shared pipeline settings."""
from pathlib import Path
import math
import yaml

DEFAULT_SHARED_CONFIG = Path(__file__).with_name('config.yaml')


def load_shared_config(path=DEFAULT_SHARED_CONFIG):
    with Path(path).open(encoding='utf-8') as stream:
        cfg = yaml.safe_load(stream)
    if not isinstance(cfg, dict):
        raise ValueError('ROS共享配置必须是映射')
    for group in ('camera', 'topics', 'tracking', 'rtabmap', 'odometry_bridge'):
        if not isinstance(cfg.get(group), dict):
            raise ValueError(f'缺少共享配置分组: {group}')
    for group, key in [('camera','depth_width'),('camera','depth_height'),('camera','depth_fps'),
                       ('tracking','sync_queue_size'),('rtabmap','topic_queue_size'),('rtabmap','sync_queue_size'),
                       ('odometry_bridge','tcp_port')]:
        value=cfg[group].get(key)
        if type(value) is not int or value <= 0:
            raise ValueError(f'{group}.{key}必须为正整数')
    if cfg['odometry_bridge']['tcp_port'] > 65535:
        raise ValueError('tcp_port超出范围')
    for group,key in [('tracking','max_image_age'),('rtabmap','approx_sync_max_interval'),('odometry_bridge','max_pose_age'),('odometry_bridge','console_interval')]:
        v=cfg[group].get(key)
        if type(v) not in (int,float) or not math.isfinite(v) or v <= 0:
            raise ValueError(f'{group}.{key}必须为正数')
    for key in ('color','camera_info','depth','odometry','pose_prefix','camera_pose'):
        if not isinstance(cfg['topics'].get(key),str) or not cfg['topics'][key].startswith('/'):
            raise ValueError(f'topics.{key}必须是绝对ROS话题名')
    for group,key in [('camera','namespace'),('camera','name'),('rtabmap','namespace'),
                       ('rtabmap','frame_id'),('rtabmap','odom_frame_id'),('odometry_bridge','tcp_host')]:
        if not isinstance(cfg[group].get(key),str) or not cfg[group][key]:
            raise ValueError(f'{group}.{key}必须是非空字符串')
    for group,key in [('rtabmap','visualization'),('odometry_bridge','tcp_enabled'),('odometry_bridge','show_position')]:
        if type(cfg[group].get(key)) is not bool:
            raise ValueError(f'{group}.{key}必须是布尔值')
    if not isinstance(cfg['rtabmap'].get('database_path'),str):
        raise ValueError('database_path必须是字符串')
    views = cfg.get('views', {})
    frames = []
    for name in ('hands', 'camera'):
        view = views.get(name)
        if not isinstance(view, dict) or type(view.get('enabled')) is not bool:
            raise ValueError(f'views.{name}.enabled 必须为布尔值')
        if not isinstance(view.get('topic'), str) or not view['topic'].startswith('/'):
            raise ValueError(f'views.{name}.topic 必须为绝对话题')
        for key in ('stale_timeout', 'axis_length'):
            value = view.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'views.{name}.{key} 必须为正数')
    hands, camera = views['hands'], views['camera']
    if not isinstance(hands.get('hand_frames'), list) or len(hands['hand_frames']) != 2:
        raise ValueError('hand_frames 必须包含两个不同的TF子坐标系')
    frames = hands['hand_frames'] + [hands.get('fixed_frame'), camera.get('world_frame'), camera.get('reference_frame')]
    if any(not isinstance(f, str) or not f or f.startswith('/') or ' ' in f for f in frames):
        raise ValueError('视图TF坐标系名称必须非空且不能以/开头或包含空格')
    if len(set(frames)) != len(frames):
        raise ValueError('手部、世界、相机及初始参考TF名称不能重复')
    for key in ('sample_distance', 'update_rate'):
        value = camera.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'views.camera.{key} 必须为正数')
    if type(camera.get('trail_max_points')) is not int or camera['trail_max_points'] < 2:
        raise ValueError('trail_max_points 至少为2')
    return cfg
