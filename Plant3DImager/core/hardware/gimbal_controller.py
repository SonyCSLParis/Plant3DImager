#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified gimbal controller for acquisition and targeting modules
"""

import time
import math
import serial
import numpy as np
from core.utils import config

class GimbalController:
    def __init__(self, arduino_port=None):
        """Initialize the gimbal controller"""
        self.arduino_port = arduino_port or config.ARDUINO_PORT
        self.gimbal_serial = None
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.initialized = False
    
    def connect(self):
        """Connect to the gimbal and initialize it"""
        if self.initialized:
            return self
        
        try:
            print(f"Connecting to Arduino on port {self.arduino_port}...")
            self.gimbal_serial = serial.Serial(self.arduino_port, 9600, timeout=1)
            time.sleep(2)  # Wait for initialization
            
            # Read and display initialization messages
            while self.gimbal_serial.in_waiting:
                response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                print(f"Arduino: {response}")
            
            self.initialized = True
            return self
        except Exception as e:
            print(f"Error initializing gimbal: {e}")
            raise
    
    def normalize_angle_difference(self, delta):
        """Normalize angle difference to take the shortest path"""
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        return delta
    
    def send_command(self, pan_angle, tilt_angle, wait_for_goal=False):
        """Send angles to the gimbal"""
        if not self.initialized or self.gimbal_serial is None:
            raise RuntimeError("Gimbal not initialized")
        
        try:
            # If both angles are negligible, don't move
            if abs(pan_angle) < 0.1 and abs(tilt_angle) < 0.1:
                print(f"Negligible delta (Pan={pan_angle:.2f}°, Tilt={tilt_angle:.2f}°) - no movement")
                return True
            
            print(f"Sending adjustments: Delta Pan={pan_angle:.2f}°, Delta Tilt={tilt_angle:.2f}°")
            
            # Send command
            command = f"{pan_angle} {tilt_angle}\n"
            self.gimbal_serial.write(command.encode())
            
            # Clear initial buffer
            time.sleep(0.2)
            while self.gimbal_serial.in_waiting:
                response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                print(f"Arduino: {response}")
            
            # Wait for confirmation if requested
            if wait_for_goal:
                print("Waiting for motors to reach position...")
                
                # Pause to let the gimbal process and start moving
                time.sleep(0.5)
                
                # Check if there are messages in the buffer
                goal_reached = False
                
                while self.gimbal_serial.in_waiting:
                    response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                    print(f"Arduino: {response}")
                    if "GOAL_REACHED" in response or "Movement completed" in response:
                        goal_reached = True
                
                if goal_reached:
                    print("Position reached immediately")
                else:
                    # Wait with timeout
                    start_time = time.time()
                    timeout = 5  # 5 seconds
                    
                    # Reduce timeout for small movements
                    if abs(pan_angle) < 5 and abs(tilt_angle) < 5:
                        timeout = 2
                    
                    while time.time() - start_time < timeout:
                        if self.gimbal_serial.in_waiting:
                            response = self.gimbal_serial.readline().decode('utf-8', errors='replace').strip()
                            print(f"Arduino: {response}")
                            
                            if "GOAL_REACHED" in response or "Movement completed" in response:
                                goal_reached = True
                                break
                        
                        time.sleep(0.1)
                    
                    # For very small movements, consider as successful despite timeout
                    if not goal_reached and abs(pan_angle) < 3 and abs(tilt_angle) < 3:
                        print("Very small movement, considered successful despite no confirmation")
                        goal_reached = True
            
            # Update current angles
            self.current_pan += pan_angle
            self.current_tilt += tilt_angle
            
            return True
            
        except Exception as e:
            print(f"Error sending command to gimbal: {e}")
            return False
    
    def calculate_angles(self, camera_position, target_position):
        """Calculate angles needed for camera to point at target"""
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
        pan_angle = -math.degrees(math.atan2(dx, dy))
        
        # Calculate horizontal distance between camera and target
        horizontal_distance = math.sqrt(dx**2 + dy**2)
        
        # Calculate tilt angle (vertical angle relative to horizontal plane)
        tilt_angle = math.degrees(math.atan2(dz, horizontal_distance))
        
        return (pan_angle, tilt_angle)
    
    def aim_at_target(self, camera_position, target_position, wait=True, invert_tilt=False):
        """
        Orient camera to aim at a target point
        
        Args:
            camera_position: Current camera position
            target_position: Target position
            wait: Wait for movement to complete
            invert_tilt: Invert the calculated tilt sign (to adapt to different coordinate systems)
        
        Returns:
            True if orientation is successful, False otherwise
        """
        if not self.initialized:
            raise RuntimeError("Gimbal not initialized")
        
        try:
            # Calculate necessary angles
            target_pan, target_tilt = self.calculate_angles(camera_position, target_position)
            
            # Invert tilt if requested
            if invert_tilt:
                target_tilt = -target_tilt
                print(f"DEBUG: Tilt inverted: {target_tilt:.2f}°")
            
            # Calculate angle adjustments (deltas)
            delta_pan = target_pan - self.current_pan
            delta_tilt = target_tilt - self.current_tilt
            
            # Normalize angle difference
            delta_pan = self.normalize_angle_difference(delta_pan)
            
            # Send command to gimbal
            return self.send_command(delta_pan, delta_tilt, wait_for_goal=wait)
            
        except Exception as e:
            print(f"Error orienting toward target: {e}")
            return False
    
    def reset_position(self):
        """Reset camera to initial position (0, 0)"""
        if not self.initialized:
            return True
        
        try:
            # Calculate increments needed to return to 0,0
            delta_pan = 0.0 - self.current_pan
            delta_pan = self.normalize_angle_difference(delta_pan)
            delta_tilt = 0.0 - self.current_tilt
            
            print(f"Resetting camera to initial position: "
                  f"Delta Pan={delta_pan:.2f}°, Delta Tilt={delta_tilt:.2f}°")
            
            # Send command
            success = self.send_command(delta_pan, delta_tilt, wait_for_goal=True)
            
            if success:
                self.current_pan = 0.0
                self.current_tilt = 0.0
            
            return success
        except Exception as e:
            print(f"Error resetting camera: {e}")
            return False
    
    def shutdown(self):
        """Properly shut down the gimbal"""
        if not self.initialized or self.gimbal_serial is None:
            return True
        
        try:
            # Reset camera to initial position
            self.reset_position()
            
            # Close serial connection
            print("Closing Arduino connection...")
            self.gimbal_serial.close()
            
            self.initialized = False
            return True
        except Exception as e:
            print(f"Error shutting down gimbal: {e}")
            return False