#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Metadata generator for acquisition images
"""

import os
import json
from datetime import datetime

class MetadataGenerator:
    def __init__(self, storage_manager):
        """
        Initialize the metadata generator
        
        Args:
            storage_manager: StorageManager instance
        """
        self.storage = storage_manager
        self.dirs = storage_manager.dirs
    
    def create_image_metadata(self, image_id, camera_pose, output_dir=None):
        """
        Create JSON metadata for a given image
        
        Args:
            image_id: Image identifier (e.g. "00059_rgb")
            camera_pose: Dictionary containing camera pose
            output_dir: Output directory for JSON file (optional)
            
        Returns:
            Path to created JSON file
        """
        try:
            # Extract pose values
            x, y, z = camera_pose['x'], camera_pose['y'], camera_pose['z']
            
            # Get pan and tilt angles
            pan_angle = camera_pose.get('pan_angle', 0)
            tilt_angle = camera_pose.get('tilt_angle', 0)
            
            # Format ID for shot_id (remove "rgb")
            shot_id = image_id.split('_')[0]
            
            # Create metadata dictionary
            metadata = {
                "approximate_pose": [
                    x * 1000,  # Convert to mm as per examples
                    y * 1000,
                    z * 1000,
                    pan_angle,
                    0  # Last array element, 0 according to examples
                ],
                "channel": "rgb",
                "shot_id": shot_id
            }
            
            # Determine output directory
            if output_dir is None:
                if self.dirs and "metadata_images" in self.dirs:
                    output_dir = self.dirs["metadata_images"]
                else:
                    raise ValueError("Output directory not specified and not available in self.dirs")
            
            # Full path for JSON file
            json_path = os.path.join(output_dir, f"{image_id}.json")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Save JSON file
            with open(json_path, 'w') as f:
                json.dump(metadata, f, indent=4)
                
            print(f"Metadata saved: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Error creating metadata: {e}")
            return None
    
    def create_images_json(self, workspace):
        """
        Create images.json file in metadata directory
        
        Args:
            workspace: Values for workspace section of the file
            
        Returns:
            Path to created JSON file
        """
        try:
            # Check that metadata directory exists
            if not self.dirs or "metadata" not in self.dirs:
                raise ValueError("Metadata directory not defined in self.dirs")
            
            # Create images.json dictionary
            images_json = {
                "channels": [
                    "rgb"
                ],
                "hardware": {
                    "X_motor": "X-Carve NEMA23",
                    "Y_motor": "X-Carve NEMA23",
                    "Z_motor": "X-Carve NEMA23",
                    "frame": "30profile v1",
                    "pan_motor": "iPower Motor GM4108H-120T Brushless Gimbal Motor",
                    "sensor": "RX0",
                    "tilt_motor": "None"
                },
                "object": {
                    "DAG": 40,
                    "dataset_id": "3dt",
                    "experiment_id": "3dt_" + datetime.now().strftime("%d-%m-%Y"),
                    "growth_conditions": "SD+LD",
                    "growth_environment": "Lyon-indoor",
                    "plant_id": "3dt_chenoA",
                    "sample": "main_stem",
                    "seed_stock": "Col-0",
                    "species": "chenopodium album",
                    "treatment": "None"
                },
                "task_name": "ImagesFilesetExists",
                "task_params": {
                    "fileset_id": "images",
                    "scan_id": "Col_A_" + datetime.now().strftime("%Y-%m-%d")
                },
                "workspace": workspace
            }
            
            # Path for JSON file
            json_path = os.path.join(self.dirs["metadata"], "images.json")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Save file
            with open(json_path, 'w') as f:
                json.dump(images_json, f, indent=4)
            
            print(f"images.json file created: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Error creating images.json file: {e}")
            return None
    
    def create_files_json(self, photo_files):
        """
        Create files.json in the main directory root
        
        Args:
            photo_files: List of photo filenames
            
        Returns:
            Path to created JSON file
        """
        try:
            # Check that main directory exists
            if not self.dirs or "main" not in self.dirs:
                raise ValueError("Main directory not defined in self.dirs")
            
            # Basic structure
            files_json = {
                "filesets": [
                    {
                        "files": [],
                        "id": "images"
                    }
                ]
            }
            
            # Add each photo to files list
            for photo_file in photo_files:
                # Ensure we have just the filename without path
                filename = os.path.basename(photo_file)
                file_id = os.path.splitext(filename)[0]
                
                # Add to list
                files_json["filesets"][0]["files"].append({
                    "file": filename,
                    "id": file_id
                })
            
            # Path for JSON file
            json_path = os.path.join(self.dirs["main"], "files.json")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Save file
            with open(json_path, 'w') as f:
                json.dump(files_json, f, indent=4)
            
            print(f"files.json file created: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Error creating files.json file: {e}")
            return None
    
    def create_scan_toml(self, num_positions, num_circles, radius, z_offset):
        """
        Create scan.toml at the main directory root
        
        Args:
            num_positions: Number of positions per circle
            num_circles: Number of circles
            radius: Circle radius in meters
            z_offset: Z offset between circles in meters
            
        Returns:
            Path to created TOML file
        """
        try:
            # Check that main directory exists
            if not self.dirs or "main" not in self.dirs:
                raise ValueError("Main directory not defined in self.dirs")
            
            # TOML file content
            scan_toml_content = f"""[ScanPath]
class_name = "Circle"

[retcode]
already_running = 10
missing_data = 20
not_run = 25
task_failed = 30
scheduling_error = 35
unhandled_exception = 40

[ScanPath.kwargs]
center_x = 375
center_y = 350
z = 80
tilt = 0
radius = {int(radius * 1000)}
n_points = {num_positions * num_circles}

[Scan.scanner.camera]
module = "romiscanner.sony"

[Scan.scanner.gimbal]
module = "romiscanner.blgimbal"

[Scan.scanner.cnc]
module = "romiscanner.grbl"

[Scan.metadata.workspace]
x = [ 200, 600,]
y = [ 200, 600,]
z = [ -100, 300,]

[Scan.metadata.object]
species = "chenopodium album"
seed_stock = "Col-0"
plant_id = "3dt_chenoA"
growth_environment = "Lyon-indoor"
growth_conditions = "SD+LD"
treatment = "None"
DAG = 40
sample = "main_stem"
experiment_id = "3dt_{datetime.now().strftime("%d-%m-%Y")}"
dataset_id = "3dt"

[Scan.metadata.hardware]
frame = "30profile v1"
X_motor = "X-Carve NEMA23"
Y_motor = "X-Carve NEMA23"
Z_motor = "X-Carve NEMA23"
pan_motor = "iPower Motor GM4108H-120T Brushless Gimbal Motor"
tilt_motor = "None"
sensor = "RX0"

[Scan.scanner.camera.kwargs]
device_ip = "192.168.122.1"
api_port = "10000"
postview = true
use_flashair = false
rotation = 270

[Scan.scanner.gimbal.kwargs]
port = "/dev/ttyACM1"
has_tilt = false
zero_pan = 0
invert_rotation = true

[Scan.scanner.cnc.kwargs]
homing = true
port = "/dev/ttyACM0"
"""
            
            # Path for TOML file
            toml_path = os.path.join(self.dirs["main"], "scan.toml")
            
            # Create directory if needed
            os.makedirs(os.path.dirname(toml_path), exist_ok=True)
            
            # Save file
            with open(toml_path, 'w') as f:
                f.write(scan_toml_content)
            
            print(f"scan.toml file created: {toml_path}")
            return toml_path
            
        except Exception as e:
            print(f"Error creating scan.toml file: {e}")
            return None