#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Path planning with cubic splines and avoidance waypoints
"""

import numpy as np
import math
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import CubicSpline
from core.utils import config

# Cylinder avoidance parameters
CYLINDER_CENTER = (config.CENTER_POINT[0], config.CENTER_POINT[1])
CYLINDER_RADIUS = 0.15  # 15cm safety radius
CYLINDER_Z_MIN = -0.315
CYLINDER_Z_MAX = 0.0
APPROACH_DISTANCE = 0.09  # 15cm from centroid
AVOIDANCE_RADIUS = 0.25  # 25cm - circle for waypoints placement

def is_within_robot_limits(position):
    """Check if position is within robot limits"""
    x, y, z = position
    return (0 <= x <= 0.76 and 
            0 <= y <= 0.72 and 
            -0.315 <= z <= 0)

def point_in_cylinder(point, center_xy, radius, z_min, z_max):
    """Check if point is inside cylinder"""
    x, y, z = point
    cx, cy = center_xy
    
    if z < z_min or z > z_max:
        return False
    
    radial_dist = math.sqrt((x - cx)**2 + (y - cy)**2)
    return radial_dist <= radius

def line_intersects_cylinder(start, end, center_xy, radius, z_min, z_max):
    """Check if direct line intersects cylinder"""
    for i in range(50):
        t = i / 49
        point = (
            start[0] + t * (end[0] - start[0]),
            start[1] + t * (end[1] - start[1]),
            start[2] + t * (end[2] - start[2])
        )
        if point_in_cylinder(point, center_xy, radius, z_min, z_max):
            return True
    return False

def generate_avoidance_waypoints(start, end, center_xy, avoidance_radius, num_waypoints=2):
    """Generate waypoints on external circle for spline path"""
    sx, sy, sz = start
    ex, ey, ez = end
    cx, cy = center_xy
    
    # Calculate angles to start and end points
    start_angle = math.atan2(sy - cy, sx - cx)
    end_angle = math.atan2(ey - cy, ex - cx)
    
    # Choose shorter arc direction
    angle_diff = end_angle - start_angle
    if angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    elif angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    # Generate waypoints along arc
    waypoints = []
    for i in range(1, num_waypoints + 1):
        t = i / (num_waypoints + 1)
        
        # Interpolate angle
        current_angle = start_angle + t * angle_diff
        
        # Position on avoidance circle
        wx = cx + avoidance_radius * math.cos(current_angle)
        wy = cy + avoidance_radius * math.sin(current_angle)
        wz = sz + t * (ez - sz)  # Linear Z interpolation
        
        waypoints.append((wx, wy, wz))
    
    return waypoints

def create_spline_trajectory(start, end, waypoints=None, num_points=12):
    """Create smooth spline trajectory through waypoints"""
    
    # Build control points
    if waypoints:
        control_points = [start] + waypoints + [end]
    else:
        # Direct path with intermediate point for smoothness
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        mid_z = (start[2] + end[2]) / 2 + 0.03  # Slight Z lift
        control_points = [start, (mid_x, mid_y, mid_z), end]
    
    # Convert to arrays
    control_array = np.array(control_points)
    
    # Parameter values (cumulative distance approximation)
    t_values = [0]
    for i in range(1, len(control_points)):
        dist = np.linalg.norm(np.array(control_points[i]) - np.array(control_points[i-1]))
        t_values.append(t_values[-1] + dist)
    
    t_values = np.array(t_values)
    
    # Create cubic splines for each dimension
    spline_x = CubicSpline(t_values, control_array[:, 0], bc_type='natural')
    spline_y = CubicSpline(t_values, control_array[:, 1], bc_type='natural')
    spline_z = CubicSpline(t_values, control_array[:, 2], bc_type='natural')
    
    # Sample points along spline
    t_sample = np.linspace(t_values[0], t_values[-1], num_points)
    
    trajectory = []
    for t in t_sample:
        point = (float(spline_x(t)), float(spline_y(t)), float(spline_z(t)))
        
        # Clamp waypoint to robot limits
        point = (
            max(0, min(point[0], 0.76)),   # X limits
            max(0, min(point[1], 0.72)),   # Y limits  
            max(-0.315, min(point[2], 0))  # Z limits
        )
        trajectory.append(point)
    
    return trajectory

def plan_spline_trajectory(start, end, num_points=12):
    """Plan trajectory using splines with cylinder avoidance"""
    
    print(f"Planning spline: {start} -> {end}")
    
    # Check if direct path intersects cylinder
    intersects = line_intersects_cylinder(start, end, CYLINDER_CENTER, CYLINDER_RADIUS, CYLINDER_Z_MIN, CYLINDER_Z_MAX)
    
    if intersects:
        print("Using avoidance waypoints")
        # Generate avoidance waypoints
        waypoints = generate_avoidance_waypoints(start, end, CYLINDER_CENTER, AVOIDANCE_RADIUS)
        trajectory = create_spline_trajectory(start, end, waypoints, num_points)
    else:
        print("Direct spline path")
        # Direct smooth path
        trajectory = create_spline_trajectory(start, end, None, num_points)
    
    return trajectory

def calculate_approach_point(centroid, normal, distance=APPROACH_DISTANCE):
    """Calculate approach point at distance from centroid along normal"""
    centroid = np.array(centroid)
    normal = np.array(normal)
    normal_normalized = normal / np.linalg.norm(normal)
    approach_point = centroid + normal_normalized * distance
    return approach_point.tolist()

def calculate_fluoro_point_with_offset(centroid, normal, distance=0.03, offset_mm=25):
    """
    Calculate fluorescence point with geometric offset compensation
    
    Args:
        centroid: Leaf centroid coordinates
        normal: Leaf normal vector
        distance: Base distance from leaf (default 5cm)
        offset_mm: Sensor offset in mm (default 25mm)
    
    Returns:
        Corrected fluorescence point coordinates
    """
    # Point base à la distance spécifiée le long de la normale
    centroid = np.array(centroid)
    normal_vec = np.array(normal)
    normal_normalized = normal_vec / np.linalg.norm(normal_vec)
    base_point = centroid + normal_normalized * distance
    
    # Direction verticale
    vertical_direction = np.array([0, 0, 1])
    
    # Vecteur dans le plan perpendiculaire à la normale
    # Projection de la verticale sur le plan perpendiculaire à la normale
    vertical_proj = vertical_direction - np.dot(vertical_direction, normal_normalized) * normal_normalized
    
    # Vérifier si la projection n'est pas nulle (normale pas verticale)
    if np.linalg.norm(vertical_proj) < 1e-6:
        # Si normale est verticale, utiliser direction X
        horizontal_direction = np.array([1, 0, 0])
        vertical_proj = horizontal_direction - np.dot(horizontal_direction, normal_normalized) * normal_normalized
    
    # Normaliser la direction perpendiculaire dans le plan
    if np.linalg.norm(vertical_proj) > 1e-6:
        vertical_proj_normalized = vertical_proj / np.linalg.norm(vertical_proj)
        
        # Décalage -offset_mm dans cette direction (compensation capteur vers le haut)
        offset_m = offset_mm / 1000.0  # Conversion mm vers m
        offset = -vertical_proj_normalized * offset_m
        
        return (base_point + offset).tolist()
    else:
        # Cas limite : retourner point base sans décalage
        print("Warning: Could not calculate geometric offset, using base point")
        return base_point.tolist()

def plan_complete_path(start_position, target_leaves, center_point=None, circle_radius=None, num_circle_points=None):
    """Plan complete trajectory using spline paths"""
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
        
        # Calculate approach point (photo position at 20cm)
        approach_point = calculate_approach_point(centroid, normal, APPROACH_DISTANCE)
        
        # Calculate fluorescence point (3.75cm from centroid with 25mm geometric offset)
        fluoro_point = calculate_fluoro_point_with_offset(centroid, normal, 0.03, 25)
        
        # Check if essential points are within limits
        if not is_within_robot_limits(approach_point):
            print(f"ERROR: Photo point for leaf {leaf_id} outside robot limits - SKIPPING LEAF")
            print(f"  Position: {approach_point}")
            continue
        
        if not is_within_robot_limits(fluoro_point):
            print(f"ERROR: Fluoro point for leaf {leaf_id} outside robot limits - SKIPPING LEAF") 
            print(f"  Position: {fluoro_point}")
            continue
        
        # Plan spline trajectory to approach point
        spline_to_approach = plan_spline_trajectory(current_position, approach_point, num_points=10)
        
        # Add spline waypoints
        for j, waypoint in enumerate(spline_to_approach[:-1]):
            path.append({
                "position": waypoint,
                "type": "via_point",
                "comment": f"Spline to leaf {leaf_id}, point {j+1}"
            })
        
        # Approach point (photo position at 20cm)
        path.append({
            "position": approach_point,
            "type": "photo_point",
            "comment": f"Photo position for leaf {leaf_id} (20cm)",
            "leaf_data": leaf
        })
        
        # Fluorescence position (5cm from centroid)
        path.append({
            "position": fluoro_point,
            "type": "fluoro_point",
            "comment": f"Fluorescence position for leaf {leaf_id} (5cm)",
            "leaf_data": leaf
        })
        
        # Return to photo point (20cm) before final rotation
        path.append({
            "position": approach_point,
            "type": "return_photo_point",
            "comment": f"Return to photo position for leaf {leaf_id} (20cm)",
            "leaf_data": leaf
        })
        
        current_position = approach_point
    
    # Return to start using spline
    spline_to_start = plan_spline_trajectory(current_position, start_position, num_points=8)
    
    for j, waypoint in enumerate(spline_to_start[:-1]):
        path.append({
            "position": waypoint,
            "type": "via_point",
            "comment": f"Return spline, point {j+1}"
        })
    
    # Final position
    path.append({
        "position": start_position,
        "type": "end",
        "comment": "Return to starting position"
    })
    
    return path

def visualize_complete_path(path, points, leaf_points_list=None, leaf_normals_list=None, save_dir=None):
    """Visualize spline trajectory with cylinder"""
    
    positions = [p["position"] for p in path]
    
    # Dual plot
    fig = plt.figure(figsize=(16, 8))
    
    # 3D view
    ax1 = fig.add_subplot(121, projection='3d')
    
    # Cylinder 3D
    theta = np.linspace(0, 2*np.pi, 50)
    for i in range(0, 50, 3):
        cx = CYLINDER_CENTER[0] + CYLINDER_RADIUS * np.cos(theta[i])
        cy = CYLINDER_CENTER[1] + CYLINDER_RADIUS * np.sin(theta[i])
        ax1.plot([cx, cx], [cy, cy], [CYLINDER_Z_MIN, CYLINDER_Z_MAX], 'r-', linewidth=2, alpha=0.7)
    
    cylinder_x = CYLINDER_CENTER[0] + CYLINDER_RADIUS * np.cos(theta)
    cylinder_y = CYLINDER_CENTER[1] + CYLINDER_RADIUS * np.sin(theta)
    ax1.plot(cylinder_x, cylinder_y, CYLINDER_Z_MIN, 'r-', linewidth=3, label='Cylinder (15cm)')
    ax1.plot(cylinder_x, cylinder_y, CYLINDER_Z_MAX, 'r-', linewidth=3)
    
    # Avoidance circle (25cm)
    avoid_x = CYLINDER_CENTER[0] + AVOIDANCE_RADIUS * np.cos(theta)
    avoid_y = CYLINDER_CENTER[1] + AVOIDANCE_RADIUS * np.sin(theta)
    ax1.plot(avoid_x, avoid_y, 0, 'g--', linewidth=2, alpha=0.5, label='Avoidance circle (25cm)')
    
    # Trajectory
    ax1.plot([p[0] for p in positions], [p[1] for p in positions], [p[2] for p in positions], 
            'b-', linewidth=3, label="Spline trajectory")
    
    # Point cloud
    if len(points) > 2000:
        sample_indices = np.random.choice(len(points), 2000, replace=False)
        display_points = points[sample_indices]
        ax1.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
                  c='gray', s=0.5, alpha=0.2)
    
    # Path points
    for position, point_info in zip(positions, path):
        if point_info["type"] == "photo_point":
            ax1.scatter(position[0], position[1], position[2], color='blue', s=100, marker='s')
        elif point_info["type"] == "fluoro_point":
            ax1.scatter(position[0], position[1], position[2], color='red', s=100, marker='*')
    
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')
    ax1.set_title('3D Spline Trajectory')
    ax1.legend()
    ax1.view_init(elev=25, azim=45)
    
    # Top view
    ax2 = fig.add_subplot(122)
    
    # Cylinders top view
    circle_inner = plt.Circle(CYLINDER_CENTER, CYLINDER_RADIUS, color='red', fill=False, linewidth=3, label='Cylinder (15cm)')
    circle_outer = plt.Circle(CYLINDER_CENTER, AVOIDANCE_RADIUS, color='green', fill=False, linewidth=2, linestyle='--', label='Waypoint circle (25cm)')
    ax2.add_patch(circle_inner)
    ax2.add_patch(circle_outer)
    
    # Trajectory
    ax2.plot([p[0] for p in positions], [p[1] for p in positions], 'b-', linewidth=3, label="Spline path")
    
    # Point cloud
    if len(points) > 3000:
        sample_indices = np.random.choice(len(points), 3000, replace=False)
        display_points = points[sample_indices]
        ax2.scatter(display_points[:, 0], display_points[:, 1], c='gray', s=0.3, alpha=0.1)
    
    # Path points
    for position, point_info in zip(positions, path):
        if point_info["type"] == "photo_point":
            ax2.scatter(position[0], position[1], color='blue', s=100, marker='s')
        elif point_info["type"] == "fluoro_point":
            ax2.scatter(position[0], position[1], color='red', s=100, marker='*')
        elif point_info["type"] == "start":
            ax2.scatter(position[0], position[1], color='purple', s=120, marker='D')
    
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_title('Top View - Spline Strategy')
    ax2.grid(True, alpha=0.3)
    ax2.axis('equal')
    ax2.legend()
    
    # Algorithm explanation
    explanation = """SPLINE ALGORITHM:
1. Check direct line intersection
2. Generate waypoints on 25cm circle
3. Cubic spline through waypoints
4. Natural boundary conditions"""
    
    ax2.text(0.02, 0.98, explanation, transform=ax2.transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
    
    plt.tight_layout()
    
    if save_dir:
        save_path = os.path.join(save_dir, 'spline_trajectory.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Spline visualization saved: {save_path}")
    
    plt.show()