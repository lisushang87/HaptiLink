"""Offline fixed-grid human observations. No invented robot action labels."""
import bisect
import json
from pathlib import Path
import numpy as np
from glove.align import align
from .common import config, stamp_ns, pose_vector


def load_episode(folder):
    folder=Path(folder);meta=json.loads((folder/'metadata.json').read_text())
    if meta['status']!='saved':raise ValueError('Episode must be explicitly saved')
    if meta.get('queue_drops') or meta.get('write_errors'):raise ValueError('Recording has disk/queue errors; inspect raw data')
    with (folder/'events.jsonl').open() as f: events=[json.loads(l) for l in f if l.strip()]
    return meta,events


def nearest(rows,t,tolerance):
    if not rows:return None
    j=bisect.bisect_left(rows,(t,),key=None)
    choices=rows[max(0,j-1):min(len(rows),j+1)]
    best=min(choices,key=lambda x:abs(x[0]-t))
    return best[1] if abs(best[0]-t)<=tolerance else None


def aligned_frames(folder,cfg=None):
    cfg=cfg or config();meta,events=load_episode(folder)
    fps=float(cfg['fps'])
    if not 0<fps<=120:raise ValueError('fps must be in (0,120]')
    streams={};frames={};frame_ids={};last_image_stamp=None
    for event in events:
        key=event['kind']
        if key=='image':header=event['header'];value=event
        elif key in ('left_pose','right_pose','odometry'):
            header=event['data']['header'];value=event['data']
            if key=='odometry':
                cov=value['pose']['covariance'][0]
                if not np.isfinite(cov) or not 0<=cov<9999:continue
        else:continue
        ts=stamp_ns(header['stamp'])
        if ts<=0:continue
        if key=='image':
            if last_image_stamp is not None and ts<last_image_stamp:raise ValueError('Image clock moved backward; split raw episode')
            last_image_stamp=ts
        frame_ids.setdefault(key,set()).add(header['frame_id'])
        if key=='odometry':frame_ids.setdefault('odometry_child',set()).add(value['child_frame_id'])
        streams.setdefault(key,{})[ts]=value
    if any(len(v)!=1 for v in frame_ids.values()):raise ValueError('Coordinate frame changed within episode')
    for key in ('left_pose','right_pose'):
        if key in frame_ids and frame_ids[key]!=frame_ids.get('image'):raise ValueError('Hand pose is not in image frame')
    streams={k:sorted(v.items()) for k,v in streams.items()};images=streams.get('image',[])
    if not images:raise ValueError('No images')
    origin=images[0][0];end=images[-1][0]
    targets=[origin+round(i*1e9/fps) for i in range(int((end-origin+1)*fps/1e9)+1)]
    glove={}
    for hand in ('left','right'):
        rows=[e['data'] for e in events if e['kind']==hand+'_glove']
        if len({r['uid'] for r in rows if r.get('kind')=='sample'})>1:raise ValueError('Glove UID changed within episode')
        glove[hand]=align(rows,targets,max_gap_ms=cfg['glove_max_gap_ms'])
    used=set()
    for i,t in enumerate(targets):
        image=nearest(images,t,cfg['max_image_error_ms']*1e6)
        if image is None or image['path'] in used:
            yield None;continue  # exporter starts a new segment; never compress missing video time
        used.add(image['path']);state=[];valid=[]
        for hand in ('left','right'):
            p=nearest(streams.get(hand+'_pose',[]),t,cfg['max_pose_error_ms']*1e6)
            try:v=pose_vector(p['pose']);ok=True
            except (ValueError,TypeError,KeyError):v=[0.]*6+[1.];ok=False
            state+=v;valid.append(float(ok))
        for hand in ('left','right'):
            g=glove[hand][i];ok=g['valid'] and len(g['adc'])==22
            state+=g['adc'] if ok else [0.]*22;valid.append(float(ok))
        odom=nearest(streams.get('odometry',[]),t,cfg['max_pose_error_ms']*1e6)
        try:v=pose_vector(odom['pose']['pose']);ok=True
        except (ValueError,TypeError,KeyError):v=[0.]*6+[1.];ok=False
        state+=v;valid.append(float(ok))
        yield dict(image=image['path'],state=np.asarray(state,dtype=np.float32),valid=np.asarray(valid,dtype=np.float32),
                   source_time=np.asarray([(t-origin)/1e9],dtype=np.float64),task=meta['task'],
                   frame_ids={k:next(iter(v)) for k,v in frame_ids.items()})
