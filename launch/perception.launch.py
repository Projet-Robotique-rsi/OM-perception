#!/usr/bin/env python3
"""
Launch the perception stack.
Run AFTER om_description gazebo.launch.py is already up.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    cube_detector = Node(
        package='om_perception',
        executable='cube_detector',
        name='cube_detector',
        output='screen',
    )

    return LaunchDescription([cube_detector])
