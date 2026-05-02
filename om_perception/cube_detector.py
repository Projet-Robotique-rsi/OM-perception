#!/usr/bin/env python3
"""
Detects the 3 colored cubes by subscribing directly to the Gazebo
/world/pick_place/pose/info topic via gz-transport Python bindings.
Republishes cube poses on clean ROS2 topics for om_motion / om_mission.

Published topics:
  /cube_poses          (geometry_msgs/PoseArray)  — order: [red, green, blue]
  /cube_poses/red      (geometry_msgs/PoseStamped)
  /cube_poses/green    (geometry_msgs/PoseStamped)
  /cube_poses/blue     (geometry_msgs/PoseStamped)
"""

import threading

import gz.msgs10.pose_v_pb2 as pose_v_pb2
import gz.transport13 as gz_transport
import rclpy
from geometry_msgs.msg import Pose, PoseArray, PoseStamped
from rclpy.node import Node

CUBE_NAMES = ['red_cube', 'green_cube', 'blue_cube']
COLORS = ['red', 'green', 'blue']
GZ_TOPIC = '/world/pick_place/pose/info'


class CubeDetector(Node):

    def __init__(self):
        super().__init__('cube_detector')

        self._lock = threading.Lock()
        self._poses: dict[str, Pose | None] = {name: None for name in CUBE_NAMES}

        # Individual cube publishers
        self._pubs = {
            cube: self.create_publisher(PoseStamped, f'/cube_poses/{color}', 10)
            for cube, color in zip(CUBE_NAMES, COLORS)
        }
        self._array_pub = self.create_publisher(PoseArray, '/cube_poses', 10)

        # gz-transport subscriber (runs in its own thread)
        self._gz_node = gz_transport.Node()
        self._gz_node.subscribe(pose_v_pb2.Pose_V, GZ_TOPIC, self._gz_cb)

        self.create_timer(0.1, self._publish_cb)
        self.get_logger().info(f'CubeDetector: subscribed to {GZ_TOPIC}')

    def _gz_cb(self, pose_v: pose_v_pb2.Pose_V) -> None:
        with self._lock:
            for pose in pose_v.pose:
                if pose.name not in self._poses:
                    continue
                p = Pose()
                p.position.x = pose.position.x
                p.position.y = pose.position.y
                p.position.z = pose.position.z
                p.orientation.x = pose.orientation.x
                p.orientation.y = pose.orientation.y
                p.orientation.z = pose.orientation.z
                p.orientation.w = pose.orientation.w
                self._poses[pose.name] = p

    def _publish_cb(self) -> None:
        stamp = self.get_clock().now().to_msg()
        with self._lock:
            poses_snapshot = dict(self._poses)

        for cube, color in zip(CUBE_NAMES, COLORS):
            if poses_snapshot[cube] is None:
                continue
            ps = PoseStamped()
            ps.header.stamp = stamp
            ps.header.frame_id = 'world'
            ps.pose = poses_snapshot[cube]
            self._pubs[cube].publish(ps)

        if all(p is not None for p in poses_snapshot.values()):
            arr = PoseArray()
            arr.header.stamp = stamp
            arr.header.frame_id = 'world'
            arr.poses = [poses_snapshot[n] for n in CUBE_NAMES]
            self._array_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = CubeDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
