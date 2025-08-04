#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Path planning module for leaf targeting
"""

import numpy as np
import math
import os
from core.geometry.path_calculator import calculate_circle_positions, find_closest_point_index
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def plan_safe_path(circle_position, target_point, leaf_position):
    """
    Plan a safe trajectory between a point on the circle and a leaf
    
    Args:
        circle_position: Position on the circle [x, y, z]
        target_point: Target position near the leaf [x, y, z] (already calculated with appropriate distance)
        leaf_position: Leaf position (centroid) [x, y, z]
    
    Returns:
        List of dictionaries describing the trajectory
    """
    # Convert positions to numpy arrays for easier calculations
    circle_pos = np.array(circle_position)
    leaf_pos = np.array(leaf_position)
    target_pos = np.array(target_point)
    
    # Calculate actual distance between leaf and target point
    real_distance = np.linalg.norm(target_pos - leaf_pos)
    print(f"DEBUG: Calculated distance between target point and leaf: {real_distance:.3f} m")
    
    # Create trajectory
    path = []
    
    # Starting point on circle
    path.append({
        "position": circle_pos.tolist(),
        "type": "via_point",
        "comment": "Position on circle"
    })
    
    # Intermediate point for leaf approach
    # (halfway between circle and leaf)
    middle_pos = circle_pos + 0.5 * (target_pos - circle_pos)
    path.append({
        "position": middle_pos.tolist(),
        "type": "via_point",
        "comment": "Approaching leaf"
    })
    
    # Target point near leaf (uses precalculated point directly)
    path.append({
        "position": target_pos.tolist(),
        "type": "target",
        "comment": f"Target point near leaf (distance: {real_distance:.3f} m)"
    })
    
    # Return path (same as approach but in reverse)
    path.append({
        "position": middle_pos.tolist(),
        "type": "via_point",
        "comment": "Returning to circle"
    })
    
    return path

def plan_complete_path(start_position, target_points, center_point, circle_radius, 
                      num_circle_points, leaf_distance=None):
    """
    Plan a complete trajectory including the circle and leaf approaches
    
    Args:
        start_position: Starting position [x, y, z]
        target_points: List of target points (leaves) [[x, y, z], ...]
        center_point: Circle center [x, y, z]
        circle_radius: Circle radius
        num_circle_points: Number of points on circle
        leaf_distance: Ignored parameter, kept for compatibility (distance already accounted for)
    
    Returns:
        List of dictionaries describing the complete trajectory
    """
    if leaf_distance is not None:
        print(f"Note: 'leaf_distance' parameter is ignored as distance is already accounted for in target points")
    
    if not target_points:
        return []
    
    # Calculate positions on circle
    circle_positions = calculate_circle_positions(center_point, circle_radius, num_circle_points)
    
    # Initialize path with starting position
    path = [{
        "position": start_position,
        "type": "via_point",
        "comment": "Starting position"
    }]
    
    # Find closest point on circle to starting position
    start_pos_index = find_closest_point_index(circle_positions, start_position)
    current_pos = circle_positions[start_pos_index]
    
    # Add entry point on circle
    path.append({
        "position": current_pos,
        "type": "via_point",
        "comment": "Entry point on circle"
    })
    
    # For each target point (leaf)
    for i, target_point in enumerate(target_points):
        # Find closest point on circle to leaf
        leaf_pos_index = find_closest_point_index(circle_positions, target_point)
        leaf_circle_pos = circle_positions[leaf_pos_index]
        
        # Add path on circle to closest point
        # Determine whether to go clockwise or counterclockwise (shortest)
        clockwise_distance = (leaf_pos_index - start_pos_index) % len(circle_positions)
        counterclockwise_distance = (start_pos_index - leaf_pos_index) % len(circle_positions)
        
        if clockwise_distance <= counterclockwise_distance:
            # Clockwise
            for j in range(1, clockwise_distance + 1):
                pos_index = (start_pos_index + j) % len(circle_positions)
                path.append({
                    "position": circle_positions[pos_index],
                    "type": "via_point",
                    "comment": f"Position {pos_index} on circle (toward leaf {i+1})"
                })
        else:
            # Counterclockwise
            for j in range(1, counterclockwise_distance + 1):
                pos_index = (start_pos_index - j) % len(circle_positions)
                path.append({
                    "position": circle_positions[pos_index],
                    "type": "via_point",
                    "comment": f"Position {pos_index} on circle (toward leaf {i+1})"
                })
        
        # Use target_point directly (already at correct distance)
        # For compatibility with plan_safe_path
        leaf_position = target_point
        
        # Plan approach path to leaf
        approach_path = plan_safe_path(leaf_circle_pos, target_point, leaf_position)
        
        # Add approach path (skip first point already on circle)
        path.extend(approach_path[1:])
        
        # Update starting point for next leaf
        start_pos_index = leaf_pos_index
    
    # ===== NEW PART: SAFE RETURN TO INITIAL POSITION =====
    # Find closest point on circle to starting position
    end_pos_index = find_closest_point_index(circle_positions, start_position)
    
    # Determine shortest path on circle to return to point near starting position
    clockwise_distance = (end_pos_index - start_pos_index) % len(circle_positions)
    counterclockwise_distance = (start_pos_index - end_pos_index) % len(circle_positions)
    
    print(f"Planning return via circle: current position {start_pos_index}, target point {end_pos_index}")
    
    if clockwise_distance <= counterclockwise_distance:
        # Clockwise
        print(f"Returning clockwise: {clockwise_distance} points")
        for j in range(1, clockwise_distance + 1):
            pos_index = (start_pos_index + j) % len(circle_positions)
            path.append({
                "position": circle_positions[pos_index],
                "type": "via_point",
                "comment": f"Position {pos_index} on circle (returning)"
            })
    else:
        # Counterclockwise
        print(f"Returning counterclockwise: {counterclockwise_distance} points")
        for j in range(1, counterclockwise_distance + 1):
            pos_index = (start_pos_index - j) % len(circle_positions)
            path.append({
                "position": circle_positions[pos_index],
                "type": "via_point",
                "comment": f"Position {pos_index} on circle (returning)"
            })
    
    # Finally add return to starting position
    path.append({
        "position": start_position,
        "type": "end",
        "comment": "Return to starting position"
    })
    
    return path

def visualize_path(path, points=None, target_point=None, save_path=None):
    """
    Visualize a 3D trajectory
    
    Args:
        path: List of dictionaries describing the trajectory
        points: Point cloud to display (optional)
        target_point: Target point to display (optional)
        save_path: Path to save image (optional)
    """
    # Create figure
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extract path positions
    positions = [p["position"] for p in path]
    x = [p[0] for p in positions]
    y = [p[1] for p in positions]
    z = [p[2] for p in positions]
    
    # Display path
    ax.plot(x, y, z, 'b-', linewidth=2, label="Path")
    
    # Display path points
    for i, point in enumerate(path):
        pos = point["position"]
        if point["type"] == "via_point":
            ax.scatter(pos[0], pos[1], pos[2], color='green', s=30)
        elif point["type"] == "target":
            ax.scatter(pos[0], pos[1], pos[2], color='red', s=50)
            ax.text(pos[0], pos[1], pos[2], f"Target {i}", color='red')
        elif point["type"] == "end":
            ax.scatter(pos[0], pos[1], pos[2], color='purple', s=50)
            ax.text(pos[0], pos[1], pos[2], "End", color='purple')
    
    # Display point cloud if provided
    if points is not None:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], color='gray', s=1, alpha=0.5)
    
    # Display target point if provided
    if target_point is not None:
        ax.scatter(target_point[0], target_point[1], target_point[2], color='orange', s=100)
    
    # Configure axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Path Visualization')
    
    # Adjust axis limits
    max_range = max([
        max(x) - min(x),
        max(y) - min(y),
        max(z) - min(z)
    ])
    mid_x = (max(x) + min(x)) / 2
    mid_y = (max(y) + min(y)) / 2
    mid_z = (max(z) + min(z)) / 2
    ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
    ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
    ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
    
    # Add legend
    ax.legend()
    
    # Display or save figure
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)

def visualize_complete_path(path, points, leaf_points_list=None, leaf_normals_list=None, save_dir=None):
    """
    Visualize a complete trajectory with leaves
    
    Args:
        path: List of dictionaries describing the trajectory
        points: Global point cloud
        leaf_points_list: List of leaf points (optional)
        leaf_normals_list: List of leaf normals (optional)
        save_dir: Directory to save images (optional)
    """
    # Create figure
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Extract path positions
    positions = [p["position"] for p in path]
    x = [p[0] for p in positions]
    y = [p[1] for p in positions]
    z = [p[2] for p in positions]
    
    # Display path
    ax.plot(x, y, z, 'b-', linewidth=2, label="Complete path")
    
    # Display path points
    for i, point in enumerate(path):
        pos = point["position"]
        if point["type"] == "via_point":
            ax.scatter(pos[0], pos[1], pos[2], color='green', s=20)
        elif point["type"] == "target":
            ax.scatter(pos[0], pos[1], pos[2], color='red', s=50)
            ax.text(pos[0], pos[1], pos[2], f"T{i}", color='red')
        elif point["type"] == "end":
            ax.scatter(pos[0], pos[1], pos[2], color='purple', s=50)
            ax.text(pos[0], pos[1], pos[2], "End", color='purple')
    
    # Display global point cloud (subsampled for performance)
    if len(points) > 5000:
        # Subsample for performance
        indices = np.random.choice(len(points), 5000, replace=False)
        sampled_points = points[indices]
        ax.scatter(sampled_points[:, 0], sampled_points[:, 1], sampled_points[:, 2], 
                  color='gray', s=1, alpha=0.3, label="Point cloud")
    else:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], 
                  color='gray', s=1, alpha=0.3, label="Point cloud")
    
    # Display leaf points if provided
    if leaf_points_list is not None:
        for i, leaf_points in enumerate(leaf_points_list):
            if isinstance(leaf_points, list) and len(leaf_points) == 3:
                # It's a single point (centroid)
                ax.scatter(leaf_points[0], leaf_points[1], leaf_points[2], 
                          color='orange', s=100, label=f"Leaf {i+1}" if i == 0 else "")
            else:
                # It's a set of points
                ax.scatter(leaf_points[:, 0], leaf_points[:, 1], leaf_points[:, 2], 
                          color='orange', s=10, alpha=0.7, label=f"Leaf {i+1}" if i == 0 else "")
    
    # Display leaf normals if provided
    if leaf_normals_list is not None and leaf_points_list is not None:
        for i, (leaf_points, leaf_normal) in enumerate(zip(leaf_points_list, leaf_normals_list)):
            if isinstance(leaf_points, list) and len(leaf_points) == 3:
                # It's a single point (centroid)
                centroid = leaf_points
            else:
                # Calculate centroid
                centroid = np.mean(leaf_points, axis=0)
            
            # Normalize normal
            normal = leaf_normal / np.linalg.norm(leaf_normal)
            
            # Draw normal
            ax.quiver(centroid[0], centroid[1], centroid[2], 
                     normal[0], normal[1], normal[2], 
                     color='red', length=0.05, arrow_length_ratio=0.3)
    
    # Configure axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Complete planned trajectory', fontsize=16)
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    # Remove duplicates
    unique = [(h, l) for i, (h, l) in enumerate(zip(handles, labels)) if l not in labels[:i]]
    ax.legend(*zip(*unique))
    
    # Adjust view
    ax.view_init(elev=30, azim=45)
    
    # Display or save figure
    if save_dir:
        save_path = os.path.join(save_dir, "complete_path.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {save_path}")
        
        # Also save top view
        ax.view_init(elev=90, azim=0)
        save_path = os.path.join(save_dir, "complete_path_top_view.png")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Top view saved: {save_path}")
    else:
        plt.show()
    
    plt.close(fig)