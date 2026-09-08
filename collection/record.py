"""ROS recording with bounded disk queue and explicit episode services."""
import json
import queue
import threading
import time
import uuid
from pathlib import Path
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rcl_interfaces.msg import ParameterDescriptor
from cv_bridge import CvBridge
from rosidl_runtime_py.convert import message_to_ordereddict
from .common import config, DEFAULT_CONFIG


class Recorder(Node):
    def __init__(self):
        super().__init__('human_recorder')
        self.declare_parameter('config',str(DEFAULT_CONFIG),ParameterDescriptor(read_only=True))
        self.cfg=config(self.get_parameter('config').value)
        self.declare_parameter('output_root',self.cfg['output_root'],ParameterDescriptor(read_only=True))
        self.declare_parameter('task','human demonstration')
        self.root=Path(self.get_parameter('output_root').value).resolve()
        self.bridge=CvBridge(); self.episode=None; self.cache={}; self.last_episode=None
        self.q=queue.Queue(maxsize=self.cfg['queue_size']); self.dropped=0; self.errors=[]
        self.worker=threading.Thread(target=self.write_loop,daemon=True);self.worker.start()
        self.subs=[]
        types=dict(image=Image,camera_info=CameraInfo,left_pose=PoseStamped,right_pose=PoseStamped,
                   left_glove=String,right_glove=String,left_timing=String,right_timing=String,odometry=Odometry)
        for key,topic in self.cfg['topics'].items():
            self.subs.append(self.create_subscription(types[key],topic,lambda msg,k=key:self.receive(k,msg),qos_profile_sensor_data))
        self.subs.append(self.create_subscription(TFMessage,'/tf',lambda m:self.receive('tf',m),100))
        self.subs.append(self.create_subscription(TFMessage,'/tf_static',lambda m:self.receive('tf_static',m),
            QoSProfile(depth=100,durability=DurabilityPolicy.TRANSIENT_LOCAL)))
        for name,callback in [('start',self.start),('stop',self.stop),('discard',self.discard)]:
            self.create_service(Trigger,'~/'+name,callback)
        self.get_logger().info('Ready: /human_recorder/start, stop, discard. No robot control.')

    def receive(self,key,msg):
        if key=='tf_static':
            for t in msg.transforms:self.cache[('tf_static',t.child_frame_id)]=t
        elif key=='camera_info':self.cache[key]=msg
        if self.episode is None:return
        try:self.q.put_nowait((self.episode,key,msg,time.time_ns(),time.monotonic_ns()))
        except queue.Full:self.dropped+=1

    def write_loop(self):
        while True:
            item=self.q.get()
            try:
                if item is None:return
                folder,key,msg,wall,mono=item
                event=dict(kind=key,receive_wall_ns=wall,receive_monotonic_ns=mono)
                if key=='image':
                    path='images/'+uuid.uuid4().hex+'.png'
                    if not cv2.imwrite(str(folder/path),self.bridge.imgmsg_to_cv2(msg,'bgr8')):raise OSError('Image write failed')
                    event.update(path=path,header=message_to_ordereddict(msg.header),width=msg.width,height=msg.height)
                elif isinstance(msg,String):event['data']=json.loads(msg.data)
                else:event['data']=message_to_ordereddict(msg)
                with (folder/'events.jsonl').open('a') as f:f.write(json.dumps(event,allow_nan=False)+'\n')
            except Exception as e:
                if len(self.errors)<20:self.errors.append(str(e))
            finally:self.q.task_done()

    def start(self,request,response):
        if self.episode is not None:response.message='Already recording';return response
        folder=self.root/(time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);(folder/'images').mkdir(parents=True)
        (folder/'events.jsonl').touch()
        self.dropped=0;self.errors=[];self.episode=folder
        metadata=dict(schema=1,task=self.get_parameter('task').value,status='recording',config=self.cfg,
                      started_wall_ns=time.time_ns(),glove_calibration='unverified_raw_adc',pose_origin='hexagonal_prism_center',
                      use_sim_time=bool(self.get_parameter('use_sim_time').value))
        repo=Path(__file__).resolve().parents[1]
        metadata['source_configs']={p:(repo/p).read_text() for p in ('config.yaml','rtabmap/config.yaml','STM32/src/USER/glove_config.h')}
        (folder/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False))
        for key,msg in list(self.cache.items()):
            if isinstance(key,tuple):self.receive('tf_static',TFMessage(transforms=[msg]))
            else:self.receive(key,msg)
        response.success=True;response.message=str(folder);return response

    def finish(self,status):
        folder=self.episode
        if folder is None:return None
        self.episode=None; self.q.join()
        path=folder/'metadata.json';meta=json.loads(path.read_text())
        meta.update(status=status,ended_wall_ns=time.time_ns(),queue_drops=self.dropped,write_errors=self.errors)
        path.write_text(json.dumps(meta,indent=2,ensure_ascii=False));self.last_episode=folder
        return folder

    def stop(self,request,response):
        folder=self.finish('saved');response.success=folder is not None;response.message=str(folder or 'Not recording');return response

    def discard(self,request,response):
        folder=self.finish('discarded') or self.last_episode
        if folder:
            path=folder/'metadata.json';meta=json.loads(path.read_text());meta['status']='discarded';path.write_text(json.dumps(meta,indent=2))
        response.success=folder is not None;response.message=str(folder or 'No episode')
        return response

    def close(self):
        self.finish('interrupted');self.q.put(None);self.worker.join()


def main():
    rclpy.init();node=Recorder()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.close();node.destroy_node();rclpy.shutdown()
if __name__=='__main__':main()
