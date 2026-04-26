import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped

class TFFix(Node):
    def __init__(self):
        super().__init__('tf_fix')
        
        # Use sim time
        self.set_parameters([Parameter('use_sim_time', 
                                       Parameter.Type.BOOL, True)])

        # Republish scan with correct frame
        self.scan_pub = self.create_publisher(LaserScan, '/scan_fixed', 10)
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        
        # Publish dynamic TF from odom
        self.tf_broadcaster = TransformBroadcaster(self)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        
        # Static transforms
        self.static_broadcaster = StaticTransformBroadcaster(self)
        
        # base_link -> base_scan
        static_tf = TransformStamped()
        static_tf.header.stamp = self.get_clock().now().to_msg()
        static_tf.header.frame_id = 'base_link'
        static_tf.child_frame_id = 'base_scan'
        static_tf.transform.translation.x = -0.032
        static_tf.transform.translation.y = 0.0
        static_tf.transform.translation.z = 0.171
        static_tf.transform.rotation.w = 1.0

        # map -> odom (identity, SLAM will update this)
        static_tf2 = TransformStamped()
        static_tf2.header.stamp = self.get_clock().now().to_msg()
        static_tf2.header.frame_id = 'map'
        static_tf2.child_frame_id = 'odom'
        static_tf2.transform.rotation.w = 1.0

        self.static_broadcaster.sendTransform([static_tf, static_tf2])
        self.get_logger().info('TF Fix node started!')

    def scan_callback(self, msg):
        msg.header.frame_id = 'base_scan'
        self.scan_pub.publish(msg)

    def odom_callback(self, msg):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation
        self.tf_broadcaster.sendTransform(t)

def main():
    rclpy.init()
    node = TFFix()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
