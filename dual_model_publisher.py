#!/usr/bin/env python3
"""
Dual-Model Gesture Publisher
Uses two YOLO models simultaneously:
  - Model 1 (best.pt): Basic gestures (up, down, left, right, stop)
  - Model 2 (best2.pt): Advanced gestures (fist, ok)

Author: Your Name
Date: 2026-05-08
"""

import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ultralytics import YOLO


class DualModelGesturePublisher(Node):
    """
    Publisher that uses two YOLO models simultaneously
    """

    def __init__(self):
        super().__init__("dual_model_gesture_publisher")

        # Publisher for gesture commands
        self.publisher_ = self.create_publisher(
            String,
            "/gesture/command",
            10
        )

        # Load BOTH models
        self.get_logger().info("Loading Model 1 (basic gestures)...")
        self.model1 = YOLO("/root/best.pt")  # Basic: up, down, left, right, stop
        self.get_logger().info(f"  Model 1 classes: {list(self.model1.names.values())}")

        self.get_logger().info("Loading Model 2 (advanced gestures)...")
        self.model2 = YOLO("/root/best2.pt")  # Advanced: fist, ok
        self.get_logger().info(f"  Model 2 classes: {list(self.model2.names.values())}")

        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Timer for detection (20 Hz)
        self.timer = self.create_timer(0.05, self.timer_callback)

        # State tracking
        self.last_command = "none"

        self.get_logger().info("="*60)
        self.get_logger().info("Dual-Model Gesture Publisher Started!")
        self.get_logger().info("="*60)
        self.get_logger().info("Model 1 (basic): up, down, left, right, stop")
        self.get_logger().info("Model 2 (advanced): fist, ok")
        self.get_logger().info("="*60)

    def timer_callback(self):
        """
        Main detection loop - runs both models on each frame
        """
        ret, frame = self.cap.read()
        if not ret:
            return

        # Run BOTH models on the same frame
        results1 = self.model1(frame, verbose=False, imgsz=320)[0]
        results2 = self.model2(frame, verbose=False, imgsz=320)[0]

        # Find best detection from Model 1 (basic gestures)
        best_conf1 = 0.0
        command1 = None
        box1 = None

        for box in results1.boxes:
            conf = float(box.conf[0])
            if conf < 0.30:  # Confidence threshold
                continue

            class_id = int(box.cls[0])
            class_name = self.model1.names[class_id]

            if conf > best_conf1:
                best_conf1 = conf
                command1 = class_name
                box1 = box

        # Find best detection from Model 2 (advanced gestures)
        best_conf2 = 0.0
        command2 = None
        box2 = None

        for box in results2.boxes:
            conf = float(box.conf[0])
            if conf < 0.30:  # Confidence threshold
                continue

            class_id = int(box.cls[0])
            class_name = self.model2.names[class_id]

            if conf > best_conf2:
                best_conf2 = conf
                command2 = class_name
                box2 = box

        # Decide which command to use (highest confidence wins)
        final_command = "none"
        final_box = None
        final_conf = 0.0
        model_used = None

        if best_conf1 > best_conf2:
            # Model 1 (basic) has higher confidence
            if command1:
                final_command = command1
                final_box = box1
                final_conf = best_conf1
                model_used = "Model 1"
        else:
            # Model 2 (advanced) has higher confidence
            if command2:
                final_command = command2
                final_box = box2
                final_conf = best_conf2
                model_used = "Model 2"

        # Draw bounding box for the winning detection
        if final_box is not None:
            x1, y1, x2, y2 = map(int, final_box.xyxy[0])
            
            # Different colors for different models
            if model_used == "Model 1":
                color = (0, 255, 0)  # Green for basic gestures
            else:
                color = (255, 0, 255)  # Magenta for advanced gestures
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            label = f"{final_command} {final_conf:.2f} [{model_used}]"
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        # Publish command if it changed
        if final_command != self.last_command:
            msg = String()
            msg.data = final_command

            self.publisher_.publish(msg)

            if final_command != "none":
                self.get_logger().info(
                    f"Published: {final_command} (conf: {final_conf:.2f}, {model_used})"
                )

            self.last_command = final_command

        # Display frame
        cv2.imshow("Dual-Model Gesture Detection", frame)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            raise KeyboardInterrupt

    def destroy_node(self):
        """
        Cleanup
        """
        self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    """
    Main function
    """
    rclpy.init(args=args)

    node = DualModelGesturePublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
