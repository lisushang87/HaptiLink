"""RViz marker builders. All poses are expressed in the marker header frame."""
import numpy as np
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray


def point(value):
    return Point(x=float(value[0]), y=float(value[1]), z=float(value[2]))


def color(rgb):
    return ColorRGBA(r=float(rgb[0]), g=float(rgb[1]), b=float(rgb[2]), a=1.0)


def marker(frame, stamp, namespace, ident, kind, lifetime=0.):
    m = Marker()
    m.header.frame_id, m.header.stamp = frame, stamp
    m.ns, m.id, m.type, m.action = namespace, ident, kind, Marker.ADD
    m.pose.orientation.w = 1.
    m.color = color((1, 1, 1))
    total = int(lifetime * 1e9)
    m.lifetime = Duration(sec=total // 1_000_000_000, nanosec=total % 1_000_000_000)
    return m


def axes(frame, stamp, namespace, position, rotation, length, lifetime=0.):
    m = marker(frame, stamp, namespace, 0, Marker.LINE_LIST, lifetime)
    m.scale.x = length * .035
    for i, rgb in enumerate(((1., .25, .25), (.25, 1., .35), (.3, .6, 1.))):
        m.points.extend([point(position), point(position + rotation[:, i] * length)])
        m.colors.extend([color(rgb), color(rgb)])
    return m


def label(frame, stamp, namespace, text, position, size=.035, lifetime=0.):
    m = marker(frame, stamp, namespace, 1, Marker.TEXT_VIEW_FACING, lifetime)
    m.pose.position = point(position)
    m.scale.z = size
    # Humble's Ogre text keeps an oversized space advance at small character heights.
    # Compact tokens/newlines avoid labels spreading far outside the view.
    m.text = text.replace(' ', '_')
    return m


def wireframe(frame, stamp, namespace, position, rotation, vertices, edges, rgb, lifetime=0.):
    m = marker(frame, stamp, namespace, 2, Marker.LINE_LIST, lifetime)
    m.scale.x = .003
    m.color = color(rgb)
    transformed = np.asarray(vertices) @ rotation.T + position
    m.points = [point(transformed[i]) for edge in edges for i in edge]
    return m


def erase(frame, stamp, namespace):
    result = []
    for ident in (0, 1, 2, 3):
        m = marker(frame, stamp, namespace, ident, Marker.LINE_LIST)
        m.action = Marker.DELETE
        result.append(m)
    return result


class HandScene:
    """Hold valid measurements only; never refresh a hand's TF on a timer."""
    def __init__(self, view, geometry):
        self.view, self.geometry = view, geometry
        self.states = {}

    def update(self, poses, visible_names, now):
        for name in list(self.states):
            if name not in visible_names:
                del self.states[name]
        for name, pose in poses.items():
            self.states[name] = (now, pose)

    def build(self, frame, stamp, now):
        markers = [axes(frame, stamp, 'camera_origin', np.zeros(3), np.eye(3), self.view['axis_length'] * 1.5),
                   label(frame, stamp, 'camera_origin', 'CAMERA_ORIGIN\nX:right/Y:down/Z:forward',
                         np.array([0., -.14, 0.]))]
        for i, name in enumerate(self.geometry.groups):
            state = self.states.get(name)
            ns = self.view['hand_frames'][i]
            if state is None or now - state[0] > self.view['stale_timeout']:
                markers.extend(erase(frame, stamp, ns))
                self.states.pop(name, None)
                continue
            _, (pos, rot) = state
            # Do not extend lifetime past the stale deadline when rendering cached data.
            lifetime = max(.001, self.view['stale_timeout'] - (now - state[0]))
            connection = marker(frame, stamp, ns, 3, Marker.LINE_LIST, lifetime)
            connection.scale.x = .0015
            connection.color = color((.5, .55, .65))
            connection.points = [point(np.zeros(3)), point(pos)]
            markers.append(connection)
            markers.extend([
                axes(frame, stamp, ns, pos, rot, self.view['axis_length'], lifetime),
                wireframe(frame, stamp, ns, pos, rot, self.geometry.vertices, self.geometry.edges,
                          (0.2, 1., .5) if i == 0 else (.9, .35, 1.), lifetime),
                label(frame, stamp, ns, f'{ns}\nX={pos[0]:+.3f}m\nY={pos[1]:+.3f}m\nZ={pos[2]:+.3f}m',
                      pos + np.array([0., -.14, 0.]), size=.025, lifetime=lifetime)])
        return MarkerArray(markers=markers)
