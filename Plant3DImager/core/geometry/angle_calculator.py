#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Angle calculation functions for camera and gimbal
"""

import math
import numpy as np

def normalize_angle_difference(delta):
    """
    Normalize angle difference to take the shortest path
    
    Args:
        delta: Angle difference in degrees
        
    Returns:
        Normalized difference between -180 and +180 degrees
    """
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return delta

def calculate_camera_angles(camera_position, target_position):
    """
    Calculate pan and tilt angles needed for camera 
    to point at target from its current position
    
    Args:
        camera_position: Camera position (x, y, z) or {"x": x, "y": y, "z": z}
        target_position: Target position (x, y, z) or {"x": x, "y": y, "z": z}
        
    Returns:
        Tuple (pan_angle, tilt_angle) in degrees
    """
    # Convert camera position to x, y, z coordinates
    if isinstance(camera_position, dict):
        cam_x, cam_y, cam_z = camera_position['x'], camera_position['y'], camera_position['z']
    else:
        cam_x, cam_y, cam_z = camera_position
    
    # Convert target position to x, y, z coordinates
    if isinstance(target_position, dict):
        target_x, target_y, target_z = target_position['x'], target_position['y'], target_position['z']
    else:
        target_x, target_y, target_z = target_position
    
    # Vector from camera to target
    dx = target_x - cam_x
    dy = target_y - cam_y
    dz = target_z - cam_z
    
    # Calculate pan angle (horizontal angle relative to Y axis)
    # Note: We invert the sign so that rotation is in the right direction
    # Negative angle rotates right, positive angle rotates left
    pan_angle = -math.degrees(math.atan2(dx, dy))
    
    # Calculate horizontal distance between camera and target
    horizontal_distance = math.sqrt(dx**2 + dy**2)
    
    # Calculate tilt angle (vertical angle relative to horizontal plane)
    tilt_angle = math.degrees(math.atan2(dz, horizontal_distance))
    
    return (pan_angle, tilt_angle)