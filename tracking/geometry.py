"""Hexagonal prism geometry in the existing body/marker coordinate convention."""
import math
import numpy as np


class PrismGeometry:
    def __init__(self, cfg):
        self.groups = {
            'hex_prism_1': cfg['tags']['hexagon_1_ids'],
            'hex_prism_2': cfg['tags']['hexagon_2_ids'],
        }
        self.ids = set(sum(self.groups.values(), []))
        side = cfg['hexagon']['hexagon_size']
        self.center_offset = side * math.sqrt(3) / 2
        size = cfg['tags']['hexagon_tag_black_size'] / 2
        self.marker_points = np.array([
            [-size, -size, 0], [size, -size, 0],
            [size, size, 0], [-size, size, 0]
        ], dtype=np.float32)
        self.face_rotations = []
        vertices, edges = [], []
        half_height = cfg['hexagon']['hexagon_height'] / 2
        for i in range(6):
            angle = math.radians(i * 60 * cfg['hexagon']['face_direction'])
            c, s = math.cos(angle), math.sin(angle)
            self.face_rotations.append(np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32))
            a = math.radians(30 + i * 60)
            x, z = side * math.sin(a), side * math.cos(a)
            vertices.extend([[x, -half_height, z], [x, half_height, z]])
            top, bottom, next_top = i * 2, i * 2 + 1, ((i + 1) % 6) * 2
            edges.extend([(top, next_top), (bottom, next_top + 1), (top, bottom)])
        self.vertices = np.array(vertices, dtype=np.float32)
        self.edges = edges
        length = cfg['display']['axis_length']
        # Keep the existing display convention (-X, +Y, +Z).
        self.axes = np.array([[0, 0, 0], [-length, 0, 0], [0, length, 0], [0, 0, length]], dtype=np.float32)
