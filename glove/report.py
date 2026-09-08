"""Summarize recorded rate, losses and synchronization diagnostics."""
import argparse
import json
from pathlib import Path
import numpy as np


def summary(rows):
    samples=[r for r in rows if r.get('kind')=='sample' and 'start_unwrapped_us' in r]
    periods=[]
    for a,b in zip(samples,samples[1:]):
        if (a['uid'],a['session'])==(b['uid'],b['session']) and (b['sequence']-a['sequence'])&0xffffffff==1:
            periods.append((b['start_unwrapped_us']-a['start_unwrapped_us'])/1000)
    def stats(values):
        return None if not values else dict(median=float(np.median(values)),p95=float(np.percentile(values,95)),p99=float(np.percentile(values,99)),maximum=float(max(values)))
    sync=[r for r in rows if r.get('kind')=='sync' and r.get('accepted')]
    rtts=[1000*((r['receive_monotonic_s']-r['t1_monotonic_s'])-(r['t3_unwrapped_s']-r['t2_unwrapped_s'])) for r in sync]
    all_samples=[r for r in rows if r.get('kind')=='sample']
    counter_increases={k:sum((b[k]-a[k]) & 0xffff for a,b in zip(all_samples,all_samples[1:]) if a['uid']==b['uid'] and ((b['sequence']-a['sequence']) & 0xffffffff)<0x80000000) for k in ('missed_ticks','tx_drops','rx_errors')}
    first_valid=next((i for i,r in enumerate(samples) if r.get('valid_for_alignment')),None)
    duration=(samples[-1]['receive_monotonic_s']-samples[0]['receive_monotonic_s']) if len(samples)>1 else 0
    return dict(parser_bad_frames=max((r.get('parser_bad_frames',0) for r in rows),default=0),
                parser_discarded_bytes=max((r.get('parser_discarded_bytes',0) for r in rows),default=0),
                device_counter_increases=counter_increases,adc_timeout_frames=sum(65535 in r.get('values',[]) for r in samples),
                invalid_after_first_alignment=None if first_valid is None else sum(not r.get('valid_for_alignment',False) for r in samples[first_valid:]),
                received_rate_hz=(len(samples)-1)/duration if duration>0 else None,
                sync_requests=sum(r.get('kind')=='sync_request' for r in rows),
                sync_responses=sum(r.get('kind')=='sync' for r in rows),
                channels=sorted({len(r["values"]) for r in samples}),samples=len(samples),valid_for_alignment=sum(r.get('valid_for_alignment',False) for r in samples),
                period_ms=stats(periods),rate_hz=None if not periods or np.mean(periods)<=0 else 1000/float(np.mean(periods)),
                scan_duration_ms=stats([(r['end_unwrapped_us']-r['start_unwrapped_us'])/1000 for r in samples]),
                sequence_gaps=sum(r.get('sequence_gap',0) for r in samples),
                last_device_counters=None if not samples else {k:samples[-1][k] for k in ('missed_ticks','tx_drops','rx_errors')},
                adjusted_rtt_ms=stats(rtts),last_clock=None if not samples else samples[-1]['clock'],
                warning='RTT/2 and fitting residual are not measured absolute synchronization error; verify with independent reference')


def main():
    p=argparse.ArgumentParser(description='统计手套记录实际采样间隔、扫描耗时、丢包和同步质量')
    p.add_argument('input',type=Path);args=p.parse_args()
    with args.input.open() as f:rows=[json.loads(line) for line in f if line.strip()]
    print(json.dumps(summary(rows),indent=2,ensure_ascii=False))


if __name__=='__main__':main()
