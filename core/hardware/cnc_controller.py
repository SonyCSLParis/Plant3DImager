#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified CNC controller for acquisition and targeting modules
"""

import time
import math
from romi.cnc import CNC

class CNCController:
    def __init__(self, speed=0.1):
        """
        Initialize the CNC controller with specified parameters
        """
        self.speed = speed
        self.cnc = None
        self.current_position = None
        self.initialized = False
    
    def connect(self):
        """Connect to the CNC and initialize it"""
        if self.initialized:
            return self
        
        try:
            print("Initializing CNC...")
            self.cnc = CNC("cnc", "cnc")
            
            # Start the CNC
            print("Starting CNC...")
            self.cnc.power_up()
            
            # Get initial position
            robot_pos = self.cnc.get_position()
            
            # Convert and store position
            self.current_position = {
                'x': robot_pos['x'],
                'y': robot_pos['y'],
                'z': -robot_pos['z']  # Invert for consistent display
            }
            
            print(f"Initial position: X={self.current_position['x']:.3f}, "
                  f"Y={self.current_position['y']:.3f}, Z={self.current_position['z']:.3f}")
            
            self.initialized = True
            return self
            
        except Exception as e:
            print(f"Error initializing CNC: {e}")
            raise
    
    def get_position(self):
        """Get the current position of the CNC"""
        if not self.initialized:
            raise RuntimeError("CNC not initialized")
        
        robot_pos = self.cnc.get_position()
        
        # Convert for consistent display
        position = {
            'x': robot_pos['x'],
            'y': robot_pos['y'],
            'z': -robot_pos['z']  # Invert for display
        }
        
        self.current_position = position
        return position
    
    def move_to(self, x, y, z, wait=True):
        """Move the CNC to the specified position"""
        if not self.initialized:
            raise RuntimeError("CNC not initialized")
        
        try:
            # IMPORTANT: Invert Z sign for robot control
            # (we use positive Z upward, robot uses positive Z downward)
            robot_z = -z
            
            print(f"Moving to X={x:.3f}, Y={y:.3f}, Z={z:.3f}... (Robot Z={robot_z:.3f})")
            
            # Perform the movement
            self.cnc.moveto(x, y, robot_z, self.speed, wait)
            
            # Update position if wait=True
            if wait:
                self.get_position()
                
                print(f"Position reached: X={self.current_position['x']:.3f}, "
                      f"Y={self.current_position['y']:.3f}, Z={self.current_position['z']:.3f}")
            
            return True
            
        except Exception as e:
            print(f"Error during movement: {e}")
            return False
    
    def travel(self, waypoints, wait=True):
        """Execute optimized trajectory through multiple waypoints"""
        if not self.initialized:
            raise RuntimeError("CNC not initialized")
        
        try:
            # Convert waypoints and invert Z coordinates
            robot_waypoints = []
            for waypoint in waypoints:
                x, y, z = waypoint
                robot_z = -z  # Invert Z for robot
                robot_waypoints.append([x, y, robot_z])
            
            print(f"Executing trajectory with {len(waypoints)} waypoints...")
            
            # Execute trajectory
            self.cnc.travel(robot_waypoints, speed=self.speed, sync=wait)
            
            # Update position if wait=True
            if wait:
                self.get_position()
                print(f"Trajectory completed. Final position: X={self.current_position['x']:.3f}, "
                      f"Y={self.current_position['y']:.3f}, Z={self.current_position['z']:.3f}")
            
            return True
            
        except Exception as e:
            print(f"Error during trajectory execution: {e}")
            return False
    
    def check_movement_status(self, previous_position, tolerance=0.001):
        """Check if the CNC is still moving by comparing positions"""
        if not self.initialized:
            raise RuntimeError("CNC not initialized")
        
        current_position = self.get_position()
        
        # Calculate distance between current and previous position
        dx = current_position['x'] - previous_position['x']
        dy = current_position['y'] - previous_position['y']
        dz = current_position['z'] - previous_position['z']
        
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # If the distance is less than tolerance, movement is considered finished
        return distance > tolerance, current_position
    
    def home(self):
        """Return to home position"""
        if not self.initialized:
            raise RuntimeError("CNC not initialized")
        
        try:
            print("Returning to home position (homing)...")
            self.cnc.homing()
            return True
        except Exception as e:
            print(f"Error during homing: {e}")
            return False
    
    def shutdown(self):
        """Properly shut down the CNC"""
        if not self.initialized:
            return True
        
        try:
            # First move to (0, 0, 0)
            print("Moving to position (0, 0, 0)...")
            self.move_to(0, 0, 0, wait=True)
            
            # Then return to home
            self.home()
            
            # Finally, power down
            print("Shutting down CNC...")
            self.cnc.power_down()
            
            self.initialized = False
            return True
        except Exception as e:
            print(f"Error shutting down CNC: {e}")
            return False
