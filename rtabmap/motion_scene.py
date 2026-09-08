"""Camera trajectory relative to its first world pose; pure numerical state."""
from collections import deque
import numpy as np


class CameraTrajectory:
    def __init__(self, max_points=3000, sample_distance=.005):
        self.max_points, self.sample_distance = max_points, sample_distance
        self.reset()

    def reset(self):
        self.origin = self.origin_rotation = self.latest = self.last_stamp = None
        self.points = deque(maxlen=self.max_points)

    def update(self, position, rotation, stamp):
        if self.last_stamp is not None and stamp < self.last_stamp:
            self.reset()
        first = self.origin is None
        if first:
            self.origin = np.asarray(position).copy()
            self.origin_rotation = np.asarray(rotation).copy()
        relative_pos = self.origin_rotation.T @ (position - self.origin)
        relative_rot = self.origin_rotation.T @ rotation
        if not self.points or np.linalg.norm(relative_pos - self.points[-1]) >= self.sample_distance:
            self.points.append(relative_pos.copy())
        self.latest = (relative_pos, relative_rot)
        self.last_stamp = stamp
        return first
