from pathlib import Path
import yaml
import math

DEFAULT_CONFIG=Path(__file__).with_name('config.yaml')
def config(path=DEFAULT_CONFIG):
    with open(path) as f: return yaml.safe_load(f)

def stamp_ns(stamp):return int(stamp['sec'])*1000000000+int(stamp['nanosec'])

def pose_vector(pose):
    p,q=pose['position'],pose['orientation']
    v=[p[k] for k in ('x','y','z')]+[q[k] for k in ('x','y','z','w')]
    if not all(math.isfinite(x) for x in v):raise ValueError('Nonfinite pose')
    norm=sum(x*x for x in v[3:])**.5
    if norm<1e-8:raise ValueError('Invalid quaternion')
    return v[:3]+[x/norm for x in v[3:]]
