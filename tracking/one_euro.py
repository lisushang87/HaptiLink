"""One Euro position filter and a quaternion/SLERP adaptation.

Reference: https://github.com/casiez/OneEuroFilter
Position units: meters; quaternion order: [w, x, y, z].
"""
import math
import numpy as np


def _alpha(cutoff, dt):
    return 1.0 / (1.0 + 1.0 / (2.0 * math.pi * cutoff * dt))


class OneEuroFilter:
    """Component-wise One Euro filter using actual monotonic timestamps."""

    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0, reset_after=0.5):
        params = (min_cutoff, beta, d_cutoff, reset_after)
        if not all(math.isfinite(v) for v in params):
            raise ValueError('One Euro parameters must be finite')
        if min_cutoff <= 0 or beta < 0 or d_cutoff <= 0 or reset_after <= 0:
            raise ValueError('Cutoffs/reset_after must be positive; beta must be nonnegative')
        self.min_cutoff, self.beta = min_cutoff, beta
        self.d_cutoff, self.reset_after = d_cutoff, reset_after
        self.timestamp = None
        self.raw = self.filtered = self.derivative = None

    def _prepare(self, value):
        value = np.asarray(value, dtype=float)
        if value.size == 0 or not np.isfinite(value).all():
            raise ValueError('Filter input must be nonempty and finite')
        return value.copy()

    def _velocity(self, value, dt):
        return (value - self.raw) / dt

    def _blend(self, value, alpha):
        return alpha * value + (1.0 - alpha) * self.filtered

    def update(self, value, timestamp):
        value = self._prepare(value)
        if not math.isfinite(timestamp):
            raise ValueError('Timestamp must be finite')
        if self.raw is not None and value.shape != self.raw.shape:
            raise ValueError('Filter input shape must remain constant')
        dt = None if self.timestamp is None else timestamp - self.timestamp
        if dt is not None and dt <= 0:
            # Duplicate/out-of-order samples must not corrupt the derivative state.
            return self.filtered.copy()
        if dt is None or dt > self.reset_after:
            self.raw = value.copy()
            self.filtered = value.copy()
            self.derivative = np.zeros_like(self._velocity(value, 1.0))
        else:
            velocity = self._velocity(value, dt)
            a_d = _alpha(self.d_cutoff, dt)
            self.derivative = a_d * velocity + (1.0 - a_d) * self.derivative
            cutoff = self.min_cutoff + self.beta * np.abs(self.derivative)
            self.filtered = self._blend(value, _alpha(cutoff, dt))
            self.raw = value.copy()
        self.timestamp = timestamp
        return self.filtered.copy()


class OneEuroQuaternionFilter(OneEuroFilter):
    """One Euro adaptation: angular speed (rad/s) sets a scalar SLERP cutoff.

    Unlike component-wise quaternion filtering, SLERP follows the shortest arc
    and keeps the result on the unit sphere. q and -q denote the same rotation.
    """

    def _prepare(self, value):
        q = super()._prepare(value)
        if q.shape != (4,) or np.linalg.norm(q) < 1e-12:
            raise ValueError('Quaternion must be a nonzero [w, x, y, z] vector')
        q /= np.linalg.norm(q)
        if self.raw is not None and np.dot(q, self.raw) < 0:
            q = -q
        return q

    def _velocity(self, value, dt):
        cosine = np.clip(abs(np.dot(value, self.raw)), 0.0, 1.0)
        return 2.0 * np.arccos(cosine) / dt

    def _blend(self, value, alpha):
        dot = np.dot(self.filtered, value)
        if dot < 0:
            value = -value
            dot = -dot
        dot = np.clip(dot, 0.0, 1.0)
        if dot > 0.9995:
            q = (1.0 - alpha) * self.filtered + alpha * value
        else:
            angle = np.arccos(dot)
            q = (np.sin((1.0 - alpha) * angle) * self.filtered
                 + np.sin(alpha * angle) * value) / np.sin(angle)
        return q / np.linalg.norm(q)
