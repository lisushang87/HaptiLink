"""Minimal RViz scenes; configurable topics/frames, no RTAB native GUI."""
import yaml


def view_config(kind, shared):
    view = shared['views'][kind]
    frame = view['fixed_frame'] if kind == 'hands' else view['reference_frame']
    hands = kind == 'hands'
    return {
        'Panels': [{'Class': 'rviz_common/Displays', 'Name': 'Displays'}],
        'Visualization Manager': {
            'Class': '', 'Enabled': True, 'Name': 'root',
            'Global Options': {'Background Color': '24; 29; 39', 'Fixed Frame': frame, 'Frame Rate': 30},
            'Displays': [
                {'Class': 'rviz_default_plugins/Grid', 'Name': 'Grid', 'Enabled': True,
                 'Value': True, 'Alpha': .35, 'Cell Size': .1 if hands else .25,
                 'Color': '125; 140; 165', 'Plane': 'XZ' if hands else 'XY',
                 'Plane Cell Count': 20, 'Normal Cell Count': 0, 'Reference Frame': '<Fixed Frame>',
                 'Line Style': {'Value': 'Lines', 'Line Width': .01}},
                {'Class': 'rviz_default_plugins/MarkerArray', 'Name': '3D Scene',
                 'Enabled': True, 'Value': True, 'Namespaces': {},
                 'Topic': {'Value': view['topic'], 'Depth': 1, 'History Policy': 'Keep Last',
                           'Reliability Policy': 'Reliable', 'Durability Policy': 'Volatile', 'Filter size': 10}},
                {'Class': 'rviz_default_plugins/TF', 'Name': 'TF Tree', 'Enabled': False,
                 'Frame Timeout': view['stale_timeout'], 'Show Arrows': True, 'Show Axes': True,
                 'Show Names': True, 'Marker Scale': .3, 'Frames': {'All Enabled': True}},
            ],
            'Tools': [{'Class': 'rviz_default_plugins/Interact'}, {'Class': 'rviz_default_plugins/MoveCamera'},
                      {'Class': 'rviz_default_plugins/Select'}, {'Class': 'rviz_default_plugins/FocusCamera'}],
            'Views': {'Current': {'Class': 'rviz_default_plugins/Orbit', 'Name': 'Current View',
                                 'Distance': 1.6 if hands else 2.4, 'Pitch': .35, 'Yaw': -.8,
                                 'Focal Point': {'X': 0., 'Y': 0., 'Z': .4 if hands else 0.},
                                 'Target Frame': '<Fixed Frame>', 'Near Clip Distance': .01}, 'Saved': []},
            'Transformation': {'Current': {'Class': 'rviz_default_plugins/TF'}}, 'Value': True,
        },
        'Window Geometry': {'Width': 1100, 'Height': 800, 'X': 60 if hands else 100, 'Y': 60 if hands else 90},
    }


def write_view(path, kind, shared):
    with open(path, 'w', encoding='utf-8') as stream:
        yaml.safe_dump(view_config(kind, shared), stream, sort_keys=False)
