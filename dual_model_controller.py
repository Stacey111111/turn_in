#!/usr/bin/env python3
"""
Unified Gesture Controller - Handles ALL 7 gestures
统一手势控制器 - 处理全部7个手势

Gestures:
  Basic (5):
    - up, down, left, right, stop
  Advanced (2):
    - fist (zigzag pattern)
    - ok (circle movement)

Author: Your Name
Date: 2026-05-08
"""

import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration


class UnifiedGestureController(Node):
    """
    Unified controller handling all 7 gestures
    """

    def __init__(self):
        super().__init__("unified_gesture_controller")

        # Subscribe to gesture commands
        self.subscription = self.create_subscription(
            String,
            "/gesture/command",
            self.command_callback,
            10
        )

        # Publish velocity commands
        self.cmd_pub = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        # Arm action client
        self.arm_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory"
        )

        # State tracking
        self.last_command = ""
        self.is_executing = False  # Prevent action overlap for complex movements

        self.get_logger().info("="*60)
        self.get_logger().info("Unified Gesture Controller Started!")
        self.get_logger().info("="*60)
        self.get_logger().info("Supported gestures:")
        self.get_logger().info("  Basic movements:")
        self.get_logger().info("    up    - Move forward")
        self.get_logger().info("    down  - Move backward")
        self.get_logger().info("    left  - Turn left")
        self.get_logger().info("    right - Turn right")
        self.get_logger().info("    stop  - Stop and wave")
        self.get_logger().info("  Advanced patterns:")
        self.get_logger().info("    fist  - Zigzag pattern")
        self.get_logger().info("    ok    - Circle movement")
        self.get_logger().info("="*60)

    # ========================================================================
    # BASIC ROBOT CONTROL
    # ========================================================================

    def stop_robot(self):
        """Stop the robot"""
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.cmd_pub.publish(twist)

    # ========================================================================
    # ARM CONTROL
    # ========================================================================

    def send_arm_goal(self, positions, duration_sec=1.5):
        """Send arm movement goal"""
        if not self.arm_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn("Arm action server not available")
            return

        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory.joint_names = [
            "joint1", "joint2", "joint3", "joint4"
        ]

        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start = Duration(
            sec=int(duration_sec),
            nanosec=int((duration_sec % 1.0) * 1e9)
        )

        goal_msg.trajectory.points.append(point)
        self.arm_client.send_goal_async(goal_msg)

    def wave_arm(self):
        """Wave arm motion"""
        self.get_logger().info("Waving arm")

        wave_left = [0.8, -0.5, 0.3, 0.2]
        wave_right = [-0.8, -0.5, 0.3, 0.2]
        home = [0.0, 0.0, 0.0, 0.0]

        for _ in range(3):
            self.send_arm_goal(wave_left)
            time.sleep(1.5)
            self.send_arm_goal(wave_right)
            time.sleep(1.5)

        self.send_arm_goal(home)

    # ========================================================================
    # ADVANCED MOVEMENT PATTERNS
    # ========================================================================

    def zigzag_movement(self):
        """
        Zigzag movement pattern
        Forward+Left -> Forward+Right -> Forward+Left -> ...
        """
        self.get_logger().info("Executing zigzag pattern!")
        self.is_executing = True

        try:
            linear_speed = 0.12   # m/s
            angular_speed = 0.4   # rad/s
            duration = 1.0        # seconds per segment
            cycles = 3            # number of zigzags

            for i in range(cycles):
                self.get_logger().info(f"  Zigzag {i+1}/{cycles}")

                # Segment 1: Forward + Turn left
                twist = Twist()
                twist.linear.x = linear_speed
                twist.angular.z = angular_speed

                start_time = time.time()
                while time.time() - start_time < duration:
                    self.cmd_pub.publish(twist)
                    time.sleep(0.1)

                # Segment 2: Forward + Turn right
                twist = Twist()
                twist.linear.x = linear_speed
                twist.angular.z = -angular_speed

                start_time = time.time()
                while time.time() - start_time < duration:
                    self.cmd_pub.publish(twist)
                    time.sleep(0.1)

            self.stop_robot()
            self.get_logger().info("Zigzag complete!")

        except Exception as e:
            self.get_logger().error(f"Zigzag error: {e}")
            self.stop_robot()

        finally:
            self.is_executing = False

    def circle_movement(self):
        """
        Circle movement pattern
        Continuous forward + Continuous left turn = Circle
        """
        self.get_logger().info("Executing circle movement!")
        self.is_executing = True

        try:
            linear_speed = 0.12   # m/s
            angular_speed = 0.5   # rad/s
            duration = 6.3        # seconds (one full circle)

            radius = linear_speed / angular_speed
            self.get_logger().info(f"  Circle radius approximately {radius:.2f} m")

            twist = Twist()
            twist.linear.x = linear_speed
            twist.angular.z = angular_speed

            start_time = time.time()
            while time.time() - start_time < duration:
                self.cmd_pub.publish(twist)
                time.sleep(0.1)

            self.stop_robot()
            self.get_logger().info("Circle complete!")

        except Exception as e:
            self.get_logger().error(f"Circle error: {e}")
            self.stop_robot()

        finally:
            self.is_executing = False

    # ========================================================================
    # MAIN COMMAND CALLBACK
    # ========================================================================

    def command_callback(self, msg):
        """
        Main gesture command handler
        Routes gestures to appropriate functions
        """
        command = msg.data.lower()

        # Ignore duplicate commands
        if command == self.last_command:
            return

        # Ignore new commands while executing complex movements
        if self.is_executing:
            self.get_logger().warn(f"Currently executing, ignoring: {command}")
            return

        self.last_command = command
        self.get_logger().info(f"Received command: {command}")

        # Create twist message for basic movements
        twist = Twist()

        # ====================================================================
        # BASIC MOVEMENTS
        # ====================================================================

        if command == "up":
            # Move forward
            twist.linear.x = 0.15
            self.cmd_pub.publish(twist)
            self.get_logger().info("Moving forward")

        elif command == "down":
            # Move backward
            twist.linear.x = -0.15
            self.cmd_pub.publish(twist)
            self.get_logger().info("Moving backward")

        elif command == "left":
            # Turn left
            twist.angular.z = 0.7
            self.cmd_pub.publish(twist)
            self.get_logger().info("Turning left")

        elif command == "right":
            # Turn right
            twist.angular.z = -0.7
            self.cmd_pub.publish(twist)
            self.get_logger().info("Turning right")

        elif command == "stop":
            # Stop and wave
            self.stop_robot()
            self.wave_arm()
            self.get_logger().info("Stopped and waving")

        # ====================================================================
        # ADVANCED PATTERNS
        # ====================================================================

        elif command == "fist":
            # Zigzag pattern
            self.zigzag_movement()

        elif command == "ok":
            # Circle movement
            self.circle_movement()

        # ====================================================================
        # UNKNOWN COMMAND
        # ====================================================================

        else:
            # Unknown gesture - stop robot
            self.stop_robot()
            self.get_logger().debug(f"Unknown command: {command}")


def main(args=None):
    """Main function"""
    rclpy.init(args=args)

    node = UnifiedGestureController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Received exit signal")
    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
