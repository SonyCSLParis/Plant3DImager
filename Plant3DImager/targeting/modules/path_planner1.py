#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Path planning module with curved trajectories and cylindrical avoidance
"""

import numpy as np
import math
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Cylinder avoidance parameters
CYLINDER_CENTER = (0.375, 0.35)  # X,Y center
CYLINDER_RADIUS = 0.15  # 15cm safety radius
CYLINDER_Z_MIN = 0.0
CYLINDER_Z_MAX = 0.315
APPROACH_DISTANCE = 0.20  # 20cm from centroid

def point_in_cylinder(point, center_xy, radius, z_min, z_max):
    """Check if point is inside cylinder"""
    x, y, z = point
    cx, cy = center_xy
    
    # Check Z bounds
    if z < z_min or z > z_max:
        return False
    
    # Check radial distance
    radial_dist = math.sqrt((x - cx)**2 + (y - cy)**2)
    return radial_dist <= radius

def line_intersects_cylinder(start, end, center_xy, radius, z_min, z_max):
    """Check if line segment intersects cylinder"""
    # Sample points along line
    num_samples = 20
    for i in range(num_samples + 1):
        t = i / num_samples
        point = (
            start[0] + t * (end[0] - start[0]),
            start[1] + t * (end[1] - start[1]),
            start[2] + t * (end[2] - start[2])
        )
        if point_in_cylinder(point, center_xy, radius, z_min, z_max):
            return True
    return False

def calculate_avoidance_arc(start, end, center_xy, radius):
    """Calculate arc around cylinder"""
    sx, sy, sz = start
    ex, ey, ez = end
    cx, cy = center_xy
    
    # Calculate tangent points
    start_to_center = math.sqrt((sx - cx)**2 + (sy - cy)**2)
    end_to_center = math.sqrt((ex - cx)**2 + (ey - cy)**2)
    
    # Safety margin
    avoid_radius = radius + 0.05  # 5cm safety
    
    # Calculate tangent angles
    if start_to_center > avoid_radius:
        start_tangent_angle = math.asin(avoid_radius / start_to_center)
    else:
        start_tangent_angle = math.pi / 3  # 60 degrees fallback
    
    if end_to_center > avoid_radius:
        end_tangent_angle = math.asin(avoid_radius / end_to_center)
    else:
        end_tangent_angle = math.pi / 3
    
    # Vector from center to start/end
    start_angle = math.atan2(sy - cy, sx - cx)
    end_angle = math.atan2(ey - cy, ex - cx)
    
    # Choose direction (shorter arc)
    angle_diff = end_angle - start_angle
    if angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    elif angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    if angle_diff > 0:  # Counterclockwise
        tangent1_angle = start_angle + start_tangent_angle
        tangent2_angle = end_angle - end_tangent_angle
    else:  # Clockwise
        tangent1_angle = start_angle - start_tangent_angle
        tangent2_angle = end_angle + end_tangent_angle
    
    # Calculate tangent points
    tangent1 = (
        cx + avoid_radius * math.cos(tangent1_angle),
        cy + avoid_radius * math.sin(tangent1_angle),
        sz + 0.3 * (ez - sz)  # Interpolate Z
    )
    
    tangent2 = (
        cx + avoid_radius * math.cos(tangent2_angle),
        cy + avoid_radius * math.sin(tangent2_angle),
        sz + 0.7 * (ez - sz)  # Interpolate Z
    )
    
    return [tangent1, tangent2]

def plan_curved_trajectory(start, end, num_points=10):
    """Plan curved trajectory with cylinder avoidance"""
    path = []
    
    # Check if direct path intersects cylinder
    if line_intersects_cylinder(start, end, CYLINDER_CENTER, CYLINDER_RADIUS, CYLINDER_Z_MIN, CYLINDER_Z_MAX):
        # Calculate avoidance arc
        arc_points = calculate_avoidance_arc(start, end, CYLINDER_CENTER, CYLINDER_RADIUS)
        
        # Create smooth curve through avoidance points
        control_points = [start] + arc_points + [end]
    else:
        # Direct path with slight curve for smoothness
        mid_point = (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2,
            (start[2] + end[2]) / 2 + 0.02  # Slight Z lift
        )
        control_points = [start, mid_point, end]
    
    # Generate smooth curve
    for i in range(num_points):
        t = i / (num_points - 1)
        
        if len(control_points) == 3:
            # Quadratic Bezier
            p = (
                (1-t)**2 * control_points[0][0] + 2*(1-t)*t * control_points[1][0] + t**2 * control_points[2][0],
                (1-t)**2 * control_points[0][1] + 2*(1-t)*t * control_points[1][1] + t**2 * control_points[2][1],
                (1-t)**2 * control_points[0][2] + 2*(1-t)*t * control_points[1][2] + t**2 * control_points[2][2]
            )
        else:
            # Cubic Bezier
            p = (
                (1-t)**3 * control_points[0][0] + 3*(1-t)**2*t * control_points[1][0] + 3*(1-t)*t**2 * control_points[2][0] + t**3 * control_points[3][0],
                (1-t)**3 * control_points[0][1] + 3*(1-t)**2*t * control_points[1][1] + 3*(1-t)*t**2 * control_points[2][1] + t**3 * control_points[3][1],
                (1-t)**3 * control_points[0][2] + 3*(1-t)**2*t * control_points[1][2] + 3*(1-t)*t**2 * control_points[2][2] + t**3 * control_points[3][2]
            )
        
        path.append(p)
    
    return path

def calculate_approach_point(centroid, normal, distance=APPROACH_DISTANCE):
    """Calculate approach point at distance from centroid along normal"""
    centroid = np.array(centroid)
    normal = np.array(normal)
    normal_normalized = normal / np.linalg.norm(normal)
    approach_point = centroid + normal_normalized * distance
    return approach_point.tolist()

def plan_complete_path(start_position, target_leaves, center_point=None, circle_radius=None, num_circle_points=None):
    """
    Plan complete trajectory with curved paths and full measurement protocol
    
    Args:
        start_position: Starting position [x, y, z]
        target_leaves: List of leaf dictionaries with centroid, normal
        
    Returns:
        List of dictionaries describing the complete trajectory
    """
    if not target_leaves:
        return []
    
    path = []
    current_position = start_position
    
    # Starting point
    path.append({
        "position": start_position,
        "type": "start",
        "comment": "Starting position"
    })
    
    # For each leaf
    for i, leaf in enumerate(target_leaves):
        centroid = leaf['centroid']
        normal = leaf['normal']
        leaf_id = leaf.get('id', i+1)
        
        # Calculate approach point (20cm from centroid)
        approach_point = calculate_approach_point(centroid, normal, APPROACH_DISTANCE)
        
        # Plan curved trajectory to approach point
        curve_to_approach = plan_curved_trajectory(current_position, approach_point, num_points=8)
        
        # Add curved approach waypoints
        for j, waypoint in enumerate(curve_to_approach[:-1]):  # Exclude last point
            path.append({
                "position": waypoint,
                "type": "via_point",
                "comment": f"Curve to leaf {leaf_id}, waypoint {j+1}"
            })
        
        # Approach point (20cm from leaf)
        path.append({
            "position": approach_point,
            "type": "photo_point",
            "comment": f"Photo position for leaf {leaf_id} (20cm)",
            "leaf_data": leaf
        })
        
        # Close approach for fluorescence
        path.append({
            "position": centroid,
            "type": "fluoro_point", 
            "comment": f"Fluorescence position for leaf {leaf_id}",
            "leaf_data": leaf
        })
        
        # Return to approach point
        path.append({
            "position": approach_point,
            "type": "via_point",
            "comment": f"Return to approach point for leaf {leaf_id}"
        })
        
        current_position = approach_point
    
    # Return to start with curved trajectory
    curve_to_start = plan_curved_trajectory(current_position, start_position, num_points=6)
    
    for j, waypoint in enumerate(curve_to_start[:-1]):
        path.append({
            "position": waypoint,
            "type": "via_point", 
            "comment": f"Return curve, waypoint {j+1}"
        })
    
    # Final return
    path.append({
        "position": start_position,
        "type": "end",
        "comment": "Return to starting position"
    })
    
    return path

def visualize_complete_path(path, points, leaf_points_list=None, leaf_normals_list=None, save_dir=None):
    """Visualize complete trajectory with cylinder avoidance"""
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extract path positions
    positions = [p["position"] for p in path]
    x = [p[0] for p in positions]
    y = [p[1] for p in positions]
    z = [p[2] for p in positions]
    
    # Display path
    ax.plot(x, y, z, 'b-', linewidth=2, label="Curved trajectory")
    
    # Display cylinder
    theta = np.linspace(0, 2*np.pi, 50)
    cylinder_x = CYLINDER_CENTER[0] + CYLINDER_RADIUS * np.cos(theta)
    cylinder_y = CYLINDER_CENTER[1] + CYLINDER_RADIUS * np.sin(theta)
    
    for z_cyl in [CYLINDER_Z_MIN, CYLINDER_Z_MAX]:
        ax.plot(cylinder_x, cylinder_y, z_cyl, 'r-', alpha=0.5, linewidth=2)
    
    # Cylinder walls
    for i in range(0, len(theta), 5):
        ax.plot([cylinder_x[i], cylinder_x[i]], [cylinder_y[i], cylinder_y[i]], 
                [CYLINDER_Z_MIN, CYLINDER_Z_MAX], 'r-', alpha=0.3)
    
    # Path points
    target_count = 0
    for i, point in enumerate(path):
        pos = point["position"]
        if point["type"] == "photo_point":
            ax.scatter(pos[0], pos[1], pos[2], color='blue', s=100, marker='s')
            ax.text(pos[0], pos[1], pos[2], f"P{target_count+1}", color='blue')
        elif point["type"] == "fluoro_point":
            ax.scatter(pos[0], pos[1], pos[2], color='red', s=100, marker='*')
            ax.text(pos[0], pos[1], pos[2], f"F{target_count+1}", color='red')
            target_count += 1
        elif point["type"] == "via_point":
            ax.scatter(pos[0], pos[1], pos[2], color='green', s=20)
    
    # Point cloud
    if len(points) > 5000:
        indices = np.random.choice(len(points), 5000, replace=False)
        sampled_points = points[indices]
        ax.scatter(sampled_points[:, 0], sampled_points[:, 1], sampled_points[:, 2], 
                  color='gray', s=1, alpha=0.3, label="Point cloud")
    else:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], 
                  color='gray', s=1, alpha=0.3, label="Point cloud")
    
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Curved trajectory with cylinder avoidance')
    ax.legend()
    ax.view_init(elev=30, azim=45)
    
    if save_dir:
        save_path = os.path.join(save_dir, "curved_path.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)