#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main script for leaf targeting system with integrated fluorescence sensor
Unified version that replaces both leaf_targeting.py and leaf_targeting_with_fluo.py
MODIFIED: Added viewer support (pointcloud copy + random health_status)
"""

import os
import sys
import argparse
import numpy as np
import time
import random
import shutil

# Imports from new architecture
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.hardware.fluo_controller import FluoController
from core.data.storage_manager import StorageManager
from core.utils import config

# Imports from unified storage manager
from core.data.storage_manager import StorageManager
from targeting.modules.leaf_analyzer import calculate_adaptive_radius, build_connectivity_graph
from targeting.modules.leaf_analyzer import detect_communities_louvain_multiple, extract_leaf_data_from_communities
from targeting.modules.interactive_selector import select_leaf_with_matplotlib
from targeting.modules.path_planner import plan_safe_path, plan_complete_path
from targeting.modules.robot_controller import RobotController
from targeting.modules.visualization import visualize_path, visualize_complete_path

# Health status calculation based on fluorescence
HEALTH_THRESHOLDS = {
    "Critique": 0.010,     # < 0.010
    "Stressé": 0.015,      # 0.010-0.015  
    "Normal": 0.020,       # 0.015-0.020
    "Bon": 0.025,          # 0.020-0.025
    "Excellent": float('inf')  # > 0.025
}

HEALTH_COLORS = {
    "Critique": "#D32F2F",    # Rouge foncé
    "Stressé": "#FF7043",     # Orange-rouge
    "Normal": "#FFA726",      # Orange
    "Bon": "#66BB6A",         # Vert clair
    "Excellent": "#2E7D32"    # Vert foncé
}

def calculate_health_from_fluorescence(mean_fluorescence):
    """Calcule l'état de santé basé sur la moyenne de fluorescence"""
    if mean_fluorescence < HEALTH_THRESHOLDS["Critique"]:
        return "Critique"
    elif mean_fluorescence < HEALTH_THRESHOLDS["Stressé"]:
        return "Stressé"
    elif mean_fluorescence < HEALTH_THRESHOLDS["Normal"]:
        return "Normal"
    elif mean_fluorescence < HEALTH_THRESHOLDS["Bon"]:
        return "Bon"
    else:
        return "Excellent"

class LeafTargeting:
    """Main class for leaf targeting system with integrated fluorescence sensor"""
    
    def __init__(self, args=None):
        """
        Initialize the leaf targeting system
        
        Args:
            args: Command line arguments (optional)
        """
        # Default parameters
        self.point_cloud_path = None
        self.scale = 0.001
        self.alpha = 0.1
        self.crop_method = 'none'
        self.crop_percentage = 0.25
        self.z_offset = 0.0
        self.arduino_port = config.ARDUINO_PORT
        self.simulate = False
        self.take_photos = True  # NEW: Default to True (auto photos)
        self.louvain_coeff = 0.5
        self.distance = 0.1
        self.enable_fluorescence = config.ENABLE_FLUORESCENCE  # From config
        
        # Update parameters with command line arguments
        if args:
            self.update_from_args(args)
        
        # Hardware controllers
        self.cnc = None
        self.camera = None
        self.gimbal = None
        self.fluo_sensor = None
        self.robot = None
        
        # Storage manager
        self.storage = None
        self.session_dirs = None
        
        # Data
        self.pcd = None
        self.points = None
        self.alpha_pcd = None
        self.alpha_points = None
        self.leaves_data = []
        self.selected_leaves = []
        
        # State
        self.initialized = False
    
    def update_from_args(self, args):
        """Update parameters from command line arguments"""
        if hasattr(args, 'point_cloud') and args.point_cloud is not None:
            self.point_cloud_path = args.point_cloud
        
        if hasattr(args, 'scale') and args.scale is not None:
            self.scale = args.scale
        
        if hasattr(args, 'alpha') and args.alpha is not None:
            self.alpha = args.alpha
        
        if hasattr(args, 'crop_method') and args.crop_method is not None:
            self.crop_method = args.crop_method
        
        if hasattr(args, 'crop_percentage') and args.crop_percentage is not None:
            self.crop_percentage = args.crop_percentage
        
        if hasattr(args, 'z_offset') and args.z_offset is not None:
            self.z_offset = args.z_offset
        
        if hasattr(args, 'arduino_port') and args.arduino_port is not None:
            self.arduino_port = args.arduino_port
        
        if hasattr(args, 'simulate') and args.simulate is not None:
            self.simulate = args.simulate
        
        # NEW: Inverted photo logic
        if hasattr(args, 'no_photo') and args.no_photo:
            self.take_photos = False
        
        if hasattr(args, 'louvain_coeff') and args.louvain_coeff is not None:
            self.louvain_coeff = args.louvain_coeff
            
        if hasattr(args, 'distance') and args.distance is not None:
            self.distance = args.distance
        
        # NEW: Fluorescence disable option
        if hasattr(args, 'disable_fluorescence') and args.disable_fluorescence:
            self.enable_fluorescence = False
    
    def initialize(self):
        """Initialize components and directories"""
        if self.initialized:
            return True
        
        try:
            print("\n=== Initializing leaf targeting system ===")
            
            # Check point cloud path
            if not self.point_cloud_path:
                print("ERROR: Point cloud path not specified")
                return False
            
            if not os.path.exists(self.point_cloud_path):
                print(f"ERROR: File {self.point_cloud_path} does not exist")
                return False
            
            # Create storage manager
            self.storage = StorageManager(mode="targeting")
            self.session_dirs = self.storage.create_directory_structure()
            
            print("\nDirectories created:")
            for key, path in self.session_dirs.items():
                print(f"- {key}: {path}")
            
            # Initialize hardware controllers (only if not in simulation mode)
            if not self.simulate:
                self.cnc = CNCController(config.CNC_SPEED)
                self.cnc.connect()
                
                self.camera = CameraController()
                self.camera.connect()
                self.camera.set_output_directory(self.session_dirs["images"])
                
                self.gimbal = GimbalController(self.arduino_port)
                self.gimbal.connect()
                
                # Initialize fluorescence sensor if enabled
                if self.enable_fluorescence:
                    try:
                        print("\n--- Initializing fluorescence sensor ---")
                        self.fluo_sensor = FluoController("fluo", "fluo")
                        
                        status = self.fluo_sensor.get_device_status()
                        if status['connected']:
                            print(f"✅ Fluorescence sensor ready: {status['status']}")
                        else:
                            print(f"⚠️  Fluorescence sensor not ready: {status['status']}")
                            print("   Continuing without fluorescence measurements...")
                            self.fluo_sensor = None
                    except Exception as e:
                        print(f"⚠️  Could not initialize fluorescence sensor: {e}")
                        print("   Continuing without fluorescence measurements...")
                        self.fluo_sensor = None
                else:
                    print("Fluorescence measurements disabled by configuration")
                
                # Initialize robot controller with optional fluorescence sensor
                self.robot = RobotController(
                    cnc=self.cnc,
                    camera=self.camera,
                    gimbal=self.gimbal,
                    fluo_sensor=self.fluo_sensor,
                    output_dirs=self.session_dirs
                )
            
            # Display parameters
            print(f"\nTargeting parameters:")
            print(f"- Point cloud: {self.point_cloud_path}")
            print(f"- Scale factor: {self.scale}")
            print(f"- Alpha value: {self.alpha}")
            print(f"- Cropping method: {self.crop_method}")
            print(f"- Distance to leaves: {self.distance} m")
            print(f"- Simulation mode: {'Enabled' if self.simulate else 'Disabled'}")
            print(f"- Auto photo mode: {'Enabled' if self.take_photos else 'Disabled'}")
            print(f"- Fluorescence measurements: {'Enabled' if self.fluo_sensor else 'Disabled'}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Initialization error: {e}")
            self.shutdown()
            return False
    
    def _calculate_health_status_from_fluorescence(self):
        """Calcule l'état de santé de chaque feuille basé sur les données de fluorescence"""
        print("Calculating health status from fluorescence data...")
        
        # =======================================================================
        # MODE ALÉATOIRE POUR POC - Génère des valeurs de fluorescence simulées
        # =======================================================================
        print("Using random fluorescence values for POC")
        for leaf in self.leaves_data:
            # Générer valeur aléatoire entre nos seuils de référence
            mock_fluorescence_mean = 0.005 + np.random.random() * 0.025  # Entre 0.005 et 0.030
            
            leaf["fluorescence_mean"] = mock_fluorescence_mean
            leaf["health_status"] = calculate_health_from_fluorescence(mock_fluorescence_mean)
            
            print(f"Leaf {leaf.get('id', '?')}: fluor={mock_fluorescence_mean:.4f} → {leaf['health_status']}")
        
        return
        
        # =======================================================================
        # VRAIE LOGIQUE (COMMENTÉE) - À utiliser avec de vraies mesures 
        # =======================================================================
        """
        # Si pas de capteur fluo, utiliser des valeurs aléatoires
        if not self.fluo_sensor:
            print("No fluorescence sensor - using mock data")
            for leaf in self.leaves_data:
                # Mock: valeurs aléatoires dans la gamme typique
                mock_measurements = [0.005 + np.random.random() * 0.025 for _ in range(20)]
                mean_fluor = np.mean(mock_measurements)
                leaf["fluorescence_mean"] = mean_fluor
                leaf["health_status"] = calculate_health_from_fluorescence(mean_fluor)
            return
        
        # Avec capteur : utiliser vraies données 
        for leaf in self.leaves_data:
            try:
                # TODO: Récupérer vraies mesures du capteur pour cette feuille
                # measurements = self.get_fluorescence_measurements_for_leaf(leaf['id'])
                # mean_fluor = np.mean(measurements)
                
                # Pour l'instant, utiliser mock data même avec capteur
                mock_measurements = [0.005 + np.random.random() * 0.025 for _ in range(20)]
                mean_fluor = np.mean(mock_measurements)
                
                leaf["fluorescence_mean"] = mean_fluor
                leaf["health_status"] = calculate_health_from_fluorescence(mean_fluor)
                
                print(f"Leaf {leaf.get('id', '?')}: fluor={mean_fluor:.4f} → {leaf['health_status']}")
                
            except Exception as e:
                print(f"Error calculating health for leaf {leaf.get('id', '?')}: {e}")
                leaf["fluorescence_mean"] = 0.015  # Fallback
                leaf["health_status"] = "Normal"
        """
    
    def run_targeting(self):
        """Execute the complete targeting process"""
        if not self.initialize():
            return False
        
        try:
            # 1-9. Processing steps using unified storage manager
            print("\n=== 1. Loading point cloud ===")
            self.pcd, self.points = self.storage.load_and_scale_pointcloud(self.point_cloud_path, self.scale)
            
            print("\n=== 2. Computing Alpha Shape ===")
            self.alpha_pcd, self.alpha_points = self.storage.compute_cropped_alpha_shape(
                self.pcd, self.points, self.alpha, self.crop_method, self.crop_percentage, 
                self.z_offset, self.session_dirs["analysis"]
            )
            
            print("\n=== 3. Computing connectivity radius ===")
            radius = calculate_adaptive_radius(self.alpha_points)
            
            print(f"\n=== 4. Louvain Coefficient: {self.louvain_coeff} ===")
            coeff = self.louvain_coeff
            
            print("\n=== 5. Building connectivity graph ===")
            graph = build_connectivity_graph(self.alpha_points, radius)
            
            min_size = max(10, len(self.alpha_points) // 30)
            print(f"\n=== 6. Minimum community size: {min_size} points ===")
            
            print("\n=== 7. Detecting communities ===")
            communities = detect_communities_louvain_multiple(graph, coeff, min_size, n_iterations=5)
            
            print("\n=== 8. Extracting leaf data ===")
            self.leaves_data = extract_leaf_data_from_communities(
                communities, self.alpha_points, distance=self.distance
            )
            
            # NEW: Calculate health status based on fluorescence
            self._calculate_health_status_from_fluorescence()
            
            leaves_json = os.path.join(self.session_dirs["analysis"], "leaves_data.json")
            self.storage.save_leaves_data(self.leaves_data, leaves_json)
            
            # NEW: Copy point cloud for viewer access
            print("Copying point cloud for viewer...")
            pointcloud_copy = os.path.join(self.session_dirs["main"], "pointcloud.ply")
            shutil.copy(self.point_cloud_path, pointcloud_copy)
            print(f"Point cloud copied for viewer: {pointcloud_copy}")
            
            print("\n=== 9. Interactive leaf selection ===")
            self.selected_leaves = select_leaf_with_matplotlib(
                self.leaves_data, self.points, self.session_dirs["visualizations"]
            )
            
            if not self.selected_leaves:
                print("No leaves selected. Ending program.")
                return True
            
            # 10-11. Path planning and visualization (same as before)
            print("\n=== 10. Planning complete trajectory ===")
            current_position = [0, 0, 0]
            
            if not self.simulate and self.cnc:
                pos = self.cnc.get_position()
                current_position = [pos['x'], pos['y'], pos['z']]
            
            target_points = [leaf["target_point"] for leaf in self.selected_leaves]
            
            complete_path = plan_complete_path(
                current_position, target_points, config.CENTER_POINT, config.CIRCLE_RADIUS, 
                config.NUM_POSITIONS
            )
            
            print("\n=== 11. Visualizing complete trajectory ===")
            
            leaf_points_list = []
            leaf_normals_list = []
            
            for leaf in self.selected_leaves:
                if 'points' in leaf:
                    leaf_points_list.append(np.array(leaf['points']))
                else:
                    leaf_points_list.append(np.array([leaf['centroid']]))
                
                if 'normal' in leaf:
                    leaf_normals_list.append(np.array(leaf['normal']))
                else:
                    leaf_normals_list.append(np.array([0, 0, 1]))
            
            visualize_complete_path(
                complete_path, self.points, leaf_points_list, leaf_normals_list, 
                self.session_dirs["visualizations"]
            )
            
            if self.simulate:
                print("\nSimulation mode: Program complete.")
                return True
            
            # 12. Execute trajectory with unified photo/fluorescence logic
            print("\n=== 12. Executing trajectory ===")
            
            if self.fluo_sensor:
                print("🧬 Fluorescence measurements enabled")
            else:
                print("📷 Photo-only mode")
            
            leaf_centroids = [leaf['centroid'] for leaf in self.selected_leaves]
            leaf_ids = [leaf['id'] for leaf in self.selected_leaves]
            
            success = self.robot.execute_path(
                complete_path,
                leaf_centroids=leaf_centroids,
                leaf_ids=leaf_ids,
                auto_photo=self.take_photos,  # Use unified photo logic
                stabilization_time=config.STABILIZATION_TIME
            )
            
            if success:
                print("\n✅ Trajectory completed successfully.")
                if self.fluo_sensor:
                    print("🧬 Fluorescence data saved in analysis/ directory")
                print(f"\n🌐 Launch viewer: python fluorescence_viewer_browser.py")
                print(f"📂 Session data: {self.session_dirs['main']}")
            else:
                print("\n❌ Error during trajectory execution.")
            
            return success
            
        except KeyboardInterrupt:
            print("\nProgram interrupted by user.")
            return False
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Properly shut down the system"""
        print("\nShutting down targeting system...")
        
        if hasattr(self, 'robot') and self.robot and not self.simulate:
            self.robot.shutdown()
        elif not self.simulate:
            if hasattr(self, 'fluo_sensor') and self.fluo_sensor:
                try:
                    # Fluorescence sensor doesn't have explicit shutdown, just let it be
                    pass
                except:
                    pass
            
            if hasattr(self, 'gimbal') and self.gimbal:
                self.gimbal.shutdown()
            
            if hasattr(self, 'camera') and self.camera:
                self.camera.shutdown()
            
            if hasattr(self, 'cnc') and self.cnc:
                self.cnc.shutdown()
        
        self.initialized = False
        print("Targeting system shut down.")


def parse_arguments():
    """Parse command line arguments with unified fluorescence and photo options"""
    parser = argparse.ArgumentParser(description='Leaf targeting system with integrated fluorescence measurements')
    
    parser.add_argument('point_cloud', help='Point cloud file (PLY/PCD)')
    parser.add_argument('--scale', type=float, default=0.001, help='Scale factor for point cloud (default: 0.001 = mm->m)')
    parser.add_argument('--alpha', type=float, default=0.1, help='Alpha value for Alpha Shape (default: 0.1)')
    parser.add_argument('--crop_method', choices=['none', 'top_percentage', 'single_furthest'], 
                      default='none', help='Cropping method (default: none)')
    parser.add_argument('--crop_percentage', type=float, default=0.25, help='Percentage for top_percentage (default: 0.25)')
    parser.add_argument('--z_offset', type=float, default=0.0, help='Z offset for cropping (default: 0.0)')
    parser.add_argument('--arduino_port', default=config.ARDUINO_PORT, help=f'Arduino serial port (default: {config.ARDUINO_PORT})')
    parser.add_argument('--simulate', action='store_true', help='Simulation mode (no robot control)')
    
    # NEW: Inverted photo logic
    parser.add_argument('--no-photo', action='store_true', help='Disable automatic photo capture (default: photos enabled)')
    
    parser.add_argument('--louvain_coeff', type=float, default=0.5, help='Coefficient for Louvain detection (default: 0.5)')
    parser.add_argument('--distance', type=float, default=0.1, help='Distance to target leaves in meters (default: 0.1 m)')
    
    # NEW: Fluorescence disable option
    parser.add_argument('--disable-fluorescence', action='store_true', 
                       help='Disable fluorescence measurements (photo only)')
    
    return parser.parse_args()

def main():
    """Main function with unified fluorescence integration"""
    args = parse_arguments()
    targeting = LeafTargeting(args)
    success = targeting.run_targeting()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())