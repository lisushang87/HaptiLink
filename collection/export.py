"""Export human observation-only LeRobot datasets; no robot action field."""
import argparse
import json
from pathlib import Path
import cv2
from .common import config,DEFAULT_CONFIG
from .dataset import aligned_frames


def export(episodes,root,repo_id,cfg,factory=None):
    if Path(root).exists():raise ValueError('Output must not already exist')
    if factory is None:
        try:
            from lerobot.datasets.lerobot_dataset import LeRobotDataset
        except ImportError as e:
            raise RuntimeError('LeRobot export dependencies missing; run bash collection/setup_export.bash and use .venv-lerobot/bin/python') from e
        factory=LeRobotDataset
    dataset=None;pending=0;segments=0;total=0;provenance=[];shape=None
    try:
        for episode in episodes:
            info=None;segment_start=segments
            for frame in aligned_frames(episode,cfg):
                if frame is None:
                    if pending:dataset.save_episode();segments+=1;pending=0
                    continue
                image=cv2.imread(str(Path(episode)/frame['image']))
                if image is None:raise ValueError('Missing image '+frame['image'])
                image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
                if dataset is None:
                    shape=image.shape
                    features={'observation.images.camera':dict(dtype='video',shape=shape,names=['height','width','channels']),
                              'observation.state':dict(dtype='float32',shape=(65,),names=
                                  [f'{hand}_prism_camera_{axis}' for hand in ('left','right') for axis in ('x','y','z','qx','qy','qz','qw')]+
                                  [f'{hand}_raw_adc_{ch}' for hand in ('left','right') for ch in [f'HZ{i}' for i in range(6)]+[f'H{i}' for i in range(16)]]+
                                  [f'odometry_child_{axis}' for axis in ('x','y','z','qx','qy','qz','qw')]),
                              'observation.valid':dict(dtype='float32',shape=(5,),names=['left_pose','right_pose','left_glove','right_glove','odometry']),
                              'observation.source_time':dict(dtype='float64',shape=(1,),names=['raw_episode_seconds'])}
                    dataset=factory.create(repo_id=repo_id,root=str(root),fps=cfg['fps'],features=features,robot_type='human_demonstration',use_videos=True)
                if image.shape!=shape:raise ValueError('Image dimensions changed')
                dataset.add_frame({'observation.images.camera':image,'observation.state':frame['state'],
                    'observation.valid':frame['valid'],'observation.source_time':frame['source_time'],'task':frame['task']})
                pending+=1;total+=1;info=frame['frame_ids']
            if pending:dataset.save_episode();segments+=1;pending=0
            provenance.append(dict(raw_episode=str(Path(episode).resolve()),frame_ids=info,dataset_episode_start=segment_start,dataset_episode_count=segments-segment_start))
    finally:
        if dataset is not None:dataset.finalize()
    if dataset is None:raise ValueError('No exportable images')
    (Path(root)/'human_provenance.json').write_text(json.dumps(dict(raw=provenance,config=cfg,
        state_layout=['left_prism_camera_xyz_xyzw:7','right_prism_camera_xyz_xyzw:7','left_raw_adc:22','right_raw_adc:22','odometry_child_in_parent_xyz_xyzw:7'],
        missing='zeros/identity with observation.valid=0; not valid measurements',
        action=None,glove_calibration='unverified',segments=segments,frames=total),indent=2))
    return dict(frames=total,episodes=segments)


def main():
    p=argparse.ArgumentParser();p.add_argument('episodes',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repo-id',default='local/human-demonstrations');p.add_argument('--config',default=str(DEFAULT_CONFIG))
    a=p.parse_args();print(export(a.episodes,a.output,a.repo_id,config(a.config)))
if __name__=='__main__':main()
