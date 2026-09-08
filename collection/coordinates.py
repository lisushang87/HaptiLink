"""Pose output for external teleoperation adapters. No robot commands or IK."""
import json
import math
import copy
import time
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import SetParametersResult, ParameterDescriptor
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String, Bool
from tf2_ros import Buffer, TransformListener, TransformException
from .common import config, DEFAULT_CONFIG


def transformed(msg,transform,target):
    result=copy.deepcopy(msg);p=msg.pose.position;q=msg.pose.orientation
    values=[p.x,p.y,p.z,q.x,q.y,q.z,q.w]
    if not all(math.isfinite(x) for x in values) or sum(x*x for x in values[3:])<1e-12:raise ValueError('invalid pose')
    source=Rotation.from_quat(values[3:])
    if transform is not None:
        t=transform.transform;rot=Rotation.from_quat([t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])
        xyz=rot.apply(values[:3])+np.array([t.translation.x,t.translation.y,t.translation.z]);quat=(rot*source).as_quat()
    else:xyz=np.array(values[:3]);quat=source.as_quat()
    if not np.all(np.isfinite(xyz)):raise ValueError('invalid transform')
    result.header.frame_id=target
    result.pose.position.x,result.pose.position.y,result.pose.position.z=map(float,xyz)
    result.pose.orientation.x,result.pose.orientation.y,result.pose.orientation.z,result.pose.orientation.w=map(float,quat)
    return result


class Coordinates(Node):
    def __init__(self):
        super().__init__('human_coordinates')
        self.declare_parameter('config',str(DEFAULT_CONFIG),ParameterDescriptor(read_only=True))
        cfg=config(self.get_parameter('config').value);self.cfg=cfg['teleop'];self.poses={};self.last={};self.valid={};self.epoch=0;self.previous_now=None
        self.declare_parameter('movement_enabled',self.cfg['movement_enabled'])
        for key in ('world_frame','camera_frame','max_age_s','future_tolerance_s'):
            self.declare_parameter(key,self.cfg[key],ParameterDescriptor(read_only=True))
        self.cfg={key:self.get_parameter(key).value for key in ('world_frame','camera_frame','max_age_s','future_tolerance_s')}
        self.add_on_set_parameters_callback(self.change)
        self.buffer=Buffer(cache_time=Duration(seconds=10));self.listener=TransformListener(self.buffer,self)
        self.pubs={k:self.create_publisher(PoseStamped,'/teleop/'+k+'/pose',10) for k in ('left','right','camera')}
        self.status=self.create_publisher(String,'/teleop/status',10)
        self.enabled=self.create_publisher(Bool,'/teleop/movement_enabled',10)
        self.subs=[self.create_subscription(PoseStamped,cfg['topics'][k+'_pose'],lambda m,k=k:self.receive(k,m),qos_profile_sensor_data) for k in ('left','right')]
        self.subs.append(self.create_subscription(Odometry,cfg['topics']['odometry'],self.odom,qos_profile_sensor_data))
        self.create_timer(.02,self.tick)

    def change(self,params):
        for p in params:
            if p.name=='movement_enabled' and type(p.value) is not bool:return SetParametersResult(successful=False,reason='Boolean required')
        if any(p.name=='movement_enabled' for p in params):
            self.poses.clear();self.last.clear();self.valid.clear();self.epoch+=1
        return SetParametersResult(successful=True)

    def receive(self,key,msg):
        self.poses[key]=(msg,time.monotonic())

    def odom(self,msg):
        if not math.isfinite(msg.pose.covariance[0]) or not 0<=msg.pose.covariance[0]<9999:
            self.poses.pop('camera',None);self.valid.pop('camera',None);return
        self.receive('camera',msg)

    def tick(self):
        moving=self.get_parameter('movement_enabled').value
        target=self.get_parameter('world_frame' if moving else 'camera_frame').value
        now=self.get_clock().now().nanoseconds;mono=time.monotonic();max_age=self.cfg['max_age_s'];future=self.cfg['future_tolerance_s']
        if self.previous_now is not None and now<self.previous_now:
            self.poses.clear();self.last.clear();self.epoch+=1
        self.previous_now=now
        validity={k:False for k in self.pubs}
        reasons={}
        for key in self.pubs:
            if key=='camera' and not moving:reasons[key]='movement_disabled';continue
            entry=self.poses.get(key)
            if entry is None:reasons[key]='missing';continue
            msg,received=entry;stamp=Time.from_msg(msg.header.stamp);age=(now-stamp.nanoseconds)/1e9
            if not -future<=age<=max_age or mono-received>max_age:reasons[key]='stale';continue
            if stamp.nanoseconds<self.last.get(key,0):reasons[key]='out_of_order';continue
            try:
                if key=='camera':
                    source=self.cfg['camera_frame']
                    pose=PoseStamped();pose.header=copy.deepcopy(msg.header);pose.header.frame_id=source;pose.pose.orientation.w=1.
                else:pose=msg;source=msg.header.frame_id
                if not source or stamp.nanoseconds<=0:raise ValueError('missing frame/stamp')
                tf=None if source==target else self.buffer.lookup_transform(target,source,stamp)
                result=transformed(pose,tf,target)
                validity[key]=True
                if self.last.get(key)!=stamp.nanoseconds:
                    self.pubs[key].publish(result);self.last[key]=stamp.nanoseconds
            except (TransformException,ValueError) as error:reasons[key]=str(error)
        self.enabled.publish(Bool(data=moving))
        self.status.publish(String(data=json.dumps(dict(stamp_ns=now,movement_enabled=moving,frame_id=target,
            mode_epoch=self.epoch,valid=validity,reasons=reasons,pose_origin='hexagonal_prism_center',
            robot_control_enabled=False))))


def main():
    rclpy.init();node=Coordinates()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.shutdown()
if __name__=='__main__':main()
