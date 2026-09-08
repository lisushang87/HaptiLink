"""Four-timestamp affine clock estimator. RTT/2 is not a measured accuracy."""
from collections import deque
import numpy as np


class ClockMap:
    def __init__(self, max_rtt=.100, max_age=3., max_residual=.005):
        self.points = deque(maxlen=120)
        self.max_rtt, self.max_age, self.max_residual = max_rtt, max_age, max_residual
        self.a = 1.
        self.x0 = self.y0 = self.residual = self.last = None
        self.rejected = 0
        self.rtt = None

    def add(self, t1, t2, t3, t4):
        rtt = (t4-t1)-(t3-t2)
        if t3 < t2 or t4 < t1 or not 0 <= rtt <= self.max_rtt:
            self.rejected += 1
            return False
        self.points.append(((t2+t3)/2, (t1+t4)/2, rtt, t4))
        # Prefer lower-delay exchanges. There is no assumption of zero radio jitter.
        recent = [p for p in self.points if t4-p[3] <= 60]
        good = sorted(recent, key=lambda p: p[2])[:max(5, len(recent)//4)]
        x, y, _, _ = np.asarray(good).T
        self.x0, self.y0 = float(x.mean()), float(y.mean())
        dx, dy = x-self.x0, y-self.y0
        self.a = float(dx@dy/(dx@dx)) if np.ptp(x) >= 10 and dx@dx > 0 else 1.
        self.residual = float(np.sqrt(np.mean((self.a*dx-dy)**2)))
        self.last = t4
        self.rtt = min(p[2] for p in good)
        return True

    def quality(self, now):
        span = self.points[-1][0]-self.points[0][0] if len(self.points)>1 else 0
        valid = (len(self.points)>=5 and span>=2 and self.last is not None
                 and now-self.last <= self.max_age and abs(self.a-1)<=.001
                 and self.residual <= self.max_residual)
        return dict(valid=bool(valid), exchanges=len(self.points), rejected=self.rejected,
                    age_s=None if self.last is None else now-self.last,
                    drift_ppm=(self.a-1)*1e6, fit_rms_s=self.residual,
                    best_adjusted_rtt_s=self.rtt,
                    warning='RTT and fit residual do not prove absolute synchronization accuracy')

    def to_host(self, board_s, now):
        if not self.quality(now)['valid']:
            return None
        return self.y0+self.a*(board_s-self.x0)
