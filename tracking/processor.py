"""RGB processing independent of ROS transport."""
from .geometry import PrismGeometry
from .pose import PoseEstimator
from .filtering import PoseFilters
from .rendering import Renderer


def pose_payload(poses):
    payload = {}
    for i, name in enumerate(('hex_prism_1', 'hex_prism_2'), 1):
        if name in poses:
            position, rotation = poses[name]
            payload[f'cube_{i}'] = {
                'position': dict(zip(('x', 'y', 'z'), map(float, position))),
                'rotation_matrix': rotation.flatten().tolist(),
            }
    return payload


class TrackingProcessor:
    def __init__(self, cfg, camera_matrix, dist_coeffs):
        self.cfg = cfg
        self.geometry = PrismGeometry(cfg)
        self.estimator = PoseEstimator(cfg, self.geometry, camera_matrix, dist_coeffs)
        self.filters = PoseFilters(cfg['filter'], self.geometry.groups)
        self.renderer = Renderer(cfg['display'], self.geometry, camera_matrix, dist_coeffs)
        self.last_update = None
        self.last_poses = {}
        self.markers = {}

    def process(self, frame, timestamp):
        if self.last_update is not None and timestamp < self.last_update:
            # rosbag / simulated-clock rewind: discard state from the previous timeline.
            self.filters = PoseFilters(self.cfg['filter'], self.geometry.groups)
            self.last_update = None
            self.last_poses.clear()
        self.markers = self.estimator.detect(frame)
        current = {}
        if self.last_update is None or timestamp - self.last_update >= self.cfg['update']['interval']:
            for name, ids in self.geometry.groups.items():
                pose = self.estimator.estimate(self.markers, ids)
                if pose is not None:
                    pos, rot = pose
                    current[name] = self.filters.update(name, pos, rot, timestamp)
                    self.last_poses[name] = current[name]
            self.last_update = timestamp
        return current

    def draw(self, frame):
        return self.renderer.draw(frame, self.markers, self.last_poses)
