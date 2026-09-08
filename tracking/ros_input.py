"""ROS message validation helpers, testable without a running ROS graph."""
import numpy as np


def camera_model(image, info):
    if (image.width, image.height) != (info.width, info.height):
        raise ValueError('Image与CameraInfo尺寸不一致')
    if not image.header.frame_id or image.header.frame_id != info.header.frame_id:
        raise ValueError('Image与CameraInfo必须使用相同且非空的光学坐标系')
    K = np.asarray(info.k, dtype=float).reshape(3, 3)
    D = np.asarray(info.d, dtype=float)
    if not np.isfinite(K).all() or K[0, 0] <= 0 or K[1, 1] <= 0 or not np.isfinite(D).all():
        raise ValueError('CameraInfo没有有效相机内参')
    if info.distortion_model not in ('plumb_bob', 'rational_polynomial') and np.any(D):
        raise ValueError(f'不支持的非零畸变模型: {info.distortion_model}')
    if not np.any(D):
        D = np.zeros(5)
    elif len(D) not in (4, 5, 8, 12, 14):
        raise ValueError('CameraInfo畸变系数长度不支持')
    return K, D


def stamp_seconds(stamp):
    return stamp.sec + stamp.nanosec * 1e-9
