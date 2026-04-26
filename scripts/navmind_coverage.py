import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from action_msgs.msg import GoalStatus
import math

ROOMS = {
    "living room": {
        "x": 0.0,  "y": 0.0,
        "x1": -1.35, "y1": -1.91,
        "x2":  0.76, "y2":  2.13
    },
    "dining room": {
        "x": 3.93, "y": 0.79,
        "x1":  1.03, "y1": -3.00,
        "x2":  5.87, "y2":  2.17
    },
    "kitchen": {
        "x": 7.51, "y": 0.67,
        "x1":  6.14, "y1": -1.98,
        "x2":  8.14, "y2":  2.05
    },
    "study": {
        "x": 10.85, "y": -1.90,
        "x1":  8.51, "y1": -3.13,
        "x2": 13.42, "y2":  2.04
    },
    "bedroom": {
        "x": 12.0, "y": -5.90,
        "x1": 10.91, "y1": -8.30,
        "x2": 13.31, "y2": -3.53
    },
    "guest room": {
        "x": -0.49, "y": -4.46,
        "x1": -1.1,  "y1": -6.78,
        "x2":  0.50, "y2": -2.20
    },
}

HOME_X = 0.0
HOME_Y = 0.0
STRIP_WIDTH = 0.35
MARGIN = 0.1

class NavMindCoverage(Node):
    def __init__(self):
        super().__init__('navmind_coverage')
        self._action_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose')

        # Trail publisher
        qos = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.trail_pub = self.create_publisher(Path, '/coverage_trail', qos)
        self.trail = Path()
        self.trail.header.frame_id = 'map'

        # Subscribe to AMCL pose
        self.pose_sub = self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self.pose_callback,
            10
        )

        self.get_logger().info('NavMind Coverage Node started!')

    def pose_callback(self, msg):
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = msg.header.stamp
        pose.pose = msg.pose.pose
        self.trail.poses.append(pose)
        self.trail.header.stamp = self.get_clock().now().to_msg()
        self.trail_pub.publish(self.trail)

    def navigate_to(self, x, y, yaw=0.0):
        self.get_logger().info(f'Navigating to ({x:.2f}, {y:.2f})')

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation.z = math.sin(yaw / 2)
        goal.pose.pose.orientation.w = math.cos(yaw / 2)

        self._action_client.wait_for_server()
        future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected!')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        status = result_future.result().status
        success = status == GoalStatus.STATUS_SUCCEEDED
        if success:
            self.get_logger().info('Goal reached!')
        else:
            self.get_logger().warn(f'Goal failed with status: {status}')
        return success

    def generate_coverage_waypoints(self, room):
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
        if room_name not in ROOMS:
            self.get_logger().error(f'Unknown room: {room_name}')
            return False

        room = ROOMS[room_name]
        self.get_logger().info(f'Heading to {room_name}...')

        success = self.navigate_to(room['x'], room['y'])
        if not success:
            self.get_logger().error(f'Failed to reach {room_name}!')
            return False

        self.get_logger().info(f'Starting coverage of {room_name}...')

        waypoints = self.generate_coverage_waypoints(room)
        total = len(waypoints)

        for i, (wx, wy) in enumerate(waypoints):
            self.get_logger().info(
                f'Waypoint {i+1}/{total}: ({wx:.2f}, {wy:.2f})')
            self.navigate_to(wx, wy)

        self.get_logger().info(f'Coverage of {room_name} complete!')

        # Return to home
        self.get_logger().info('Returning to home position...')
        self.navigate_to(HOME_X, HOME_Y)
        self.get_logger().info('Back home!')

        return True

def main():
    rclpy.init()
    node = NavMindCoverage()

    room_to_cover = "living room"
    node.get_logger().info(f'NavMind: Covering {room_to_cover}')
    node.cover_room(room_to_cover)

    rclpy.shutdown()

if __name__ == '__main__':
    main()
