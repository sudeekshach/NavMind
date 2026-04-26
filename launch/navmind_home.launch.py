import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    config_dir = os.path.join(os.path.expanduser('~'), 'navmind', 'config')
    maps_dir = os.path.join(os.path.expanduser('~'), 'navmind', 'maps')

    # Robot state publisher
    urdf_file = os.path.join(os.path.expanduser('~'), 'navmind/config/turtlebot3_burger.urdf')
    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}],
        output='screen'
    )

    # Map server
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        parameters=[{
            'use_sim_time': True,
            'yaml_filename': os.path.join(maps_dir, 'house_map.yaml')
        }],
        output='screen'
    )

    # AMCL for localization
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        parameters=[
            os.path.join(config_dir, 'nav2_params.yaml'),
            {'use_sim_time': True}
        ],
        output='screen'
    )

    # Lifecycle manager for localization (map_server + amcl)
    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server', 'amcl']
        }],
        output='screen'
    )

    # Nav2 navigation
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'params_file': os.path.join(config_dir, 'nav2_params.yaml'),
        }.items()
    )

    return LaunchDescription([
        robot_state_publisher,
        map_server,
        amcl,
        lifecycle_manager_localization,
        nav2,
    ])
