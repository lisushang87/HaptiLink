"""Build driver/RTAB arguments from shared configuration (no ROS imports)."""
from pathlib import Path


def camera_arguments(tracking, shared):
    c, depth = tracking['camera'], shared['camera']
    return {
        'camera_namespace': depth['namespace'], 'camera_name': depth['name'],
        'serial_no': '_' + c['serial_number'] if c['serial_number'] else "''",
        'enable_color': 'true', 'enable_depth': 'true',
        'enable_infra1': 'false', 'enable_infra2': 'false',
        'rgb_camera.color_profile': f"{c['width']},{c['height']},{c['fps']}",
        'depth_module.depth_profile': f"{depth['depth_width']},{depth['depth_height']},{depth['depth_fps']}",
        'align_depth.enable': 'true', 'enable_sync': 'true',
        'pointcloud.enable': 'false',
    }


def rtabmap_arguments(shared, database_path=None):
    r, t = shared['rtabmap'], shared['topics']
    return {
        'namespace': r['namespace'], 'frame_id': r['frame_id'],
        'vo_frame_id': r['odom_frame_id'], 'odom_topic': t['odometry'],
        'rgb_topic': t['color'], 'depth_topic': t['depth'], 'camera_info_topic': t['camera_info'],
        'visual_odometry': 'true', 'depth': 'true', 'subscribe_rgb': 'true',
        'approx_sync': 'true', 'approx_sync_max_interval': str(r['approx_sync_max_interval']),
        'topic_queue_size': str(r['topic_queue_size']), 'sync_queue_size': str(r['sync_queue_size']),
        'qos': '2', 'qos_image': '2', 'qos_camera_info': '2', 'qos_odom': '2',
        'rtabmap_viz': str(r['visualization']).lower(), 'rviz': 'false',
        'database_path': str(Path(database_path or r['database_path'] or '~/.ros/rtabmap.db').expanduser()),
        'args': '',  # Never delete a user's saved map on startup.
    }
