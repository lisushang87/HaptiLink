"""Offline interpolation at video/pose ROS timestamps. Never extrapolate."""
import argparse
import bisect
import json
from pathlib import Path


def align(records, target_ns, max_gap_ms=30):
    """Return six or 22 ADC values or None; independent per-channel acquisition times.

    Future samples are allowed here: this is an offline label/measurement tool,
    not a causal deployment observation builder. Never cross sessions/gaps.
    """
    records=list(records)
    widths={len(r['values']) for r in records if r.get('kind')=='sample'}
    if len(widths)>1 or (widths and not widths.issubset({6,22})):
        raise ValueError('Cannot mix channel layouts in one alignment input')
    channels=next(iter(widths),6)
    streams=[[] for _ in range(channels)]
    for row in records:
        if row.get('kind')!='sample' or not row.get('valid_for_alignment'):
            continue
        if len(row['channel_ros_ns'])!=channels: raise ValueError('Channel timestamp count mismatch')
        for index,(t,v) in enumerate(zip(row['channel_ros_ns'], row['values'])):
            if t is not None:
                streams[index].append((t,float(v),(row['uid'],row['session']),row['sequence']))
    for stream in streams: stream.sort(key=lambda x:x[0])
    times=[[v[0] for v in stream] for stream in streams]
    output=[]
    for t in target_ns:
        values=[]; sessions=[]
        for stream,ts in zip(streams,times):
            j=bisect.bisect_left(ts,t)
            if j<len(ts) and ts[j]==t:
                values.append(stream[j][1]); sessions.append(stream[j][2]); continue
            if j==0 or j==len(ts): break
            left,right=stream[j-1],stream[j]
            if (right[0]-left[0]>max_gap_ms*1e6 or left[2]!=right[2]
                    or (right[3]-left[3])&0xffffffff != 1): break
            a=(t-left[0])/(right[0]-left[0])
            values.append(left[1]+a*(right[1]-left[1])); sessions.append(left[2])
        valid=len(values)==channels and len(set(sessions))==1
        output.append(dict(timestamp_ns=t,valid=valid,adc=values if valid else None))
    return output


def main():
    p=argparse.ArgumentParser(description='离线按图像原始ROS纳秒时间戳对齐手套ADC；不外推、不跨丢包')
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--timestamps',type=Path,required=True,help='每行一个图像header时间戳（整数纳秒）')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-gap-ms',type=float,default=30)
    args=p.parse_args()
    if args.max_gap_ms<=0:p.error('max-gap-ms必须为正数')
    with args.input.open() as f:rows=[json.loads(line) for line in f if line.strip()]
    targets=[int(line) for line in args.timestamps.read_text().splitlines() if line.strip()]
    with args.output.open('x') as f:
        for row in align(rows,targets,args.max_gap_ms):f.write(json.dumps(row)+'\n')


if __name__=='__main__':main()
