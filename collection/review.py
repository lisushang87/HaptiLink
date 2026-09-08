"""Quality summary and optional timestamp-paced RGB playback."""
import argparse,json,time
from collections import Counter
from pathlib import Path
import cv2
from .common import stamp_ns
from .dataset import aligned_frames


def main():
    p=argparse.ArgumentParser();p.add_argument('episode',type=Path);p.add_argument('--play',action='store_true');a=p.parse_args()
    meta=json.loads((a.episode/'metadata.json').read_text())
    with (a.episode/'events.jsonl').open() as f:events=[json.loads(l) for l in f]
    print(json.dumps(dict(metadata=meta,counts=dict(Counter(e['kind'] for e in events))),ensure_ascii=False,indent=2))
    if meta['status']=='saved' and not meta.get('queue_drops') and not meta.get('write_errors'):
        frames=list(aligned_frames(a.episode));valid=[f for f in frames if f is not None]
        print('grid_frames',len(frames),'missing_images',len(frames)-len(valid),'valid_counts',
              [sum(int(f['valid'][i]) for f in valid) for i in range(5)])
    if a.play:
        images=sorted((stamp_ns(e['header']['stamp']),e['path']) for e in events if e['kind']=='image')
        begin=time.monotonic()
        for stamp,path in images:
            target=begin+(stamp-images[0][0])/1e9
            while time.monotonic()<target:
                if cv2.waitKey(1)&255==ord('q'):cv2.destroyAllWindows();return
                time.sleep(.001)
            image=cv2.imread(str(a.episode/path))
            if image is None:raise ValueError('Missing image')
            cv2.imshow('Human demonstration: q to quit',image)
            if cv2.waitKey(1)&255==ord('q'):break
        cv2.destroyAllWindows()
if __name__=='__main__':main()
