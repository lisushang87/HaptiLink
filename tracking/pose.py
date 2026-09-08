"""Image detection and camera-frame pose estimation; no device or socket I/O."""
import cv2
import numpy as np
from tracking.utils import rotation_matrix_to_quaternion, quaternion_to_rotation_matrix


class PoseEstimator:
    def __init__(self, cfg, geometry, camera_matrix, dist_coeffs):
        self.geometry = geometry
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, cfg['tags']['dictionary']))
        self.dictionary = dictionary
        if hasattr(cv2.aruco, 'ArucoDetector'):
            self.parameters = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(dictionary, self.parameters)
        else:
            # Ubuntu 22.04 / ROS 2 Humble ships OpenCV 4.5.
            self.parameters = cv2.aruco.DetectorParameters_create()
            self.detector = None

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, self.dictionary, parameters=self.parameters)
        markers = {}
        if ids is None:
            return markers
        for corner, mid in zip(corners, ids.flatten()):
            mid = int(mid)
            if mid not in self.geometry.ids:
                continue
            ok, rvec, tvec = cv2.solvePnP(self.geometry.marker_points, corner,
                                        self.camera_matrix, self.dist_coeffs)
            if ok:
                markers[mid] = {'corners': corner, 'rvec': rvec, 'tvec': tvec}
        return markers

    def estimate(self, markers, target_ids):
        centers, quaternions = [], []
        for face, mid in enumerate(target_ids):
            if mid not in markers:
                continue
            marker = markers[mid]
            rotation, _ = cv2.Rodrigues(marker['rvec'])
            centers.append(marker['tvec'].flatten() + self.geometry.center_offset * rotation[:, 2])
            quaternions.append(rotation_matrix_to_quaternion(rotation @ self.geometry.face_rotations[face]))
        if not centers:
            return None
        if len(quaternions) == 1:
            rotation = quaternion_to_rotation_matrix(quaternions[0])
        else:
            # The outer-product average is invariant to quaternion sign.
            Q = np.asarray(quaternions).T
            U, _, _ = np.linalg.svd(Q @ Q.T / len(quaternions))
            rotation = quaternion_to_rotation_matrix(U[:, 0] / np.linalg.norm(U[:, 0]))
        return np.mean(centers, axis=0), rotation
