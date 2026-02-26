#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified storage manager for files and directories
Combines core storage functionality with targeting-specific data operations
"""

import os
import json
import time
import numpy as np
import open3d as o3d
from datetime import datetime
from scipy.spatial import cKDTree
from core.utils import config

class StorageManager:
    def __init__(self, parent_dir=None, mode="acquisition"):
        """Initialize the storage manager"""
        # Determine parent directory
        if parent_dir is None:
            # First create results directory if it doesn't exist
            os.makedirs(config.RESULTS_DIR, exist_ok=True)
            
            if mode == "acquisition":
                self.parent_dir = os.path.join(config.RESULTS_DIR, config.ACQUISITION_DIR)
            else:  # targeting
                self.parent_dir = os.path.join(config.RESULTS_DIR, config.TARGETING_DIR)
        else:
            self.parent_dir = parent_dir
        
        self.mode = mode
        self.dirs = None
    
    def create_directory_structure(self, suffix=None):
        """
        Create a complete directory structure for the current execution
        
        Args:
            suffix: Optional suffix for directory name
            
        Returns:
            Dictionary of created paths
        """
        # Create parent directory if it doesn't exist
        os.makedirs(self.parent_dir, exist_ok=True)
        
        # Generate timestamp for directory name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Create main directory name
        if suffix:
            dir_name = f"{suffix}_{timestamp}"
        else:
            if self.mode == "acquisition":
                dir_name = f"circular_scan_{timestamp}"  # More descriptive name
            else:  # targeting
                dir_name = f"leaf_analysis_{timestamp}"  # More descriptive name
        
        # Full path to main directory
        main_dir = os.path.join(self.parent_dir, dir_name)
        
        # Create subdirectories based on mode
        if self.mode == "acquisition":
            # Structure for acquisition
            images_dir = os.path.join(main_dir, "images")
            metadata_dir = os.path.join(main_dir, "metadata")
            metadata_images_dir = os.path.join(metadata_dir, "images")
            
            # Create directories
            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(metadata_dir, exist_ok=True)
            os.makedirs(metadata_images_dir, exist_ok=True)
            
            # Store paths
            self.dirs = {
                "main": main_dir,
                "images": images_dir,
                "metadata": metadata_dir,
                "metadata_images": metadata_images_dir
            }
            
            print(f"Directory created for photos: {main_dir}")
            print(f"Subdirectories created: images/, metadata/, metadata/images/")
            
        else:  # targeting
            # Structure for targeting
            images_dir = os.path.join(main_dir, "images")
            analysis_dir = os.path.join(main_dir, "analysis")
            visualization_dir = os.path.join(main_dir, "visualizations")
            
            # Create directories
            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(analysis_dir, exist_ok=True)
            os.makedirs(visualization_dir, exist_ok=True)
            
            # Store paths
            self.dirs = {
                "main": main_dir,
                "images": images_dir,
                "analysis": analysis_dir,
                "visualizations": visualization_dir
            }
            
            print(f"Directory created for results: {main_dir}")
            print(f"Subdirectories created: images/, analysis/, visualizations/")
        
        return self.dirs
    
    def save_json(self, data, filename, subdirectory=None):
        """Save data as JSON"""
        if self.dirs is None:
            raise RuntimeError("Directory structure not initialized")
        
        try:
            # Determine full path
            if subdirectory and subdirectory in self.dirs:
                filepath = os.path.join(self.dirs[subdirectory], filename)
            else:
                filepath = os.path.join(self.dirs["main"], filename)
            
            # Create parent directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save data
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f"JSON file saved: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Error saving JSON file: {e}")
            return None
    
    def save_toml(self, content, filename):
        """Save content as TOML"""
        if self.dirs is None:
            raise RuntimeError("Directory structure not initialized")
        
        try:
            # Determine full path
            filepath = os.path.join(self.dirs["main"], filename)
            
            # Create parent directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save content
            with open(filepath, 'w') as f:
                f.write(content)
                
            print(f"TOML file saved: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Error saving TOML file: {e}")
            return None

    # === TARGETING-SPECIFIC METHODS (from targeting/modules/data_manager.py) ===
    
    def load_and_scale_pointcloud(self, file_path, scale_factor=0.001):
        """
        Load and scale point cloud
        """
        print(f"Loading point cloud from {file_path}...")
        
        try:
            # Check file existence
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_path} does not exist.")
            
            # Load cloud with Open3D
            pcd = o3d.io.read_point_cloud(file_path)
            points = np.asarray(pcd.points) * scale_factor
            pcd.points = o3d.utility.Vector3dVector(points)
            
            print(f"Cloud loaded: {len(points)} points, scale: {scale_factor}")
            min_bound = np.min(points, axis=0)
            max_bound = np.max(points, axis=0)
            size = max_bound - min_bound
            print(f"Dimensions: {size[0]:.3f} x {size[1]:.3f} x {size[2]:.3f} m")
            
            return pcd, points
            
        except Exception as e:
            print(f"ERROR: {e}")
            raise

    def apply_cropping_method(self, points, crop_method='single_furthest', crop_percentage=0.25, z_offset=0.0):
        """Apply chosen cropping method"""
        z_values = points[:, 2]
        min_z, max_z = np.min(z_values), np.max(z_values)
        
        if crop_method == 'none':
            z_threshold = min_z
        elif crop_method == 'top_percentage':
            z_range = max_z - min_z
            z_threshold = max_z - (z_range * (1.0 - crop_percentage))
        else:  # single_furthest (default)
            xy_points = points[:, :2]
            xy_center = np.mean(xy_points, axis=0)
            distances = np.sqrt(np.sum((xy_points - xy_center)**2, axis=1))
            furthest_idx = np.argmax(distances)
            furthest_point_z = points[furthest_idx, 2]
            z_threshold = furthest_point_z - z_offset
        
        return z_threshold

    def compute_cropped_alpha_shape(self, pcd, points, alpha_value=0.1, crop_method='single_furthest', 
                                  crop_percentage=0.25, z_offset=0.0, output_dir=None):
        """Compute cropped alpha shape"""
        # Apply cropping
        z_threshold = self.apply_cropping_method(points, crop_method, crop_percentage, z_offset)
        
        # Crop points
        mask = points[:, 2] >= z_threshold
        cropped_points = points[mask]
        n_cropped = len(cropped_points)
        
        print(f"Points after cropping: {n_cropped} ({n_cropped/len(points)*100:.1f}%)")
        print(f"Z threshold: {z_threshold:.4f} m")
        
        # Create cropped cloud
        cropped_pcd = o3d.geometry.PointCloud()
        cropped_pcd.points = o3d.utility.Vector3dVector(cropped_points)
        
        # Calculate Alpha Shape
        print(f"Computing Alpha Shape: alpha = {alpha_value}")
        start_time = time.time()
        
        try:
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(cropped_pcd, alpha_value)
            alpha_points = np.asarray(mesh.vertices)
            
            print(f"Alpha Shape computed in {time.time() - start_time:.2f}s")
            print(f"Alpha Points: {len(alpha_points)} ({len(alpha_points)/n_cropped*100:.1f}%)")
            
            # Light re-cropping to eliminate residues
            z_min, z_max = np.min(points[:, 2]), np.max(points[:, 2])
            z_range = z_max - z_min
            recrop_offset = 0.005 * z_range
            recrop_threshold = z_threshold + recrop_offset
            
            # Apply re-cropping
            recrop_mask = alpha_points[:, 2] >= recrop_threshold
            alpha_points = alpha_points[recrop_mask]
            
            print(f"Re-cropping: offset of {recrop_offset:.4f} m")
            print(f"Final points: {len(alpha_points)}")
            
            # Create final point cloud
            alpha_pcd = o3d.geometry.PointCloud()
            alpha_pcd.points = o3d.utility.Vector3dVector(alpha_points)
            
            # Save Alpha Shape if directory specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                alpha_output = os.path.join(output_dir, f"alpha_shape_{alpha_value:.3f}.ply")
                o3d.io.write_point_cloud(alpha_output, alpha_pcd)
                print(f"Alpha Shape saved: {alpha_output}")
            
            return alpha_pcd, alpha_points
            
        except Exception as e:
            print(f"ERROR computing Alpha Shape: {e}")
            raise

    def save_leaves_data(self, leaves_data, output_file):
        """Save leaf data in JSON format"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # For each leaf, filter fields to exclude complete points
            leaves_to_save = []
            for leaf in leaves_data:
                leaf_copy = leaf.copy()
                
                # Remove voluminous fields
                if 'points' in leaf_copy:
                    del leaf_copy['points']
                if 'points_indices' in leaf_copy:
                    del leaf_copy['points_indices']
                
                leaves_to_save.append(leaf_copy)
            
            with open(output_file, 'w') as f:
                json.dump({"leaves": leaves_to_save}, f, indent=2)
                
            print(f"Data saved to {output_file}")
            return True
        except Exception as e:
            print(f"Error during save: {e}")
            return False

    def load_leaves_data(self, input_file):
        """Load leaf data from JSON file"""
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            # Validate structure
            if "leaves" not in data:
                raise ValueError("Invalid JSON format: missing 'leaves' key")
            
            print(f"Data loaded: {len(data['leaves'])} leaves")
            return data["leaves"]
        except Exception as e:
            print(f"Error during loading: {e}")
            raise

    def create_output_directory(self):
        """Create a dated output directory"""
        # Parent directory
        parent_dir = "leaf_targeting_results"
        
        # Ensure parent directory exists
        os.makedirs(parent_dir, exist_ok=True)
        
        # Create subdirectory with current date and time
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = os.path.join(parent_dir, f"leaf_targeting_{timestamp}")
        
        # Create complete directory structure
        images_dir = os.path.join(output_dir, "images")
        analysis_dir = os.path.join(output_dir, "analysis")
        visualization_dir = os.path.join(output_dir, "visualizations")
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(analysis_dir, exist_ok=True)
        os.makedirs(visualization_dir, exist_ok=True)
        
        print(f"Directory created for results: {output_dir}")
        print(f"Subdirectories created: images/, analysis/, visualizations/")
        
        return {
            "main": output_dir,
            "images": images_dir,
            "analysis": analysis_dir,
            "visualizations": visualization_dir
        }


# Convenience functions for backward compatibility
def load_and_scale_pointcloud(file_path, scale_factor=0.001):
    """Convenience function for point cloud loading"""
    storage = StorageManager()
    return storage.load_and_scale_pointcloud(file_path, scale_factor)

def compute_cropped_alpha_shape(pcd, points, alpha_value=0.1, crop_method='single_furthest', 
                              crop_percentage=0.25, z_offset=0.0, output_dir=None):
    """Convenience function for alpha shape computation"""
    storage = StorageManager()
    return storage.compute_cropped_alpha_shape(pcd, points, alpha_value, crop_method, 
                                             crop_percentage, z_offset, output_dir)

def save_leaves_data(leaves_data, output_file):
    """Convenience function for saving leaf data"""
    storage = StorageManager()
    return storage.save_leaves_data(leaves_data, output_file)

def load_leaves_data(input_file):
    """Convenience function for loading leaf data"""
    storage = StorageManager()
    return storage.load_leaves_data(input_file)

def create_output_directory():
    """Convenience function for creating output directory"""
    storage = StorageManager()
    return storage.create_output_directory()