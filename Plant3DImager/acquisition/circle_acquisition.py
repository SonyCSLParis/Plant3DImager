#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Circular image acquisition module integrated into the modular architecture
"""

import time
import os
import argparse
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.geometry.path_calculator import plan_multi_circle_path
from core.data.storage_manager import StorageManager
from acquisition.metadata_generator import MetadataGenerator
from core.utils import config

class CircleAcquisition:
    def __init__(self, args=None):
        """
        Initialize the circular acquisition module
        
        Args:
            args: Command line arguments (optional)
        """
        # Default parameters
        self.num_circles = 1
        self.num_positions = config.NUM_POSITIONS
        self.circle_radius = config.CIRCLE_RADIUS
        self.z_offset = config.Z_OFFSET
        self.arduino_port = config.ARDUINO_PORT
        self.cnc_speed = config.CNC_SPEED
        self.update_interval = config.UPDATE_INTERVAL
        self.target_point = config.TARGET_POINT
        
        # Update parameters with command line arguments
        if args:
            self.update_from_args(args)
        
        # Hardware controllers
        self.cnc = None
        self.camera = None
        self.gimbal = None
        
        # Storage manager
        self.storage = None
        self.metadata_generator = None
        
        # Session data
        self.photos_taken = []
        self.metadata_files = []
        self.session_dirs = None
        
        # State
        self.initialized = False
    
    def update_from_args(self, args):
        """Update parameters from command line arguments"""
        if hasattr(args, 'circles') and args.circles is not None:
            self.num_circles = args.circles
        
        if hasattr(args, 'positions') and args.positions is not None:
            self.num_positions = args.positions
        
        if hasattr(args, 'radius') and args.radius is not None:
            self.circle_radius = args.radius
        
        if hasattr(args, 'z_offset') and args.z_offset is not None:
            self.z_offset = args.z_offset
        
        if hasattr(args, 'arduino_port') and args.arduino_port is not None:
            self.arduino_port = args.arduino_port
        
        if hasattr(args, 'speed') and args.speed is not None:
            self.cnc_speed = args.speed
    
    def initialize(self):
        """Initialize hardware components and directories"""
        if self.initialized:
            return True
        
        try:
            print("\n=== Initializing circular acquisition system ===")
            
            # Create storage manager
            self.storage = StorageManager(mode="acquisition")
            self.session_dirs = self.storage.create_directory_structure()
            
            # Display directories for debugging
            print("\nCreated directories:")
            for key, path in self.session_dirs.items():
                print(f"- {key}: {path}")
            
            # Create metadata generator
            self.metadata_generator = MetadataGenerator(self.storage)
            
            # Initialize hardware controllers
            self.cnc = CNCController(self.cnc_speed)
            self.cnc.connect()
            
            self.camera = CameraController()
            self.camera.connect()
            self.camera.set_output_directory(self.session_dirs["images"])
            
            self.gimbal = GimbalController(self.arduino_port)
            self.gimbal.connect()
            
            # Display parameters
            print(f"\nAcquisition parameters:")
            print(f"- Target point: {self.target_point}")
            print(f"- Circle center: {config.CENTER_POINT}")
            print(f"- Radius: {self.circle_radius} m")
            print(f"- Number of circles: {self.num_circles}")
            print(f"- Positions per circle: {self.num_positions}")
            print(f"- Total number of photos: {self.num_positions * self.num_circles}")
            if self.num_circles > 1:
                print(f"- Z offset: {self.z_offset} m")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Initialization error: {e}")
            self.shutdown()
            return False
    
    def run_acquisition(self):
        """Execute the complete acquisition process"""
        if not self.initialize():
            return False
        
        try:
            # Initial position for path calculation
            current_pos = self.cnc.get_position()
            start_point = (current_pos['x'], current_pos['y'], current_pos['z'])
            
            # Plan path on circle(s)
            path = plan_multi_circle_path(
                center=config.CENTER_POINT,
                radius=self.circle_radius,
                num_positions=self.num_positions,
                num_circles=self.num_circles,
                z_offset=self.z_offset,
                start_point=start_point
            )
            
            print(f"\nPlanned path: {len(path)} points")
            
            # Ask for confirmation
            input("\nPress Enter to start image acquisition...")
            
            # Initial camera orientation toward target point
            print("\nInitial camera orientation toward target point...")
            self.gimbal.aim_at_target(current_pos, self.target_point)
            
            # Variables to track camera position
            photo_index = 0
            
            # Follow the path
            for i, point_info in enumerate(path):
                position = point_info["position"]
                point_type = point_info["type"]
                comment = point_info.get("comment", "")
                
                print(f"\n--- Point {i+1}/{len(path)}: {point_type} ---")
                if comment:
                    print(f"Info: {comment}")
                
                # Move to position
                success = self.cnc.move_to(
                    position[0], position[1], position[2], wait=True
                )
                
                if not success:
                    print(f"Error during movement to point {i+1}")
                    continue
                
                # If this is a via point on the circle (where we take a photo)
                if point_type == "via_point" and "Position" in comment:
                    # Get final position
                    final_pos = self.cnc.get_position()
                    
                    # Final camera orientation
                    print("Final camera adjustment...")
                    self.gimbal.aim_at_target(final_pos, self.target_point, wait=True)
                    
                    # Pause for stabilization
                    print(f"Stabilizing for {config.STABILIZATION_TIME} seconds...")
                    time.sleep(config.STABILIZATION_TIME)
                    
                    # Create dictionary with camera pose information
                    camera_pose = {
                        'x': final_pos['x'],
                        'y': final_pos['y'],
                        'z': final_pos['z'],
                        'pan_angle': self.gimbal.current_pan,
                        'tilt_angle': self.gimbal.current_tilt
                    }
                    
                    # Take a photo
                    print(f"Taking photo {photo_index+1}...")
                    image_id = f"{photo_index:05d}_rgb"
                    filename = f"{image_id}.jpg"
                    
                    photo_path, _ = self.camera.take_photo(filename, camera_pose)
                    
                    if photo_path:
                        # Generate metadata
                        json_path = self.metadata_generator.create_image_metadata(
                            image_id, camera_pose, self.session_dirs["metadata_images"]
                        )
                        
                        # Add to lists
                        self.photos_taken.append(photo_path)
                        self.metadata_files.append(json_path)
                        
                        print(f"Photo {photo_index+1} taken successfully")
                        photo_index += 1
                    else:
                        print(f"Failed to take photo at position {i+1}")
            
            # Generate final metadata files
            print("\nGenerating metadata files...")
            
            # Check that directories exist
            if not self.session_dirs:
                print("ERROR: Session directories were not created")
                return False
            
            # Generate workspace.json
            workspace = {
                "x": [225, 525],
                "y": [220, 520],
                "z": [200, 500]
            }
            self.metadata_generator.create_images_json(workspace)
            
            # Extract filenames (without full path)
            # Even if self.photos_taken is empty, still generate files
            photo_filenames = []
            if self.photos_taken:
                photo_filenames = [os.path.basename(path) for path in self.photos_taken]
            
            # Generate files.json (even if photo_filenames is empty)
            self.metadata_generator.create_files_json(photo_filenames)
            
            # Generate scan.toml (independent of photos)
            self.metadata_generator.create_scan_toml(
                self.num_positions, self.num_circles, self.circle_radius, self.z_offset
            )
            
            print(f"\nMetadata generated:")
            print(f"- images.json: {os.path.join(self.session_dirs['metadata'], 'images.json')}")
            print(f"- files.json: {os.path.join(self.session_dirs['main'], 'files.json')}")
            print(f"- scan.toml: {os.path.join(self.session_dirs['main'], 'scan.toml')}")
            
            if not self.photos_taken:
                print("Note: files.json generated without photos as no photos were taken")
            
            print("\nImage acquisition completed!")
            print(f"Total photos taken: {len(self.photos_taken)}/{self.num_positions*self.num_circles}")
            print(f"Photos saved in: {self.session_dirs['images']}")
            print(f"Metadata saved in: {self.session_dirs['metadata_images']}")
            
            return True
            
        except KeyboardInterrupt:
            print("\nAcquisition interrupted by user")
            return False
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Properly shut down the system"""
        print("\nShutting down acquisition system...")
        
        # Stop controllers in reverse order of initialization
        if hasattr(self, 'gimbal') and self.gimbal:
            self.gimbal.shutdown()
        
        if hasattr(self, 'camera') and self.camera:
            self.camera.shutdown()
        
        if hasattr(self, 'cnc') and self.cnc:
            self.cnc.shutdown()
        
        self.initialized = False
        print("Acquisition system shut down.")