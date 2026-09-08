"""Validated ROS-format monocular calibration, independent of ROS imports."""
from pathlib import Path
import numpy as np
import yaml


def load_calibration(path, width, height):
    cfg = yaml.safe_load(Path(path).read_text())
    if (cfg['image_width'], cfg['image_height']) != (width, height):
        raise ValueError('标定分辨率与图像不同；请使用相同档位重新标定，不自动缩放内参')
    K = np.asarray(cfg['camera_matrix']['data'], dtype=float).reshape(3, 3)
    D = np.asarray(cfg['distortion_coefficients']['data'], dtype=float)
    if cfg['distortion_model'] != 'plumb_bob' or D.shape != (5,):
        raise ValueError('普通相机接入目前只支持plumb_bob五参数模型；鱼眼需单独适配')
    if not np.isfinite(K).all() or not np.isfinite(D).all() or K[0, 0] <= 0 or K[1, 1] <= 0:
        raise ValueError('标定参数包含无效数值')
    if not np.allclose(K[2], [0, 0, 1]) or not np.isclose(K[0, 1], 0) or not np.isclose(K[1, 0], 0):
        raise ValueError('内参矩阵格式错误')
    return K, D


def calibration_data(width, height, K, D, rms, errors):
    P = np.zeros((3, 4)); P[:, :3] = K
    def matrix(a):
        a = np.asarray(a)
        return {'rows': a.shape[0], 'cols': a.shape[1], 'data': a.flatten().tolist()}
    return {'image_width': width, 'image_height': height, 'camera_name': 'usb_camera',
            'camera_matrix': matrix(K), 'distortion_model': 'plumb_bob',
            'distortion_coefficients': matrix(np.asarray(D).reshape(1, 5)),
            'rectification_matrix': matrix(np.eye(3)), 'projection_matrix': matrix(P),
            'calibration_quality': {'rms_pixels': float(rms), 'per_view_rms_pixels': list(map(float, errors)), 'views': len(errors)}}
