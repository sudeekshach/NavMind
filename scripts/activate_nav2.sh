#!/bin/bash
echo "Waiting for Nav2 nodes..."
sleep 5

echo "Activating map_server..."
ros2 lifecycle set /map_server activate

echo "Activating amcl..."
ros2 lifecycle set /amcl configure
ros2 lifecycle set /amcl activate

echo "Setting initial pose..."
ros2 topic pub /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
"{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}, covariance: [0.25, 0, 0, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.068]}}" --once

echo "Done! Nav2 ready."
