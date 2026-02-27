#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to execute complete workflow of acquisition, synchronization and targeting
"""

import os
import sys
import argparse
import time
import logging
from datetime import datetime

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import required modules
from acquisition.circle_acquisition import CircleAcquisition
from sync.server_sync import ServerSync
from targeting.leaf_targeting import LeafTargeting
from core.utils import config

class WorkflowManager:
    def __init__(self, args):
        """
        Initialize workflow manager
        
        Args:
            args: Command line arguments
        """
        # Logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger("workflow")
        
        # Store arguments
        self.args = args
        
        # Results of each step
        self.acquisition_result = None
        self.sync_result = None
        self.targeting_result = None
        
        # Data paths
        self.latest_acquisition_dir = None
        self.latest_ply_path = None
        
        # Workflow tracking states
        self.acquisition_completed = False
        self.sync_completed = False
        self.targeting_completed = False
    
    def run_acquisition(self):
        """Execute image acquisition step"""
        self.logger.info("=== STEP 1: IMAGE ACQUISITION ===")
        
        # Check if we should skip this step
        if self.args.skip_acquisition:
            self.logger.info("Acquisition step skipped (--skip-acquisition)")
            self.acquisition_completed = True
            return True
        
        try:
            # Create and initialize acquisition
            acquisition = CircleAcquisition(self.args)
            
            # Run acquisition
            self.logger.info("Starting image acquisition...")
            self.acquisition_result = acquisition.run_acquisition()
            
            if not self.acquisition_result:
                self.logger.error("Acquisition failed")
                return False
            
            self.logger.info("Image acquisition completed successfully")
            self.acquisition_completed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error during acquisition: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_sync(self):
        """Execute server synchronization step"""
        self.logger.info("\n=== STEP 2: SERVER SYNCHRONIZATION ===")
        
        # Check if we should skip this step
        if self.args.skip_sync:
            self.logger.info("Synchronization step skipped (--skip-sync)")
            
            # If we skip sync, we still need to set PLY path
            if self.args.point_cloud:
                self.latest_ply_path = self.args.point_cloud
                self.logger.info(f"Using specified point cloud: {self.latest_ply_path}")
                self.sync_completed = True
                return True
            else:
                self.logger.error("No point cloud specified with --point-cloud while --skip-sync is enabled")
                return False
        
        try:
            # Create and initialize synchronization
            sync = ServerSync(self.args)
            
            # Run synchronization
            self.logger.info("Starting synchronization...")
            self.sync_result = sync.run_sync()
            
            if not self.sync_result:
                self.logger.error("Synchronization failed")
                return False
            
            # Get latest PLY path
            self.latest_ply_path = self._find_latest_ply()
            
            if not self.latest_ply_path:
                self.logger.error("Unable to find generated point cloud")
                return False
            
            self.logger.info(f"Point cloud found: {self.latest_ply_path}")
            self.sync_completed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error during synchronization: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_targeting(self):
        """Execute leaf targeting step"""
        self.logger.info("\n=== STEP 3: LEAF TARGETING ===")
        
        # Check if we should skip this step
        if self.args.skip_targeting:
            self.logger.info("Targeting step skipped (--skip-targeting)")
            self.targeting_completed = True
            return True
        
        # Check that we have a PLY file
        if not self.latest_ply_path:
            if self.args.point_cloud:
                self.latest_ply_path = self.args.point_cloud
                self.logger.info(f"Using specified point cloud: {self.latest_ply_path}")
            else:
                self.logger.error("No point cloud available for targeting")
                return False
        
        try:
            # Create argument dictionary for targeting
            targeting_args = argparse.Namespace(
                point_cloud=self.latest_ply_path,
                scale=self.args.scale,
                alpha=self.args.alpha,
                crop_method=self.args.crop_method,
                crop_percentage=self.args.crop_percentage,
                z_offset=self.args.z_offset,
                arduino_port=self.args.arduino_port,
                simulate=self.args.simulate,
                auto_photo=self.args.auto_photo,
                louvain_coeff=self.args.louvain_coeff,
                distance=self.args.distance
            )
            
            # Create and initialize targeting
            targeting = LeafTargeting(targeting_args)
            
            # Run targeting
            self.logger.info("Starting leaf targeting...")
            self.targeting_result = targeting.run_targeting()
            
            if not self.targeting_result:
                self.logger.error("Targeting failed")
                return False
            
            self.logger.info("Leaf targeting completed successfully")
            self.targeting_completed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error during targeting: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _find_latest_ply(self):
        """Find latest PLY file in point clouds directory"""
        ply_dir = config.LOCAL_PLY_TARGET
        
        if not os.path.exists(ply_dir):
            self.logger.error(f"Point clouds directory not found: {ply_dir}")
            return None
        
        # Find all PLY files
        ply_files = [f for f in os.listdir(ply_dir) if f.lower().endswith('.ply')]
        
        if not ply_files:
            self.logger.error(f"No PLY files found in {ply_dir}")
            return None
        
        # Sort by modification date (newest first)
        ply_files.sort(key=lambda f: os.path.getmtime(os.path.join(ply_dir, f)), reverse=True)
        
        # Return full path of most recent file
        latest_ply = os.path.join(ply_dir, ply_files[0])
        return latest_ply
    
    def run_workflow(self):
        """Execute complete workflow"""
        start_time = time.time()
        self.logger.info("=== STARTING COMPLETE WORKFLOW ===")
        
        # Step 1: Acquisition
        if not self.run_acquisition():
            self.logger.error("Workflow interrupted at acquisition step")
            return False
        
        # Step 2: Synchronization
        if not self.run_sync():
            self.logger.error("Workflow interrupted at synchronization step")
            return False
        
        # Step 3: Targeting
        if not self.run_targeting():
            self.logger.error("Workflow interrupted at targeting step")
            return False
        
        # Complete workflow finished
        elapsed_time = time.time() - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        self.logger.info("\n=== COMPLETE WORKFLOW FINISHED SUCCESSFULLY ===")
        self.logger.info(f"Total time: {int(hours):02}h {int(minutes):02}m {int(seconds):02}s")
        
        return True

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Complete workflow for acquisition, synchronization and targeting")
    
    # General workflow options
    workflow_group = parser.add_argument_group('Workflow options')
    workflow_group.add_argument("--skip-acquisition", action="store_true", 
                             help="Skip acquisition step")
    workflow_group.add_argument("--skip-sync", action="store_true", 
                             help="Skip synchronization step")
    workflow_group.add_argument("--skip-targeting", action="store_true", 
                             help="Skip targeting step")
    workflow_group.add_argument("--point-cloud", type=str, 
                             help="Path to existing point cloud (if --skip-sync)")
    
    # Acquisition options
    acq_group = parser.add_argument_group('Acquisition options')
    acq_group.add_argument("--circles", "-c", type=int, choices=[1, 2], default=1,
                      help=f"Number of circles to photograph (1 or 2, default: 1)")
    
    acq_group.add_argument("--positions", "-p", type=int, default=config.NUM_POSITIONS, 
                      help=f"Number of positions per circle (default: {config.NUM_POSITIONS})")
    
    acq_group.add_argument("--radius", "-r", type=float, default=config.CIRCLE_RADIUS,
                      help=f"Circle radius in meters (default: {config.CIRCLE_RADIUS})")
    
    acq_group.add_argument("--z-offset", "-z", type=float, default=config.Z_OFFSET,
                      help=f"Z offset between two circles in meters (default: {config.Z_OFFSET})")
    
    # Targeting options
    target_group = parser.add_argument_group('Targeting options')
    target_group.add_argument("--scale", type=float, default=0.001, 
                         help="Scale factor for point cloud (default: 0.001 = mm->m)")
    
    target_group.add_argument("--alpha", type=float, default=0.1, 
                         help="Alpha value for Alpha Shape (default: 0.1)")
    
    target_group.add_argument("--crop_method", choices=['none', 'top_percentage', 'single_furthest'], 
                         default='none', help="Cropping method (default: none)")
    
    target_group.add_argument("--crop_percentage", type=float, default=0.25, 
                         help="Percentage for top_percentage (default: 0.25)")
    
    target_group.add_argument("--louvain_coeff", type=float, default=0.5, 
                         help="Coefficient for Louvain detection (default: 0.5)")
    
    target_group.add_argument("--distance", type=float, default=0.4, 
                         help="Distance to target leaves in meters (default: 0.4 m)")
    
    target_group.add_argument("--simulate", action="store_true", 
                         help="Simulation mode (no robot control)")
    
    target_group.add_argument("--auto_photo", action="store_true", 
                         help="Take photos automatically at each target")
    
    # Hardware options
    hw_group = parser.add_argument_group('Hardware options')
    hw_group.add_argument("--arduino-port", "-a", type=str, default=config.ARDUINO_PORT,
                      help=f"Arduino port (default: {config.ARDUINO_PORT})")
    
    hw_group.add_argument("--speed", "-s", type=float, default=config.CNC_SPEED,
                      help=f"CNC movement speed in m/s (default: {config.CNC_SPEED})")
    
    # Synchronization options
    sync_group = parser.add_argument_group('Synchronization options')
    sync_group.add_argument("--ssh-host", type=str, default=config.SSH_HOST,
                       help=f"SSH server address (default: {config.SSH_HOST})")
    
    sync_group.add_argument("--ssh-user", type=str, default=config.SSH_USER,
                       help=f"SSH username (default: {config.SSH_USER})")
    
    sync_group.add_argument("--key-path", type=str, default=config.KEY_PATH,
                       help=f"Path to SSH key (default: {config.KEY_PATH})")
    
    sync_group.add_argument("--remote-path", type=str, default=config.REMOTE_WORK_PATH,
                       help=f"Remote working directory path (default: {config.REMOTE_WORK_PATH})")
    
    sync_group.add_argument("--local-acq", type=str, default=config.LOCAL_ACQUISITION_BASE,
                       help=f"Local acquisition directory (default: {config.LOCAL_ACQUISITION_BASE})")
    
    sync_group.add_argument("--ply-target", type=str, default=config.LOCAL_PLY_TARGET,
                       help=f"Target directory for PLY files (default: {config.LOCAL_PLY_TARGET})")
    
    sync_group.add_argument("--dry-run", action="store_true",
                       help="Simulation mode for synchronization (no actual execution)")
    
    return parser.parse_args()

def main():
    """Main function"""
    print("=== Complete Workflow: Acquisition, Synchronization and Targeting ===")
    
    # Parse arguments
    args = parse_arguments()
    
    # Create and run workflow
    workflow = WorkflowManager(args)
    success = workflow.run_workflow()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())