"""One camera driver, two RGB consumers. Used by the two shell entry points."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, OpaqueFunction, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from tracking.config import DEFAULT_CONFIG, load_config
from rtabmap.settings import DEFAULT_SHARED_CONFIG, load_shared_config
from rtabmap.launch_config import camera_arguments, rtabmap_arguments
from rtabmap.rviz_config import write_view


def rviz_actions(kind, shared):
    # Per-launch file prevents concurrent windows from overwriting each other's settings.
    temp = tempfile.NamedTemporaryFile(prefix=f'{kind}_', suffix='.rviz', delete=False)
    path = Path(temp.name)
    temp.close()
    write_view(path, kind, shared)
    def cleanup(context):
        path.unlink(missing_ok=True)
        return []
    rviz = Path(get_package_prefix('rviz2')) / 'lib/rviz2/rviz2'
    title = 'Hands | Camera origin' if kind == 'hands' else 'Camera motion | Initial pose origin'
    window = ExecuteProcess(cmd=[str(rviz), '-d', str(path), '-t', title,
                                 '--ros-args', '-r', f'__node:={kind}_space_view'], output='screen')
    return [RegisterEventHandler(OnShutdown(on_shutdown=[OpaqueFunction(function=cleanup)])), window]


def setup(context):
    shared_path = str(Path(LaunchConfiguration('shared_config').perform(context)).resolve())
    shared = load_shared_config(shared_path)
    def enabled(name):
        value = LaunchConfiguration(name).perform(context).lower()
        if value not in ('true', 'false'):
            raise ValueError(f'{name} 必须是 true 或 false')
        return value == 'true'

    start_tracking = enabled('start_tracking')
    start_rtabmap = enabled('start_rtabmap')
    if not start_tracking and not start_rtabmap:
        raise ValueError('至少启用六棱柱跟踪或RTAB定位中的一个')
    actions = []
    show_3d = context.launch_configurations.get('show_3d', '').lower()
    if show_3d not in ('', 'true', 'false'):
        raise ValueError('show_3d 必须是 true 或 false')
    def view_enabled(kind):
        return shared['views'][kind]['enabled'] if not show_3d else show_3d == 'true'
    tracking_path = str(Path(LaunchConfiguration('tracking_config').perform(context)).resolve())
    tracking = load_config(tracking_path)
    if start_rtabmap and tracking['camera'].get('backend') == 'opencv':
        raise ValueError('普通单目相机无深度，不能启动当前RGB-D RTAB链路；只运行start_tracking.bash')
    if start_tracking:
        show = LaunchConfiguration('show_window').perform(context)
        tcp = LaunchConfiguration('tcp_enabled').perform(context)
        if tracking['camera'].get('backend', 'realsense') == 'realsense':
            camera_launch = Path(get_package_share_directory('realsense2_camera')) / 'launch/rs_launch.py'
            camera = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(camera_launch)),
                                             launch_arguments=camera_arguments(tracking, shared).items())
        else:
            camera = ExecuteProcess(cmd=['/usr/bin/python3', '-m', 'tracking.usb_camera', '--ros-args',
                '-p', f'tracking_config:={tracking_path}', '-p', f'shared_config:={shared_path}'],
                cwd=str(ROOT), output='screen')
            actions.append(RegisterEventHandler(OnProcessExit(target_action=camera,
                on_exit=[EmitEvent(event=Shutdown(reason='普通相机节点已退出'))])))
        tracker_cmd = ['/usr/bin/python3', '-m', 'tracking.ros_node', '--ros-args',
                       '-p', f'tracking_config:={tracking_path}', '-p', f'shared_config:={shared_path}']
        if show:
            tracker_cmd.extend(['-p', f'show_window:={show}'])
        if tcp:
            tracker_cmd.extend(['-p', f'tcp_enabled:={tcp}'])
        tracker = ExecuteProcess(cmd=tracker_cmd, cwd=str(ROOT), output='screen',
                                 additional_env={'PYTHONUNBUFFERED': '1'})
        stop_with_tracker = RegisterEventHandler(OnProcessExit(target_action=tracker,
            on_exit=[EmitEvent(event=Shutdown(reason='六棱柱跟踪节点已退出'))]))
        actions.extend([stop_with_tracker, camera, tracker])
        if view_enabled('hands'):
            actions.extend(rviz_actions('hands', shared))
    if start_rtabmap:
        database = LaunchConfiguration('database_path').perform(context)
        rtab_launch = Path(get_package_share_directory('rtabmap_launch')) / 'launch/rtabmap.launch.py'
        slam = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(rtab_launch)),
                                       launch_arguments=rtabmap_arguments(shared, database).items())
        bridge = ExecuteProcess(cmd=['/usr/bin/python3', '-m', 'rtabmap.get_pose', '--ros-args',
                                     '-p', f'shared_config:={shared_path}'], cwd=str(ROOT), output='screen')
        motion = ExecuteProcess(cmd=['/usr/bin/python3', '-m', 'rtabmap.motion_view', '--ros-args',
                                     '-p', f'shared_config:={shared_path}'], cwd=str(ROOT), output='screen')
        stop_with_motion = RegisterEventHandler(OnProcessExit(target_action=motion,
            on_exit=[EmitEvent(event=Shutdown(reason='相机运动视图数据节点已退出'))]))
        actions.extend([stop_with_motion, slam, bridge, motion])
        if view_enabled('camera'):
            actions.extend(rviz_actions('camera', shared))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('start_tracking', default_value='true', description='Start camera and prism tracking'),
        DeclareLaunchArgument('start_rtabmap', default_value='true', description='Start RTAB localization and odometry bridge'),
        DeclareLaunchArgument('tracking_config', default_value=str(DEFAULT_CONFIG)),
        DeclareLaunchArgument('shared_config', default_value=str(DEFAULT_SHARED_CONFIG)),
        DeclareLaunchArgument('show_3d', default_value='', description='Override 3D windows: true/false'),
        DeclareLaunchArgument('show_window', default_value='', description='Override display: true/false'),
        DeclareLaunchArgument('tcp_enabled', default_value='', description='Override tracking TCP: true/false'),
        DeclareLaunchArgument('database_path', default_value='', description='Optional RTAB database path, never deleted'),
        OpaqueFunction(function=setup),
    ])
