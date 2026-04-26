import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from action_msgs.msg import GoalStatus
import requests
import math
import threading
import time

OLLAMA_URL = "http://172.18.208.1:11434/api/generate"
MODEL = "llama3.2:1b"

ROOMS = {
    "living room": {"x": 0.0,   "y": 0.0,   "x1": -1.35, "y1": -1.91, "x2": 0.76,  "y2": 2.13},
    "dining room": {"x": 3.93,  "y": 0.79,  "x1": 1.03,  "y1": -3.00, "x2": 5.87,  "y2": 2.17},
    "kitchen":     {"x": 7.51,  "y": 0.67,  "x1": 6.14,  "y1": -1.98, "x2": 8.14,  "y2": 2.05},
    "study":       {"x": 10.85, "y": -1.90, "x1": 8.51,  "y1": -3.13, "x2": 13.42, "y2": 2.04},
    "bedroom":     {"x": 12.0,  "y": -5.90, "x1": 10.91, "y1": -8.30, "x2": 13.31, "y2": -3.53},
    "guest room":  {"x": -0.49, "y": -4.46, "x1": -1.1,  "y1": -6.78, "x2": 0.50,  "y2": -2.20},
}

HOME_X = 0.0
HOME_Y = 0.0
STRIP_WIDTH = 0.35
MARGIN = 0.1

def ask_llm(prompt):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"LLM error: {e}"

class NavMindNode(Node):
    def __init__(self):
        super().__init__('navmind_node')
        self.cb_group = ReentrantCallbackGroup()
        
        self._action_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose',
            callback_group=self.cb_group)

        self.cmd_sub = self.create_subscription(
            String, '/navmind/command', self.command_callback, 10,
            callback_group=self.cb_group)
        self.status_pub = self.create_publisher(String, '/navmind/status', 10)
        self.commentary_pub = self.create_publisher(String, '/navmind/commentary', 10)

        self.task_queue = []
        self.is_busy = False
        self.lock = threading.Lock()

        self.get_logger().info('NavMind Node ready! Waiting for commands...')

    def publish_status(self, status):
        msg = String()
        msg.data = status
        self.status_pub.publish(msg)
        self.get_logger().info(f'Status: {status}')

    def publish_commentary(self, text):
        msg = String()
        msg.data = text
        self.commentary_pub.publish(msg)
        self.get_logger().info(f'🤖 {text}')

    def command_callback(self, msg):
        room_name = msg.data.lower().strip()
        if room_name in ROOMS:
            self.get_logger().info(f'Received command: clean {room_name}')
            with self.lock:
                self.task_queue.append(room_name)
            self.publish_status(f'queued:{room_name}')
            if not self.is_busy:
                thread = threading.Thread(
                    target=self.process_tasks, daemon=True)
                thread.start()
        else:
            self.get_logger().warn(f'Unknown room: {room_name}')

    def process_tasks(self):
        with self.lock:
            if self.is_busy:
                return
            self.is_busy = True
        
        while True:
            with self.lock:
                if not self.task_queue:
                    self.is_busy = False
                    break
                room_name = self.task_queue.pop(0)
            self.cover_room(room_name)

    def navigate_to(self, x, y, yaw=0.0):
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation.z = math.sin(yaw / 2)
        goal.pose.pose.orientation.w = math.cos(yaw / 2)

        self._action_client.wait_for_server()
        send_future = self._action_client.send_goal_async(goal)
        
        while not send_future.done():
            time.sleep(0.05)
        
        goal_handle = send_future.result()
        if not goal_handle.accepted:
            return False

        result_future = goal_handle.get_result_async()
        
        while not result_future.done():
            time.sleep(0.05)

        return result_future.result().status == GoalStatus.STATUS_SUCCEEDED

    def generate_waypoints(self, room):
        x1 = room['x1'] + MARGIN
        x2 = room['x2'] - MARGIN
        y1 = room['y1'] + MARGIN
        y2 = room['y2'] - MARGIN
        waypoints = []
        y = y1
        direction = 1
        while y <= y2:
            if direction == 1:
                waypoints.append((x1, y))
                waypoints.append((x2, y))
            else:
                waypoints.append((x2, y))
                waypoints.append((x1, y))
            y += STRIP_WIDTH
            direction *= -1
        return waypoints

    def cover_room(self, room_name):
        room = ROOMS[room_name]

        self.publish_status(f'navigating:{room_name}')
        commentary = ask_llm(f"You are NavMind robot. One sentence: heading to clean the {room_name}.")
        self.publish_commentary(commentary)

        success = self.navigate_to(room['x'], room['y'])
        if not success:
            self.publish_status(f'failed:{room_name}')
            return

        self.publish_status(f'covering:{room_name}')
        commentary = ask_llm(f"You are NavMind robot. One sentence: arrived at {room_name}, starting systematic cleaning.")
        self.publish_commentary(commentary)

        waypoints = self.generate_waypoints(room)
        total = len(waypoints)

        for i, (wx, wy) in enumerate(waypoints):
            self.navigate_to(wx, wy)
            if (i + 1) % 5 == 0:
                commentary = ask_llm(f"You are NavMind robot. One sentence: cleaning {room_name}, {i+1} of {total} waypoints done.")
                self.publish_commentary(commentary)

        self.publish_status(f'complete:{room_name}')
        commentary = ask_llm(f"You are NavMind robot. One sentence: finished cleaning {room_name}, returning home.")
        self.publish_commentary(commentary)

        self.navigate_to(HOME_X, HOME_Y)
        self.publish_status('idle')

def main():
    rclpy.init()
    node = NavMindNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.spin()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
