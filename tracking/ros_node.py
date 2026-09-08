"""ROS 2 subscriber entry point. Never opens the RealSense SDK/device."""
import time
import cv2
import numpy as np
import message_filters
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, TransformStamped
from visualization_msgs.msg import MarkerArray
from tf2_ros import TransformBroadcaster
from cv_bridge import CvBridge
from tracking.network import TCPServer
from tracking.utils import rotation_matrix_to_quaternion
from .config import DEFAULT_CONFIG, load_config
from .processor import TrackingProcessor, pose_payload
from .ros_input import camera_model, stamp_seconds
from .scene_markers import HandScene
from rtabmap.settings import DEFAULT_SHARED_CONFIG, load_shared_config


class HexagonTrackingNode(Node):
    def __init__(self):
        super().__init__('hexagon_tracker')
        self.declare_parameter('tracking_config', str(DEFAULT_CONFIG))
        self.declare_parameter('shared_config', str(DEFAULT_SHARED_CONFIG))
        self.cfg = load_config(self.get_parameter('tracking_config').value)
        self.shared = load_shared_config(self.get_parameter('shared_config').value)
        self.declare_parameter('show_window', self.cfg['display']['enabled'])
        self.declare_parameter('tcp_enabled', self.cfg['tcp_server']['enabled'])
        self.cfg['display']['enabled'] = self.get_parameter('show_window').value
        tcp = dict(self.cfg['tcp_server'])
        tcp['enabled'] = self.get_parameter('tcp_enabled').value
        self.tcp_server = TCPServer(**tcp)
        self.bridge = CvBridge()
        self.processor = None
        self._model_key = None
        self._last_stamp = None
        self._last_warning = -float('inf')
        self.should_stop = False
        self.hand_scene = None
        self.hand_frame = None
        self.tf_broadcaster = TransformBroadcaster(self)
        self.marker_publisher = self.create_publisher(MarkerArray, self.shared['views']['hands']['topic'], 1)
        self.scene_timer = self.create_timer(.05, self.publish_scene)
        topics = self.shared['topics']
        self.publishers_by_name = {
            name: self.create_publisher(PoseStamped, f"{topics['pose_prefix'].rstrip('/')}/{name}/pose", 1)
            for name in ('hex_prism_1', 'hex_prism_2')
        }
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.image_sub = message_filters.Subscriber(self, Image, topics['color'], qos_profile=qos)
        self.info_sub = message_filters.Subscriber(self, CameraInfo, topics['camera_info'], qos_profile=qos)
        self.sync = message_filters.TimeSynchronizer(
            [self.image_sub, self.info_sub], self.shared['tracking']['sync_queue_size'])
        self.sync.registerCallback(self.on_frame)
        self.tcp_server.start()
        self.get_logger().info(f"订阅共用彩色流 {topics['color']}；本节点不打开相机")

    def on_frame(self, image, info):
        stamp = stamp_seconds(image.header.stamp)
        age = self.get_clock().now().nanoseconds * 1e-9 - stamp
        if age > self.shared['tracking']['max_image_age'] or age < -0.1:
            self.warn('丢弃过期或时钟不匹配的图像；检查use_sim_time及系统时钟')
            return
        if stamp == self._last_stamp:
            return
        try:
            K, D = camera_model(image, info)
            frame = self.bridge.imgmsg_to_cv2(image, desired_encoding='bgr8').copy()
        except (ValueError, RuntimeError, TypeError) as error:
            self.warn(str(error))
            return
        key = (image.width, image.height, image.header.frame_id, tuple(K.flat), tuple(D))
        if self.processor is None or key != self._model_key:
            self.processor = TrackingProcessor(self.cfg, K, D)
            self.hand_scene = HandScene(self.shared['views']['hands'], self.processor.geometry)
            self.hand_frame = image.header.frame_id
            if self.hand_frame != self.shared['views']['hands']['fixed_frame']:
                self.warn(f"三维视图fixed_frame与图像不一致，请设为 {self.hand_frame}")
            self._model_key = key
            self.get_logger().info(f'已加载CameraInfo: {image.width}x{image.height}, {image.header.frame_id}')
        self._last_stamp = stamp
        poses = self.processor.process(frame, stamp)
        visible = {name for name, ids in self.processor.geometry.groups.items()
                   if any(mid in self.processor.markers for mid in ids)}
        self.hand_scene.update(poses, visible, time.monotonic())
        if poses:
            self.tcp_server.send_packet({'cubes': pose_payload(poses), 'timestamp': time.time()})
            for name, (position, rotation) in poses.items():
                msg = PoseStamped()
                msg.header = image.header  # Image acquisition time and optical frame, never map.
                msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = map(float, position)
                q = rotation_matrix_to_quaternion(rotation)
                q /= np.linalg.norm(q)
                msg.pose.orientation.w, msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z = map(float, q)
                self.publishers_by_name[name].publish(msg)
                transform = TransformStamped()
                transform.header = msg.header
                index = 0 if name == 'hex_prism_1' else 1
                transform.child_frame_id = self.shared['views']['hands']['hand_frames'][index]
                transform.transform.translation.x = msg.pose.position.x
                transform.transform.translation.y = msg.pose.position.y
                transform.transform.translation.z = msg.pose.position.z
                transform.transform.rotation = msg.pose.orientation
                self.tf_broadcaster.sendTransform(transform)
        if self.cfg['display']['enabled']:
            self.processor.draw(frame)
            cv2.imshow(self.cfg['display']['window_name'], frame)
            if cv2.waitKey(1) & 0xff == ord('q'):
                self.should_stop = True

    def publish_scene(self):
        if self.hand_scene is not None:
            self.marker_publisher.publish(self.hand_scene.build(
                self.hand_frame, self.get_clock().now().to_msg(), time.monotonic()))

    def warn(self, text):
        now = time.monotonic()
        if now - self._last_warning > 2:
            self.get_logger().warning(text)
            self._last_warning = now

    def destroy_node(self):
        self.tcp_server.stop()
        if self.cfg['display']['enabled']:
            cv2.destroyAllWindows()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = HexagonTrackingNode()
        while rclpy.ok() and not node.should_stop:
            rclpy.spin_once(node, timeout_sec=0.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
