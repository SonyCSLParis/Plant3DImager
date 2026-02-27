#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main script for leaf targeting system with integrated fluorescence sensor.
Pipeline updated to use eigenvalue + graph-based leaf detection
(replaces Alpha Shape + Louvain community detection).

MODIFIED: Alpha Shape removed, detection replaced by detect_leaves()
"""

import os
import sys
import argparse
import numpy as np
import time
import shutil

# Core imports
from core.hardware.cnc_controller import CNCController
from core.hardware.camera_controller import CameraController
from core.hardware.gimbal_controller import GimbalController
from core.hardware.fluo_controller import FluoController
from core.data.storage_manager import StorageManager
from core.utils import config

# Leaf detection — single entry point
from targeting.modules.leaf_analyzer import detect_leaves

# Other targeting modules (unchanged)
from targeting.modules.interactive_selector import select_leaf_with_matplotlib
from targeting.modules.path_planner import plan_complete_path
from targeting.modules.robot_controller import RobotController
from targeting.modules.visualization import visualize_complete_path


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class LeafTargeting:
    """Leaf targeting system — eigenvalue + graph-based detection."""

    def __init__(self, args=None):

        # ── Detection parameters (new method) ────────────────────────────────
        self.k_kmeans              = config.get("SEG_K_KMEANS", 3)
        self.k_neighbors           = config.get("SEG_K_NEIGHBORS", 150)
        self.max_distance          = config.get("SEG_MAX_DISTANCE", 0.002)
        self.min_cluster_size      = config.get("SEG_MIN_CLUSTER_SIZE", 1000)
        self.angle_threshold       = config.get("SEG_ANGLE_THRESHOLD", 15.0)
        self.merge_distance        = config.get("SEG_MERGE_DISTANCE", 0.015)
        self.distance              = config.get("TARGETING_DISTANCE", 0.1)

        # ── General parameters ────────────────────────────────────────────────
        self.point_cloud_path = None
        self.scale            = 0.001
        self.arduino_port     = config.ARDUINO_PORT
        self.simulate         = False
        self.take_photos      = True
        self.enable_fluorescence = config.ENABLE_FLUORESCENCE

        if args:
            self._update_from_args(args)

        # ── Hardware ──────────────────────────────────────────────────────────
        self.cnc        = None
        self.camera     = None
        self.gimbal     = None
        self.fluo_sensor = None
        self.robot      = None

        # ── Storage ───────────────────────────────────────────────────────────
        self.storage      = None
        self.session_dirs = None

        # ── Data ──────────────────────────────────────────────────────────────
        self.pcd          = None
        self.points       = None
        self.leaves_data  = []
        self.selected_leaves = []

        self.initialized = False

    # ── Parameter update ─────────────────────────────────────────────────────

    def _update_from_args(self, args):
        mapping = [
            ("point_cloud",        "point_cloud_path"),
            ("scale",              "scale"),
            ("arduino_port",       "arduino_port"),
            ("simulate",           "simulate"),
            ("k_kmeans",           "k_kmeans"),
            ("k_neighbors",        "k_neighbors"),
            ("max_distance",       "max_distance"),
            ("min_cluster_size",   "min_cluster_size"),
            ("angle_threshold",    "angle_threshold"),
            ("merge_distance",     "merge_distance"),
            ("distance",           "distance"),
        ]
        for arg_name, attr_name in mapping:
            val = getattr(args, arg_name, None)
            if val is not None:
                setattr(self, attr_name, val)

        if getattr(args, "no_photo", False):
            self.take_photos = False
        if getattr(args, "disable_fluorescence", False):
            self.enable_fluorescence = False

    # ── Initialization ────────────────────────────────────────────────────────

    def initialize(self):
        if self.initialized:
            return True
        try:
            print("\n=== Initializing leaf targeting system ===")

            if not self.point_cloud_path:
                print("No point cloud specified — searching for latest in results/pointclouds/...")
                self.point_cloud_path = find_latest_pointcloud()
                if not self.point_cloud_path:
                    print("ERROR: No point cloud found in results/pointclouds/")
                    return False
            if not os.path.exists(self.point_cloud_path):
                print(f"ERROR: File {self.point_cloud_path} does not exist")
                return False

            # Directories
            self.storage = StorageManager(mode="targeting")
            self.session_dirs = self.storage.create_directory_structure()

            print("\nDirectories created:")
            for key, path in self.session_dirs.items():
                print(f"  - {key}: {path}")

            # Hardware (skipped in simulation)
            if not self.simulate:
                self.cnc = CNCController(config.CNC_SPEED)
                self.cnc.connect()

                self.camera = CameraController()
                self.camera.connect()
                self.camera.set_output_directory(self.session_dirs["images"])

                self.gimbal = GimbalController(self.arduino_port)
                self.gimbal.connect()

                if self.enable_fluorescence:
                    try:
                        print("\n--- Initializing fluorescence sensor ---")
                        self.fluo_sensor = FluoController("fluo", "fluo")
                        status = self.fluo_sensor.get_device_status()
                        if status["connected"]:
                            print(f"  Fluorescence sensor ready: {status['status']}")
                        else:
                            print(f"  Fluorescence sensor not ready: {status['status']}")
                            self.fluo_sensor = None
                    except Exception as e:
                        print(f"  Could not initialize fluorescence sensor: {e}")
                        self.fluo_sensor = None
                else:
                    print("  Fluorescence measurements disabled by configuration")

                self.robot = RobotController(
                    cnc=self.cnc,
                    camera=self.camera,
                    gimbal=self.gimbal,
                    fluo_sensor=self.fluo_sensor,
                    output_dirs=self.session_dirs,
                )

            # Summary
            print(f"\nDetection parameters:")
            print(f"  Point cloud    : {self.point_cloud_path}")
            print(f"  Scale factor   : {self.scale} (mm → m)")
            print(f"  k_kmeans       : {self.k_kmeans}")
            print(f"  k_neighbors    : {self.k_neighbors}")
            print(f"  max_distance   : {self.max_distance*1000:.1f} mm")
            print(f"  min_cluster_sz : {self.min_cluster_size} pts")
            print(f"  angle_threshold: {self.angle_threshold}°")
            print(f"  merge_distance : {self.merge_distance*1000:.1f} mm")
            print(f"  Approach dist  : {self.distance*100:.1f} cm")
            print(f"  Simulation     : {'ON' if self.simulate else 'OFF'}")
            print(f"  Auto photo     : {'ON' if self.take_photos else 'OFF'}")
            print(f"  Fluorescence   : {'ON' if self.fluo_sensor else 'OFF'}")

            self.initialized = True
            return True

        except Exception as e:
            print(f"Initialization error: {e}")
            self.shutdown()
            return False

    # ── Main pipeline ─────────────────────────────────────────────────────────

    def run_targeting(self):
        if not self.initialize():
            return False

        try:
            # ── 1. Load point cloud ───────────────────────────────────────────
            print("\n=== 1. Loading point cloud ===")
            self.pcd, self.points = self.storage.load_and_scale_pointcloud(
                self.point_cloud_path, self.scale
            )

            # ── 2. Detect leaves ──────────────────────────────────────────────
            print("\n=== 2. Detecting leaves (eigenvalue + graph) ===")
            self.leaves_data = detect_leaves(
                self.pcd,
                self.points,
                k_kmeans=self.k_kmeans,
                k_neighbors=self.k_neighbors,
                max_distance=self.max_distance,
                min_cluster_size=self.min_cluster_size,
                angle_threshold_deg=self.angle_threshold,
                merge_distance_threshold=self.merge_distance,
                distance=self.distance,
            )

            if not self.leaves_data:
                print("ERROR: No leaves detected. Adjust detection parameters.")
                return False

            # ── 3. Save leaf data ─────────────────────────────────────────────
            leaves_json = os.path.join(
                self.session_dirs["analysis"], "leaves_data.json"
            )
            self.storage.save_leaves_data(self.leaves_data, leaves_json)

            # ── 4b. Save segmentation point cloud for viewer ─────────────
            print("\n=== 3. Saving segmentation point cloud ===")
            seg_ply    = os.path.join(self.session_dirs["main"], "segmentation.ply")
            seg_labels = os.path.join(self.session_dirs["main"], "segmentation_labels.npy")
            self.storage.save_segmentation_pointcloud(self.leaves_data, seg_ply, seg_labels)

            # ── 5. Copy point cloud for viewer ───────────────────────────────
            print("\n=== 4. Copying point cloud for viewer ===")
            pointcloud_copy = os.path.join(
                self.session_dirs["main"], "pointcloud.ply"
            )
            shutil.copy(self.point_cloud_path, pointcloud_copy)
            print(f"  Copied: {pointcloud_copy}")

            # ── 6. Interactive leaf selection ─────────────────────────────────
            print("\n=== 5. Interactive leaf selection ===")
            self.selected_leaves = select_leaf_with_matplotlib(
                self.leaves_data, self.points, self.session_dirs["visualizations"]
            )

            if not self.selected_leaves:
                print("No leaves selected. Ending.")
                return True

            # ── 7. Path planning ──────────────────────────────────────────────
            print("\n=== 6. Planning trajectory ===")
            current_position = [0, 0, 0]
            if not self.simulate and self.cnc:
                pos = self.cnc.get_position()
                current_position = [pos["x"], pos["y"], pos["z"]]

            complete_path = plan_complete_path(current_position, self.selected_leaves)

            # ── 8. Trajectory visualization ───────────────────────────────────
            print("\n=== 7. Visualizing trajectory ===")
            leaf_points_list  = []
            leaf_normals_list = []
            for leaf in self.selected_leaves:
                leaf_points_list.append(
                    np.array(leaf["points"]) if "points" in leaf
                    else np.array([leaf["centroid"]])
                )
                leaf_normals_list.append(
                    np.array(leaf["normal"]) if "normal" in leaf
                    else np.array([0, 0, 1])
                )

            visualize_complete_path(
                complete_path,
                self.points,
                leaf_points_list,
                leaf_normals_list,
                self.session_dirs["visualizations"],
            )

            if self.simulate:
                print("\nSimulation mode: complete.")
                return True

            # ── 9. Execute trajectory ─────────────────────────────────────────
            print("\n=== 8. Executing trajectory ===")
            if self.fluo_sensor:
                print("  Fluorescence measurements enabled")
            else:
                print("  Photo-only mode")

            success = self.robot.execute_path(
                complete_path,
                auto_photo=self.take_photos,
                stabilization_time=config.STABILIZATION_TIME,
            )

            if success:
                print("\n✅ Trajectory completed successfully.")
                print(f"  Session data : {self.session_dirs['main']}")
                print(f"  Viewer       : python web_viewer.py")
            else:
                print("\n❌ Error during trajectory execution.")

            return success

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            return False
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.shutdown()

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def shutdown(self):
        print("\nShutting down targeting system...")
        if hasattr(self, "robot") and self.robot and not self.simulate:
            self.robot.shutdown()
        elif not self.simulate:
            for attr in ("gimbal", "camera", "cnc"):
                obj = getattr(self, attr, None)
                if obj:
                    try:
                        obj.shutdown()
                    except Exception:
                        pass
        self.initialized = False
        print("Targeting system shut down.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def find_latest_pointcloud(directory="results/pointclouds"):
    """
    Retourne le fichier PointCloud_*.ply le plus récent dans le répertoire donné.
    Le format AAAAMMDD-HHMMSS permet un tri alphabétique direct.
    """
    import glob as _glob
    pattern = os.path.join(directory, "PointCloud_*.ply")
    files = sorted(_glob.glob(pattern), reverse=True)
    if not files:
        return None
    latest = files[0]
    print(f"  Auto-detected point cloud: {latest}")
    return latest


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Leaf targeting with eigenvalue + graph-based detection"
    )

    # Optional positional — si absent, le plus récent dans results/pointclouds/ est utilisé
    parser.add_argument("point_cloud", nargs='?', default=None,
        help="Input point cloud file (.ply / .pcd). "
             "If omitted, the latest PointCloud_*.ply in results/pointclouds/ is used.")

    # General
    parser.add_argument("--scale", type=float, default=0.001,
        help="Scale factor applied to point cloud (default 0.001 → mm to m)")
    parser.add_argument("--arduino_port", default=config.ARDUINO_PORT,
        help=f"Arduino serial port (default: {config.ARDUINO_PORT})")
    parser.add_argument("--simulate", action="store_true",
        help="Simulation mode — no robot control")
    parser.add_argument("--no-photo", action="store_true",
        help="Disable automatic photo capture (photos are ON by default)")
    parser.add_argument("--disable-fluorescence", action="store_true",
        help="Disable fluorescence measurements")
    parser.add_argument("--distance", type=float, default=0.1,
        help="Approach distance to leaf for target_point (meters, default 0.1)")

    # ── Detection parameters ─────────────────────────────────────────────────
    det = parser.add_argument_group("Detection parameters")

    det.add_argument("--k_kmeans", type=int, default=3,
        help="KMeans clusters for background separation (default 3)")
    det.add_argument("--k_neighbors", type=int, default=150,
        help="KNN neighbours for adjacency graph (default 150)")
    det.add_argument("--max_distance", type=float, default=0.002,
        help="Max edge distance in adjacency graph, meters (default 0.002 = 2 mm)")
    det.add_argument("--min_cluster_size", type=int, default=1000,
        help="Minimum points per leaf cluster (default 1000)")
    det.add_argument("--angle_threshold", type=float, default=15.0,
        help="Max normal angle (°) to merge parallel clusters (default 15)")
    det.add_argument("--merge_distance", type=float, default=0.015,
        help="Max centroid distance (m) to merge clusters (default 0.015 = 15 mm)")

    return parser.parse_args()


def main():
    args = parse_arguments()
    targeting = LeafTargeting(args)
    return 0 if targeting.run_targeting() else 1


if __name__ == "__main__":
    sys.exit(main())