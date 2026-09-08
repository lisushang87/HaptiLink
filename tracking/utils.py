import numpy as np

def rad2deg(rad):
    return rad * 180.0 / np.pi

def rotation_matrix_to_ypr(R: np.ndarray):
    """Convert a rotation matrix to yaw/pitch/roll in radians using Z-Y-X order."""
    r20 = -R[2, 0]
    r20 = np.clip(r20, -1.0, 1.0)
    pitch = np.arcsin(r20)

    if abs(r20) < 0.999999:
        roll = np.arctan2(R[2, 1], R[2, 2])
        yaw = np.arctan2(R[1, 0], R[0, 0])
    else:
        roll = 0.0
        yaw = np.arctan2(-R[0, 1], R[1, 1])

    return yaw, pitch, roll

def rotation_matrix_to_ypr_y_forward(R: np.ndarray):
    """Compute Euler angles using the object's local Y axis as the forward reference."""
    R_reframed = np.column_stack([
        R[:, 0],  # New X = original X
        R[:, 2],  # New Y = original Z
        R[:, 1]   # New Z = original Y (forward)
    ])
    return rotation_matrix_to_ypr(R_reframed)

# Quaternion conversion helpers for rotation filtering

def rotation_matrix_to_quaternion(R):
    """Convert a rotation matrix to a quaternion [w, x, y, z]."""
    q = np.empty((4, ))
    trace = np.trace(R)
    
    if trace > 0:
        sqrt_trace = np.sqrt(trace + 1.0)
        q[0] = sqrt_trace * 0.5
        q[1] = (R[2, 1] - R[1, 2]) / (2.0 * sqrt_trace)
        q[2] = (R[0, 2] - R[2, 0]) / (2.0 * sqrt_trace)
        q[3] = (R[1, 0] - R[0, 1]) / (2.0 * sqrt_trace)
    else:
        max_index = np.argmax([R[0, 0], R[1, 1], R[2, 2]])
        if max_index == 0:
            sqrt_term = np.sqrt(R[0, 0] - R[1, 1] - R[2, 2] + 1.0)
            q[1] = sqrt_term * 0.5
            q[0] = (R[2, 1] - R[1, 2]) / (2.0 * sqrt_term)
            q[2] = (R[0, 1] + R[1, 0]) / (2.0 * sqrt_term)
            q[3] = (R[0, 2] + R[2, 0]) / (2.0 * sqrt_term)
        elif max_index == 1:
            sqrt_term = np.sqrt(R[1, 1] - R[0, 0] - R[2, 2] + 1.0)
            q[2] = sqrt_term * 0.5
            q[0] = (R[0, 2] - R[2, 0]) / (2.0 * sqrt_term)
            q[1] = (R[0, 1] + R[1, 0]) / (2.0 * sqrt_term)
            q[3] = (R[1, 2] + R[2, 1]) / (2.0 * sqrt_term)
        else:
            sqrt_term = np.sqrt(R[2, 2] - R[0, 0] - R[1, 1] + 1.0)
            q[3] = sqrt_term * 0.5
            q[0] = (R[1, 0] - R[0, 1]) / (2.0 * sqrt_term)
            q[1] = (R[0, 2] + R[2, 0]) / (2.0 * sqrt_term)
            q[2] = (R[1, 2] + R[2, 1]) / (2.0 * sqrt_term)
    return q

def quaternion_to_rotation_matrix(q):
    """Convert a quaternion to a rotation matrix."""
    w, x, y, z = q
    R = np.array([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
        [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
        [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]
    ])
    return R