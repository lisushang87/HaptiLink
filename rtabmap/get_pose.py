"""ROS 2 odometry -> PoseStamped and optional legacy TCP snapshot bridge."""
import copy
import json
import math
import socket
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from .settings import DEFAULT_SHARED_CONFIG, load_shared_config
from tracking.ros_input import stamp_seconds


class PoseListener(Node):
    def __init__(self):
        super().__init__('pose_listener')
        self.declare_parameter('shared_config', str(DEFAULT_SHARED_CONFIG))
        cfg = load_shared_config(self.get_parameter('shared_config').value)
        self.options = cfg['odometry_bridge']
        self.latest = None
        self.reference = None
        self.last_stamp = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.server = self.thread = None
        self.publisher = self.create_publisher(PoseStamped, cfg['topics']['camera_pose'], 1)
        self.subscription = self.create_subscription(Odometry, cfg['topics']['odometry'], self.on_pose, qos_profile_sensor_data)
        self.report_timer = None
        if self.options['show_position']:
            self.report_timer = self.create_timer(self.options['console_interval'], self.report_position)
        if self.options['tcp_enabled']:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server.bind((self.options['tcp_host'], self.options['tcp_port']))
                self.server.listen(1)
                self.server.settimeout(.2)
            except Exception:
                self.server.close()
                raise
            self.thread = threading.Thread(target=self.serve, daemon=True)
            self.thread.start()

    def on_pose(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        values = (p.x, p.y, p.z, q.x, q.y, q.z, q.w)
        if not all(math.isfinite(v) for v in values) or sum(v*v for v in values[3:]) < 1e-12:
            with self.lock:
                self.latest = None
            return
        if msg.pose.covariance[0] < 0 or msg.pose.covariance[0] >= 9999:
            with self.lock:
                self.latest = None
            return
        stamp = stamp_seconds(msg.header.stamp)
        age = self.get_clock().now().nanoseconds * 1e-9 - stamp
        if not -0.1 <= age <= self.options['max_pose_age']:
            with self.lock:
                self.latest = None
            return
        packet = {'position': {'x': p.x, 'y': p.y, 'z': p.z},
                  'orientation': {'x': q.x, 'y': q.y, 'z': q.z, 'w': q.w},
                  'timestamp': stamp, 'frame_id': msg.header.frame_id,
                  'child_frame_id': msg.child_frame_id}
        with self.lock:
            frame_pair = (msg.header.frame_id, msg.child_frame_id)
            if (self.reference is None or self.reference[0] != frame_pair
                    or (self.last_stamp is not None and stamp < self.last_stamp)):
                self.reference = (frame_pair, (p.x, p.y, p.z))
            self.last_stamp = stamp
            self.latest = (time.monotonic(), packet)
        pose = PoseStamped()
        pose.header, pose.pose = msg.header, msg.pose.pose
        self.publisher.publish(pose)

    def report_position(self):
        with self.lock:
            latest = copy.deepcopy(self.latest)
            reference = self.reference
        if latest is None:
            self.get_logger().info('等待有效相机定位数据；请确认终端1已启动且相机能看到有纹理的场景')
            return
        if time.monotonic() - latest[0] > self.options['max_pose_age']:
            self.get_logger().warning('相机定位数据已过期，暂不显示位移')
            return
        packet = latest[1]
        x, y, z = (packet['position'][axis] for axis in ('x', 'y', 'z'))
        dx, dy, dz = (value - origin for value, origin in zip((x, y, z), reference[1]))
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.get_logger().info(
            f"相机 {packet['child_frame_id']} 在 {packet['frame_id']} 中的位置[m]: "
            f"X={x:+.3f} Y={y:+.3f} Z={z:+.3f} | "
            f"相对首次定位位移[m]: dX={dx:+.3f} dY={dy:+.3f} dZ={dz:+.3f} "
            f"直线距离={distance:.3f}")

    def serve(self):
        while not self.stop_event.is_set():
            try:
                client, _ = self.server.accept()
                with client:
                    client.settimeout(.1)
                    with self.lock:
                        latest = copy.deepcopy(self.latest)
                    if latest is not None and time.monotonic() - latest[0] <= self.options['max_pose_age']:
                        client.sendall((json.dumps(latest[1], allow_nan=False)+'\n').encode())
            except socket.timeout:
                continue
            except OSError:
                if self.stop_event.is_set():
                    break

    def destroy_node(self):
        self.stop_event.set()
        if self.server is not None:
            self.server.close()
        if self.thread is not None:
            self.thread.join(timeout=1)
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PoseListener()
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
