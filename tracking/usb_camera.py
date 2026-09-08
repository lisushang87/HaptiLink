"""Ordinary Linux USB camera -> synchronized raw Image and calibrated CameraInfo."""
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from tracking.config import DEFAULT_CONFIG, load_config
from tracking.calibration import load_calibration
from rtabmap.settings import DEFAULT_SHARED_CONFIG, load_shared_config


def make_info(width, height, K, D, header):
    info = CameraInfo()
    info.header = header
    info.width, info.height = width, height
    info.distortion_model = 'plumb_bob'
    info.k = K.flatten().tolist(); info.d = D.tolist()
    info.r = np.eye(3).flatten().tolist()
    P = np.zeros((3, 4)); P[:, :3] = K
    info.p = P.flatten().tolist()
    return info


class UsbCamera(Node):
    def __init__(self):
        super().__init__('usb_camera_source')
        self.declare_parameter('tracking_config', str(DEFAULT_CONFIG))
        self.declare_parameter('shared_config', str(DEFAULT_SHARED_CONFIG))
        path = Path(self.get_parameter('tracking_config').value).resolve()
        cfg = load_config(path)['camera']
        shared = load_shared_config(self.get_parameter('shared_config').value)
        calibration = Path(cfg['calibration_file']).expanduser()
        if not calibration.is_absolute():
            calibration = path.parent / calibration
        self.K, self.D = load_calibration(calibration, cfg['width'], cfg['height'])
        self.size = (cfg['width'], cfg['height'])
        self.frame_id = shared['views']['hands']['fixed_frame']
        self.bridge = CvBridge()
        self.image_pub = self.create_publisher(Image, shared['topics']['color'], qos_profile_sensor_data)
        self.info_pub = self.create_publisher(CameraInfo, shared['topics']['camera_info'], qos_profile_sensor_data)
        device = cfg.get('device', '/dev/video0')
        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        try:
            if not self.cap.isOpened():
                raise RuntimeError(f'无法打开USB相机 {device}')
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
            self.cap.set(cv2.CAP_PROP_FPS, cfg['fps'])
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.timer = self.create_timer(1 / cfg['fps'], self.publish_frame)
        except Exception:
            self.cap.release()
            raise
        self.get_logger().info(f'普通相机已加载标定 {calibration}；只提供彩色流，不提供RTAB所需深度')

    def publish_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError('USB相机读取失败')
        if frame.shape[1::-1] != self.size:
            raise ValueError(f'相机实际输出{frame.shape[1::-1]}与标定尺寸{self.size}不符')
        image = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        # Software receipt time, not a hardware exposure timestamp.
        image.header.stamp = self.get_clock().now().to_msg()
        image.header.frame_id = self.frame_id
        info = make_info(*self.size, self.K, self.D, image.header)
        self.image_pub.publish(image)
        self.info_pub.publish(info)

    def destroy_node(self):
        self.cap.release()
        return super().destroy_node()


def main():
    rclpy.init()
    node = None
    try:
        node = UsbCamera()
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
