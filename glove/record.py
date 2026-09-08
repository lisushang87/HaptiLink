"""Read-only glove data logging + clock probes. Does not control a robot."""
import argparse
import json
from pathlib import Path
import secrets
import sys
import time
import serial
from glove.protocol import Parser, Unwrap, request
from glove.clock import ClockMap


def valid_sample_data(packet, duration):
    # Storage order is by channel name, not acquisition time: U6/U7
    # are interleaved with U10. Each timestamp must lie within the scan.
    offsets=packet['channel_offsets_us']; values=packet['values']
    return (len(values) in (6,22) and len(offsets)==len(values)
            and 0<=duration<=65535 and all(0<=v<=4095 for v in values)
            and all(0<=d<=duration for d in offsets))


def main():
    p = argparse.ArgumentParser(description='6/22通道手套数据记录和时钟同步；连接新固件，不连接机器人串口')
    p.add_argument('--port', required=True)
    p.add_argument('--hand', required=True, choices=['left', 'right'])
    p.add_argument('--baud', type=int, default=115200, help='匹配固件：22通道1000Hz用1500000；其余22通道或6通道1000Hz用921600；6通道100Hz用115200')
    p.add_argument('--output', type=Path, required=True, help='新JSONL文件，不覆盖')
    p.add_argument('--duration', type=float, default=0, help='秒；0为持续采集')
    p.add_argument('--sync-interval', type=float, default=.5)
    p.add_argument('--max-rtt', type=float, default=.1)
    p.add_argument('--ros', action='store_true', help='发布/glove/<hand>/sample和timing，std_msgs/String JSON')
    args = p.parse_args()
    if args.baud<=0 or args.duration<0 or args.sync_interval<.1 or args.max_rtt<=0:
        p.error('参数范围不合法；同步间隔至少0.1秒')
    if args.output.exists(): p.error('输出已存在，请使用新文件名')
    node = publisher = timing = None
    if args.ros:
        import rclpy
        from std_msgs.msg import String
        rclpy.init(args=[])
        node = rclpy.create_node('glove_'+args.hand+'_recorder')
        publisher = node.create_publisher(String, '/glove/'+args.hand+'/sample', 100)
        timing = node.create_publisher(String, '/glove/'+args.hand+'/timing', 10)
    parser = Parser()
    session = secrets.randbits(32) or 1
    clock, unwrap = ClockMap(max_rtt=args.max_rtt), Unwrap()
    pending = {}; number = 0; previous_seq = None; uid = None
    accepted_session = False
    start = next_sync = time.monotonic()
    last_report = last_packet = start
    wall_offset = time.time()-start
    received = gaps = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with serial.Serial(args.port,args.baud,timeout=.01,write_timeout=.2,exclusive=True) as port, args.output.open('x', buffering=1) as log:
            def emit(record):
                record['hand'] = args.hand
                line = json.dumps(record, allow_nan=False)
                log.write(line+'\n')
                if publisher is not None:
                    msg = String(); msg.data = line
                    (publisher if record['kind']=='sample' else timing).publish(msg)
            emit(dict(kind='metadata', protocol=1, port=args.port, baud=args.baud,
                      session=session, host_wall_ns=time.time_ns(), host_monotonic_ns=time.monotonic_ns(),
                      note='ADC counts are not calibrated joint angles; initial/expired sync has null aligned times'))
            while not args.duration or time.monotonic()-start<args.duration:
                now = time.monotonic()
                if node is not None:
                    rclpy.spin_once(node, timeout_sec=0)
                    if node.get_parameter('use_sim_time').value:
                        raise RuntimeError('实时串口采集不支持use_sim_time')
                if now >= next_sync:
                    number = (number+1)&0xffffffff
                    t1 = time.monotonic()
                    pending[number] = t1
                    port.write(request(session, number))
                    emit(dict(kind='sync_request', session=session, request=number, t1_monotonic_s=t1))
                    next_sync = now+args.sync_interval
                pending = {n:t for n,t in pending.items() if now-t<2}
                chunk = port.read(port.in_waiting or 1)
                t4 = time.monotonic()
                wall_now = time.time()
                new_offset = wall_now-t4
                if abs(new_offset-wall_offset)>.05:
                    emit(dict(kind='clock_jump', old_offset_s=wall_offset, new_offset_s=new_offset))
                    clock=ClockMap(max_rtt=args.max_rtt)
                wall_offset = new_offset
                if t4-last_packet > 30:
                    raise RuntimeError('超过30秒未收到有效帧：检查新固件、数据波特率、HC-05连接；重新开始会话')
                for packet in parser.feed(chunk):
                    last_packet=t4
                    if uid is not None and packet['uid']!=uid:
                        raise RuntimeError('串口设备UID改变，请新建记录会话')
                    uid = packet['uid']
                    packet.update(receive_monotonic_s=t4, receive_wall_ns=int(wall_now*1e9),
                                  parser_bad_frames=parser.bad_frames, parser_discarded_bytes=parser.discarded_bytes)
                    if packet['session']!=session:
                        if accepted_session:
                            session=secrets.randbits(32) or 1
                            clock, unwrap=ClockMap(max_rtt=args.max_rtt), Unwrap()
                            pending.clear(); previous_seq=None; accepted_session=False; next_sync=0
                            emit(dict(kind='device_reset', session=session, uid=uid))
                        packet['synchronized']=False
                        packet['valid_for_alignment']=False
                        emit(packet)
                        continue
                    accepted_session=True
                    if packet['kind']=='sync':
                        t1=pending.pop(packet['request'],None)
                        if t1 is not None:
                            t2=unwrap.extend(packet['t2_us'])/1e6
                            t3=unwrap.extend(packet['t3_us'])/1e6
                            accepted=clock.add(t1,t2,t3,t4)
                            packet.update(t1_monotonic_s=t1,t2_unwrapped_s=t2,t3_unwrapped_s=t3,accepted=accepted)
                        else:
                            packet['accepted']=False
                        packet['clock']=clock.quality(t4)
                    else:
                        received+=1
                        seq=packet['sequence']
                        delta=None if previous_seq is None else (seq-previous_seq)&0xffffffff
                        if delta is not None and delta>0x7fffffff:
                            raise RuntimeError('序号倒退，请重新开启会话')
                        packet['sequence_gap']=0 if delta is None else max(0,delta-1)
                        packet['duplicate']=delta==0
                        gaps+=packet['sequence_gap']; previous_seq=seq
                        begin=unwrap.extend(packet['start_us'])
                        end=unwrap.extend(packet['end_us'])
                        packet['start_unwrapped_us']=begin; packet['end_unwrapped_us']=end
                        quality=clock.quality(t4)
                        offsets=packet['channel_offsets_us']
                        valid_data=valid_sample_data(packet,end-begin)
                        packet['valid_data']=valid_data
                        packet['clock']=quality
                        channel=[clock.to_host((begin+d)/1e6,t4) for d in offsets]
                        packet['channel_monotonic_s']=channel
                        packet['channel_ros_ns']=[None if t is None else int((t+wall_offset)*1e9) for t in channel]
                        midpoint=clock.to_host((begin+end)/2e6,t4)
                        packet['sample_ros_ns']=None if midpoint is None else int((midpoint+wall_offset)*1e9)
                        packet['synchronized']=quality['valid']
                        packet['valid_for_alignment']=bool(valid_data and quality['valid'] and delta!=0)
                    emit(packet)
                if t4-last_report>=2:
                    print(f'{args.hand}: {received}包，累计序号缺口{gaps}，CRC/格式错误{parser.bad_frames}，同步={clock.quality(t4)}', flush=True)
                    last_report=t4
    except (serial.SerialException, OSError) as error:
        print(f'串口或日志访问失败：{error}', file=sys.stderr)
        print('请运行 /usr/bin/python3 -m serial.tools.list_ports -v 查看实际端口。'
              '若USB已识别CH340却没有ttyUSB节点，请检查内核日志中的ch341/brltty冲突。', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
            rclpy.shutdown()
    print(f'已保存 {args.output}；同步质量需实测验证，不是绝对误差保证。')


if __name__=='__main__':
    raise SystemExit(main())
