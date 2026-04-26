import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
import math
import os

RESOLUTION = 0.05  # meters per pixel
PADDING = 1.0

FURNITURE = [
    # Solid obstacles
    {'name': 'Mailbox',       'x': 0.883,  'y': -0.576, 'w': 0.4,  'd': 0.4,  'yaw': 3.14},
    {'name': 'bookshelf',     'x': -6.544, 'y': 5.195,  'w': 0.9,  'd': 0.3,  'yaw': 0},
    {'name': 'bookshelf_0',   'x': 4.724,  'y': 5.179,  'w': 0.9,  'd': 0.3,  'yaw': 0},
    {'name': 'bookshelf_1',   'x': 5.645,  'y': 5.179,  'w': 0.9,  'd': 0.3,  'yaw': 0},
    {'name': 'cabinet',       'x': -5.472, 'y': -1.576, 'w': 0.9,  'd': 0.45, 'yaw': 0},
    {'name': 'cabinet_0',     'x': -5.473, 'y': -2.065, 'w': 0.9,  'd': 0.45, 'yaw': 0},
    {'name': 'cabinet_1',     'x': -7.184, 'y': 1.248,  'w': 0.9,  'd': 0.45, 'yaw': 1.5708},
    {'name': 'trash_can',     'x': 1.883,  'y': 1.912,  'w': 0.35, 'd': 0.35, 'yaw': 0},
    {'name': 'trash_can_0',   'x': -4.694, 'y': 4.894,  'w': 0.35, 'd': 0.35, 'yaw': 0},
    # Cafe table bases (robot hits these at ground level)
    {'name': 'cafe_table_base',   'x': 6.359, 'y': -3.192, 'w': 0.56, 'd': 0.56, 'yaw': 0},
    {'name': 'cafe_table_0_base', 'x': 6.359, 'y': -2.278, 'w': 0.56, 'd': 0.56, 'yaw': 0},
    # Dining table legs
    {'name': 'table_leg1', 'x': -2.957, 'y': 2.724, 'w': 0.1, 'd': 0.1, 'yaw': 0},
    {'name': 'table_leg2', 'x': -2.357, 'y': 2.724, 'w': 0.1, 'd': 0.1, 'yaw': 0},
    {'name': 'table_leg3', 'x': -2.957, 'y': 2.124, 'w': 0.1, 'd': 0.1, 'yaw': 0},
    {'name': 'table_leg4', 'x': -2.357, 'y': 2.124, 'w': 0.1, 'd': 0.1, 'yaw': 0},
    # Table marble in upper right room (mesh-based, approximate size)
    {'name': 'table_marble', 'x': 4.883, 'y': 2.926, 'w': 1.2, 'd': 0.6, 'yaw': 0},
]

def rotate_point(x, y, yaw):
    return (math.cos(yaw)*x - math.sin(yaw)*y,
            math.sin(yaw)*x + math.cos(yaw)*y)

def parse_walls(sdf_file):
    tree = ET.parse(sdf_file)
    root = tree.getroot()
    walls = []

    for link in root.iter('link'):
        link_pose_elem = link.find('pose')
        if link_pose_elem is None:
            continue
        lp = [float(x) for x in link_pose_elem.text.split()]
        lx, ly, lyaw = lp[0], lp[1], lp[5]

        for collision in link.findall('.//collision'):
            box = collision.find('.//box/size')
            if box is None:
                continue
            size = [float(x) for x in box.text.split()]
            w, d, h = size[0], size[1], size[2]

            # Skip very low doorway thresholds
            if h < 0.6:
                continue

            col_pose_elem = collision.find('pose')
            if col_pose_elem is not None:
                cp = [float(x) for x in col_pose_elem.text.split()]
                cx_local, cy_local, cyaw_local = cp[0], cp[1], cp[5]
            else:
                cx_local, cy_local, cyaw_local = 0, 0, 0

            rx, ry = rotate_point(cx_local, cy_local, lyaw)
            wx = lx + rx
            wy = ly + ry
            wyaw = lyaw + cyaw_local

            walls.append({'x': wx, 'y': wy, 'w': w, 'd': d, 'yaw': wyaw})

    return walls

def draw_rotated_rect(img, cx, cy, w, d, yaw, origin_x, origin_y, resolution):
    draw = ImageDraw.Draw(img)
    corners_local = [(-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2)]
    corners_px = []
    for lx, ly in corners_local:
        rx, ry = rotate_point(lx, ly, yaw)
        wx = cx + rx
        wy = cy + ry
        px = int((wx - origin_x) / resolution)
        py = int((wy - origin_y) / resolution)
        corners_px.append((px, py))
    draw.polygon(corners_px, fill=0)

def main():
    sdf_file = os.path.expanduser(
        '~/navmind/ros2_ws/src/turtlebot3_simulations/'
        'turtlebot3_gazebo/models/turtlebot3_house/model.sdf')

    print("Parsing walls...")
    walls = parse_walls(sdf_file)
    print(f"Found {len(walls)} wall segments")

    # Find bounds from walls and furniture
    all_x = [w['x'] for w in walls] + [f['x'] for f in FURNITURE]
    all_y = [w['y'] for w in walls] + [f['y'] for f in FURNITURE]
    min_x = min(all_x) - PADDING
    max_x = max(all_x) + PADDING
    min_y = min(all_y) - PADDING
    max_y = max(all_y) + PADDING

    width  = int((max_x - min_x) / RESOLUTION)
    height = int((max_y - min_y) / RESOLUTION)
    print(f"Map: {width}x{height} px")
    print(f"Bounds: x=[{min_x:.1f},{max_x:.1f}] y=[{min_y:.1f},{max_y:.1f}]")

    # White = free space
    img = Image.new('L', (width, height), 254)

    # Draw walls
    print("Drawing walls...")
    for wall in walls:
        draw_rotated_rect(
            img,
            wall['x'], wall['y'],
            wall['w'], wall['d'],
            wall['yaw'],
            min_x, min_y,
            RESOLUTION
        )

    # Draw furniture
    print("Drawing furniture...")
    for item in FURNITURE:
        draw_rotated_rect(
            img,
            item['x'], item['y'],
            item['w'], item['d'],
            item['yaw'],
            min_x, min_y,
            RESOLUTION
        )
        print(f"  Drew {item['name']} at ({item['x']:.2f}, {item['y']:.2f})")

    # Flip vertically (ROS y-axis convention)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    os.makedirs(os.path.expanduser('~/navmind/maps'), exist_ok=True)

    # Save PGM
    pgm_path = os.path.expanduser('~/navmind/maps/house_map.pgm')
    img.save(pgm_path)

    # Save PNG for preview
    png_path = os.path.expanduser('~/navmind/maps/house_map.png')
    img.save(png_path)

    # Copy to Windows desktop
    img.save('/mnt/c/Users/Test/Desktop/house_map.png')

    # Save YAML
    yaml = f"""image: house_map.pgm
resolution: {RESOLUTION}
origin: [{min_x:.4f}, {min_y:.4f}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
"""
    with open(os.path.expanduser('~/navmind/maps/house_map.yaml'), 'w') as f:
        f.write(yaml)

    print("Done! Check house_map.png on your Desktop")

if __name__ == '__main__':
    main()
