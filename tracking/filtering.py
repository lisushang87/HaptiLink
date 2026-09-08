"""Independent One Euro filter state for each target."""
from tracking.one_euro import OneEuroFilter, OneEuroQuaternionFilter
from tracking.utils import rotation_matrix_to_quaternion, quaternion_to_rotation_matrix


class PoseFilters:
    def __init__(self, cfg, names):
        self.states = {
            name: (OneEuroFilter(reset_after=cfg['reset_after'], **cfg['position']),
                   OneEuroQuaternionFilter(reset_after=cfg['reset_after'], **cfg['rotation']))
            for name in names
        }

    def update(self, name, position, rotation, timestamp):
        position_filter, rotation_filter = self.states[name]
        position = position_filter.update(position, timestamp)
        quat = rotation_filter.update(rotation_matrix_to_quaternion(rotation), timestamp)
        return position, quaternion_to_rotation_matrix(quat)
