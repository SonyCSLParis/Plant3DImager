#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Manual robot control module
Allows the user to send direct commands in "x y z pan tilt [photo]" format
"""

import time
import sys
import os
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.data.storage_manager import StorageManager
from core.utils import config

class ManualController:
    def __init__(self, args=None):
        """
        Initialize the manual controller
        
        Args:
            args: Command line arguments (optional)
        """
        # Default parameters
        self.arduino_port = config.ARDUINO_PORT
        self.cnc_speed = config.CNC_SPEED
        
        # Update parameters with command line arguments
        if args:
            self.update_from_args(args)
        
        # Hardware controllers
        self.cnc = None
        self.camera = None
        self.gimbal = None
        
        # State
        self.initialized = False
    
    def update_from_args(self, args):
        """Update parameters from command line arguments"""
        if hasattr(args, 'arduino_port') and args.arduino_port is not None:
            self.arduino_port = args.arduino_port
        
        if hasattr(args, 'speed') and args.speed is not None:
            self.cnc_speed = args.speed
    
    def initialize(self):
        """Initialize hardware components"""
        if self.initialized:
            return True
        
        try:
            print("\n=== Initializing manual controller ===")
            
            # Create directory for manual photos
            photos_dir = os.path.join(config.RESULTS_DIR, "manual_control")
            os.makedirs(photos_dir, exist_ok=True)
            
            # Initialize hardware controllers
            self.cnc = CNCController(self.cnc_speed)
            self.cnc.connect()
            
            self.camera = CameraController()
            self.camera.connect()
            self.camera.set_output_directory(photos_dir)
            
            self.gimbal = GimbalController(self.arduino_port)
            self.gimbal.connect()
            
            # Display parameters
            print(f"\nControl parameters:")
            print(f"- Arduino port: {self.arduino_port}")
            print(f"- CNC speed: {self.cnc_speed} m/s")
            print(f"- Photos folder: {photos_dir}")
            print(f"- Stabilization time: {config.STABILIZATION_TIME} seconds")
            
            # Get and display initial position
            position = self.cnc.get_position()
            print(f"\nInitial position: X={position['x']:.3f}, Y={position['y']:.3f}, Z={position['z']:.3f}")
            print(f"Initial angles: Pan={self.gimbal.current_pan:.3f}°, Tilt={self.gimbal.current_tilt:.3f}°")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Initialization error: {e}")
            self.shutdown()
            return False
    
    def parse_command(self, command):
        """
        Parse a user command
        
        Args:
            command: Command string in "x y z [pan] [tilt] [photo]" format or "q" to quit
            
        Returns:
            Tuple (action, params) where action is "move", "exit" or "help",
            and params is a parameters dictionary or None
        """
        command = command.strip().lower()
        
        # Exit command
        if command in ('q', 'quit', 'exit'):
            return ("exit", None)
        
        # Help command
        if command in ('h', 'help', '?'):
            return ("help", None)
            
        # Move command
        parts = command.split()
        
        # Expected format: x y z [pan] [tilt] [photo]
        if len(parts) >= 3:
            try:
                params = {
                    'x': float(parts[0]),
                    'y': float(parts[1]),
                    'z': float(parts[2]),
                    'take_photo': False  # Default, no photo
                }
                
                # Optional angles
                if len(parts) >= 4:
                    params['pan'] = float(parts[3])
                
                if len(parts) >= 5:
                    params['tilt'] = float(parts[4])
                
                # Photo option (1=yes, 0=no)
                if len(parts) >= 6:
                    params['take_photo'] = parts[5] == '1'
                
                return ("move", params)
            except ValueError:
                print("Error: Invalid format. Use numbers for x, y, z, pan, tilt.")
                return ("invalid", None)
        
        # Invalid command
        print("Command not recognized. Type 'help' for assistance.")
        return ("invalid", None)
    
    def show_help(self):
        """Display help on available commands"""
        print("\n=== MANUAL CONTROL HELP ===")
        print("Available commands:")
        print("  x y z [pan] [tilt] [photo]  - Move robot to position (x,y,z) and orient camera")
        print("                                 Photo: 1 to take a photo, 0 or omitted for no photo")
        print("                                 Example: '0.3 0.4 0.1 45 20 1'")
        print("  h, help, ?                  - Display this help")
        print("  q, quit, exit               - Quit program")
        print("\nNote: All positions are in meters, angles in degrees.")
        print("      Parameters pan, tilt and photo are optional.")
        print(f"      A stabilization delay of {config.STABILIZATION_TIME} seconds is applied before each photo.")
    
    def take_photo(self):
        """Take a photo at current position"""
        if not self.initialized:
            print("Error: Controller not initialized.")
            return None
        
        try:
            # Pause for stabilization before taking photo
            print(f"Stabilizing for {config.STABILIZATION_TIME} seconds...")
            time.sleep(config.STABILIZATION_TIME)
            
            # Get current position
            position = self.cnc.get_position()
            
            # Create dictionary with camera pose information
            camera_pose = {
                'x': position['x'],
                'y': position['y'],
                'z': position['z'],
                'pan_angle': self.gimbal.current_pan,
                'tilt_angle': self.gimbal.current_tilt
            }
            
            # Generate filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"manual_{timestamp}.jpg"
            
            # Take photo
            print("Taking photo...")
            photo_path, _ = self.camera.take_photo(filename, camera_pose)
            
            if photo_path:
                print(f"Photo taken and saved: {photo_path}")
                return photo_path
            else:
                print("Error: Unable to take photo.")
                return None
                
        except Exception as e:
            print(f"Error taking photo: {e}")
            return None
    
    def run_manual_control(self):
        """Execute manual control mode"""
        if not self.initialize():
            return False
        
        try:
            print("\n=== MANUAL CONTROL MODE ===")
            print("Enter commands in 'x y z [pan] [tilt] [photo]' format or 'q' to quit.")
            print("Photo: 1 to take a photo, 0 or omitted for no photo")
            print("Type 'help' for assistance.")
            
            while True:
                # Get command from user
                command = input("\nCommand > ")
                
                # Parse command
                action, params = self.parse_command(command)
                
                # Execute action
                if action == "exit":
                    print("Exiting manual control mode...")
                    break
                
                elif action == "help":
                    self.show_help()
                
                elif action == "move":
                    try:
                        # Robot movement
                        x, y, z = params['x'], params['y'], params['z']
                        print(f"Moving to X={x:.3f}, Y={y:.3f}, Z={z:.3f}...")
                        
                        self.cnc.move_to(x, y, z, wait=True)
                        
                        # Camera orientation if angles are specified
                        if 'pan' in params or 'tilt' in params:
                            current_pos = self.cnc.get_position()
                            
                            # Get current angles
                            current_pan, current_tilt = self.gimbal.current_pan, self.gimbal.current_tilt
                            
                            # Calculate deltas
                            delta_pan = params.get('pan', current_pan) - current_pan
                            delta_tilt = params.get('tilt', current_tilt) - current_tilt
                            
                            print(f"Orienting camera: Pan={params.get('pan', current_pan):.3f}°, Tilt={params.get('tilt', current_tilt):.3f}°...")
                            
                            # Send command to gimbal
                            self.gimbal.send_command(delta_pan, delta_tilt, wait_for_goal=True)
                        
                        # Display final position
                        position = self.cnc.get_position()
                        print(f"Position reached: X={position['x']:.3f}, Y={position['y']:.3f}, Z={position['z']:.3f}")
                        print(f"Angles: Pan={self.gimbal.current_pan:.3f}°, Tilt={self.gimbal.current_tilt:.3f}°")
                        
                        # Take photo if requested
                        if params.get('take_photo', False):
                            self.take_photo()
                        
                    except Exception as e:
                        print(f"Error during movement: {e}")
            
            return True
            
        except KeyboardInterrupt:
            print("\nManual control interrupted by user")
            return False
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Properly shut down the system"""
        print("\nShutting down manual control system...")
        
        # Reset camera to initial position
        if self.gimbal is not None:
            try:
                print("Resetting camera to initial position (0,0)...")
                self.gimbal.reset_position()
            except Exception as e:
                print(f"Error resetting camera: {e}")
        
        # Stop controllers in reverse order of initialization
        if hasattr(self, 'gimbal') and self.gimbal:
            self.gimbal.shutdown()
        
        if hasattr(self, 'camera') and self.camera:
            self.camera.shutdown()
        
        if hasattr(self, 'cnc') and self.cnc:
            self.cnc.shutdown()  # Ce shutdown() fait déjà le homing
        
        self.initialized = False
        print("Manual control system shut down.")