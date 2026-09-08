"""Compare stationary before/test/after recordings; not an absolute accuracy test."""
import argparse
import json
from pathlib import Path
import numpy as np


def measurements(rows, skip_s=2.):
    samples=[r for r in rows if r.get('kind')=='sample']
    if not samples:
        raise ValueError('No sample frames')
    samples=[r for r in samples if r['receive_monotonic_s']-samples[0]['receive_monotonic_s']>=skip_s
             and r.get('valid_data') and not r.get('duplicate',False)]
    if len(samples)<10:
        raise ValueError('Need at least 10 valid samples after warmup')
    layouts={(r['uid'],tuple(r['channel_names'])) for r in samples}
    if len(layouts)!=1:
        raise ValueError('Mixed devices or channel layouts')
    values=np.asarray([r['values'] for r in samples],dtype=float)
    return dict(layout=next(iter(layouts)),count=len(samples),median=np.median(values,axis=0),
                spread=np.percentile(values,95,axis=0)-np.percentile(values,5,axis=0))


def compare(before, experiment, after, skip_s=2.):
    a,b,c=[measurements(rows,skip_s) for rows in (before,experiment,after)]
    if not a['layout']==b['layout']==c['layout']:
        raise ValueError('Before/test/after must use same UID and channel layout')
    reference=(a['median']+c['median'])/2
    delta=b['median']-reference
    result=[]
    for i,name in enumerate(a['layout'][1]):
        result.append(dict(channel=name,before_median=float(a['median'][i]),
                           test_median=float(b['median'][i]),after_median=float(c['median'][i]),
                           test_minus_reference_counts=float(delta[i]),
                           difference_percent_full_scale=float(delta[i]/4095*100),
                           reference_drift_counts=float(c['median'][i]-a['median'][i]),
                           before_p95_p5=float(a['spread'][i]),test_p95_p5=float(b['spread'][i]),
                           after_p95_p5=float(c['spread'][i])))
    return dict(sample_counts=[a['count'],b['count'],c['count']],channels=result,
                max_absolute_difference_counts=float(np.max(np.abs(delta))),
                max_reference_drift_counts=float(np.max(np.abs(c['median']-a['median']))),
                warning='Relative stationary comparison only. Unknown input, motion, reference drift, supply changes and settling can confound results; no absolute accuracy certification.')


def main():
    p=argparse.ArgumentParser(description='静止输入前后慢速对照与高速读数比较；不是绝对精度认证')
    for name in ('before','test','after'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--skip-seconds',type=float,default=2)
    args=p.parse_args()
    if args.skip_seconds<0:p.error('skip-seconds must be nonnegative')
    rows=[]
    for path in (args.before,args.test,args.after):
        with path.open() as f:rows.append([json.loads(l) for l in f if l.strip()])
    print(json.dumps(compare(*rows,skip_s=args.skip_seconds),indent=2,ensure_ascii=False))


if __name__=='__main__':main()
