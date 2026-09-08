"""World camera trajectory markers for a dedicated RViz window; no camera I/O."""
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped, TransformStamped
from visualization_msgs.msg import Marker, MarkerArray
from tf2_ros import Buffer, TransformListener, StaticTransformBroadcaster, TransformException
from tracking.scene_markers import axes, label, wireframe, marker, point, color, erase
from tracking.ros_input import stamp_seconds
from tracking.utils import quaternion_to_rotation_matrix, rotation_matrix_to_quaternion
from .settings import DEFAULT_SHARED_CONFIG, load_shared_config
from .motion_scene import CameraTrajectory


class CameraMotionNode(Node):
    def __init__(self):
        super().__init__('camera_motion_view')
        self.declare_parameter('shared_config', str(DEFAULT_SHARED_CONFIG))
        self.shared = load_shared_config(self.get_parameter('shared_config').value)
        self.cfg = self.shared['views']['camera']
        self.trajectory = CameraTrajectory(self.cfg['trail_max_points'], self.cfg['sample_distance'])
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.reference_broadcaster = StaticTransformBroadcaster(self)
        self.publisher = self.create_publisher(MarkerArray, self.cfg['topic'], 1)
        self.subscription = self.create_subscription(PoseStamped, self.shared['topics']['camera_pose'], self.on_pose, qos_profile_sensor_data)
        self.pending = None
        self.last_received = None
        self.last_warning = -float('inf')
        self.timer = self.create_timer(1. / self.cfg['update_rate'], self.update_view)

    def on_pose(self, msg):
        self.pending = msg

    def update_view(self):
        now = self.get_clock().now()
        monotonic_now = time.monotonic()
        if self.pending is not None:
            msg = self.pending
            age = now.nanoseconds * 1e-9 - stamp_seconds(msg.header.stamp)
            if not -.1 <= age <= self.cfg['stale_timeout']:
                self.pending = None
            else:
                try:
                    # camera_pose is in odom. Transform that pose at its acquisition time,
                    # rather than labelling odometry coordinates as map coordinates.
                    p = msg.pose.position
                    q = msg.pose.orientation
                    quaternion = np.array([q.w, q.x, q.y, q.z])
                    if not np.isfinite(quaternion).all() or np.linalg.norm(quaternion) < 1e-12:
                        raise ValueError('无效相机姿态')
                    quaternion /= np.linalg.norm(quaternion)
                    position = np.array([p.x, p.y, p.z])
                    rotation = quaternion_to_rotation_matrix(quaternion)
                    if msg.header.frame_id != self.cfg['world_frame']:
                        tf = self.buffer.lookup_transform(self.cfg['world_frame'], msg.header.frame_id,
                                                          Time.from_msg(msg.header.stamp))
                        t, r = tf.transform.translation, tf.transform.rotation
                        world_q = np.array([r.w, r.x, r.y, r.z])
                        world_q /= np.linalg.norm(world_q)
                        world_R = quaternion_to_rotation_matrix(world_q)
                        position = world_R @ position + np.array([t.x, t.y, t.z])
                        rotation = world_R @ rotation
                    if not np.isfinite(position).all():
                        raise ValueError('无效相机位置')
                    first = self.trajectory.update(position, rotation, stamp_seconds(msg.header.stamp))
                    if first:
                        self.publish_reference(msg.header.stamp)
                        self.get_logger().info('已建立相机初始参考坐标系；运动轨迹从原点开始')
                    self.last_received = monotonic_now
                    self.pending = None
                except (TransformException, ValueError) as error:
                    if monotonic_now - self.last_warning > 2:
                        self.get_logger().warning(f'等待有效世界坐标变换: {error}')
                        self.last_warning = monotonic_now
        if self.trajectory.origin is None:
            return
        self.publisher.publish(self.build_scene(now.to_msg(), monotonic_now))

    def publish_reference(self, stamp):
        transform = TransformStamped()
        transform.header.stamp, transform.header.frame_id = stamp, self.cfg['world_frame']
        transform.child_frame_id = self.cfg['reference_frame']
        p = self.trajectory.origin
        q = rotation_matrix_to_quaternion(self.trajectory.origin_rotation)
        transform.transform.translation.x, transform.transform.translation.y, transform.transform.translation.z = map(float, p)
        transform.transform.rotation.w, transform.transform.rotation.x, transform.transform.rotation.y, transform.transform.rotation.z = map(float, q)
        self.reference_broadcaster.sendTransform(transform)

    def build_scene(self, stamp, now):
        frame, size = self.cfg['reference_frame'], self.cfg['axis_length']
        output = [axes(frame, stamp, 'start_origin', np.zeros(3), np.eye(3), size),
                  label(frame, stamp, 'start_origin', 'CAMERA_START\nFIXED_ORIGIN', np.array([0., 0., -.12]), size=.05)]
        trail = marker(frame, stamp, 'camera_path', 0, Marker.LINE_STRIP)
        trail.scale.x = .008
        trail.color = color((.25, .8, 1.))
        trail.points = [point(p) for p in self.trajectory.points]
        if len(trail.points) < 2:
            trail.action = Marker.DELETE
        output.append(trail)
        fresh = self.last_received is not None and now - self.last_received <= self.cfg['stale_timeout']
        if fresh:
            p, R = self.trajectory.latest
            ttl = max(.001, self.cfg['stale_timeout'] - (now - self.last_received))
            vertices = np.array([[0,0,0],[.14,-.06,-.04],[.14,.06,-.04],[.14,.06,.04],[.14,-.06,.04]])
            edges = [(0, i) for i in range(1,5)] + [(1,2),(2,3),(3,4),(4,1)]
            output.extend([axes(frame, stamp, 'camera_current', p, R, size, ttl),
                           wireframe(frame, stamp, 'camera_current', p, R, vertices, edges, (1., .8, .2), ttl),
                           label(frame, stamp, 'camera_current',
                                 f'CAMERA\nX={p[0]:+.3f}m\nY={p[1]:+.3f}m\nZ={p[2]:+.3f}m\nDistance={np.linalg.norm(p):.3f}m',
                                 p + np.array([0., 0., .24]), size=.06, lifetime=ttl)])
        else:
            output.extend(erase(frame, stamp, 'camera_current'))
            output.append(label(frame, stamp, 'camera_status', 'TRACKING_LOST\ntrajectory_retained', np.array([0., 0., .3])))
        if fresh:
            deletion = label(frame, stamp, 'camera_status', '', np.zeros(3))
            deletion.action = Marker.DELETE
            output.append(deletion)
        return MarkerArray(markers=output)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = CameraMotionNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
