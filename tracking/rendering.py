"""Overlay rendering only; poses arrive in the selected output coordinate frame."""
import cv2
import numpy as np
from tracking.utils import rotation_matrix_to_ypr_y_forward


class Renderer:
    def __init__(self, cfg, geometry, camera_matrix, dist_coeffs):
        self.cfg, self.geometry = cfg, geometry
        self.camera_matrix, self.dist_coeffs = camera_matrix, dist_coeffs

    def _project(self, points, rvec, tvec):
        pixels, _ = cv2.projectPoints(points, rvec, tvec, self.camera_matrix, self.dist_coeffs)
        return pixels.reshape(-1, 2).astype(np.int32)

    def draw(self, frame, markers, poses):
        cfg = self.cfg
        thickness = cfg['line_thickness']
        if cfg['show_markers']:
            for mid, info in markers.items():
                corners = info['corners'].reshape(-1, 2).astype(np.int32)
                cv2.polylines(frame, [corners], True, (0, 255, 255), thickness)
                cv2.putText(frame, str(mid), tuple(corners[0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 255), thickness)
        y = 30
        for i, name in enumerate(self.geometry.groups, 1):
            if name not in poses:
                continue
            position, rotation = poses[name]
            if cfg['show_info']:
                text = f'HexPrism {i}: [{position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}]'
                cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), thickness)
                yaw, pitch, roll = rotation_matrix_to_ypr_y_forward(rotation)
                cv2.putText(frame, f'RPY {i}: [{roll:.2f}, {pitch:.2f}, {yaw:.2f}]',
                            (10, y + 25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), thickness)
                y += 50
            rvec, _ = cv2.Rodrigues(rotation)
            tvec = position.reshape(3, 1)
            if cfg['show_prism']:
                pixels = self._project(self.geometry.vertices, rvec, tvec)
                color = tuple(cfg[f'prism_{i}_color'])
                for a, b in self.geometry.edges:
                    cv2.line(frame, tuple(pixels[a]), tuple(pixels[b]), color, thickness)
            if cfg['show_axes']:
                pixels = self._project(self.geometry.axes, rvec, tvec)
                for end, color in zip(pixels[1:], [(0, 0, 255), (0, 255, 0), (255, 0, 0)]):
                    cv2.line(frame, tuple(pixels[0]), tuple(end), color, thickness + 1)
        if cfg['show_info'] and not poses:
            cv2.putText(frame, 'No prism detected', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), thickness)
        cv2.putText(frame, "Press 'q': quit", (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), thickness)
        return frame
