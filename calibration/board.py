"""One board definition shared by printing and calibration, OpenCV 4.5/4.x."""
from pathlib import Path
import math
import numpy as np
import cv2
import yaml

DEFAULT_BOARD = Path(__file__).with_name('board.yaml')


def load_board(path=DEFAULT_BOARD):
    cfg = yaml.safe_load(Path(path).read_text())
    for key in ('squares_x', 'squares_y'):
        if type(cfg[key]) is not int or cfg[key] < 3:
            raise ValueError(f'{key} 必须为至少3的整数')
    for key in ('square_length', 'marker_length'):
        if not isinstance(cfg[key], (float, int)) or not math.isfinite(cfg[key]) or cfg[key] <= 0:
            raise ValueError(f'{key} 必须为正数（米）')
    if cfg['marker_length'] >= cfg['square_length']:
        raise ValueError('marker_length 必须小于 square_length')
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, cfg['dictionary']))
    if hasattr(cv2.aruco, 'CharucoBoard_create'):
        board = cv2.aruco.CharucoBoard_create(cfg['squares_x'], cfg['squares_y'], cfg['square_length'], cfg['marker_length'], dictionary)
    else:
        board = cv2.aruco.CharucoBoard((cfg['squares_x'], cfg['squares_y']), cfg['square_length'], cfg['marker_length'], dictionary)
        if hasattr(board, 'setLegacyPattern'):
            board.setLegacyPattern(True)
    return cfg, board, dictionary


def board_image(board, cfg):
    size = (cfg['squares_x'] * 200, cfg['squares_y'] * 200)
    if hasattr(board, 'generateImage'):
        return board.generateImage(size, marginSize=0, borderBits=1)
    return board.draw(size, marginSize=0, borderBits=1)


def detect_points(image, board, dictionary):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if hasattr(cv2.aruco, 'CharucoDetector'):
        corners, ids, _, _ = cv2.aruco.CharucoDetector(board).detectBoard(gray)
    else:
        markers, marker_ids, _ = cv2.aruco.detectMarkers(gray, dictionary)
        if marker_ids is None:
            return None
        _, corners, ids = cv2.aruco.interpolateCornersCharuco(markers, marker_ids, gray, board)
    if ids is None or len(ids) < 6:
        return None
    all_points = board.getChessboardCorners() if hasattr(board, 'getChessboardCorners') else board.chessboardCorners
    obj = all_points[ids.flatten()]
    # Reject views whose visible corners lie on one line.
    if np.linalg.matrix_rank(obj[:, :2] - obj[0, :2]) < 2:
        return None
    return obj.astype('float32'), corners.astype('float32')
