#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Raspberry Pi - Server synchronization module for ROMI
This module automates the transfer of 3D plant acquisition data
and the launch of processing on the server.
"""

import time
import os
import logging
import sys
from pathlib import Path
from sync.ssh_manager import SSHManager, handle_lock_removal
from core.utils import config

class ServerSync:
    def __init__(self, args=None):
        """
        Initialize the synchronization module
        
        Args:
            args: Command line arguments (optional)
        """
        # Logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger("sync")
        
        # Default parameters
        self.ssh_host = config.SSH_HOST if hasattr(config, 'SSH_HOST') else "10.0.7.22"
        self.ssh_user = config.SSH_USER if hasattr(config, 'SSH_USER') else "ayman"
        self.key_path = config.KEY_PATH if hasattr(config, 'KEY_PATH') else "/home/romi/.ssh/id_rsa"
        self.remote_work_path = config.REMOTE_WORK_PATH if hasattr(config, 'REMOTE_WORK_PATH') else "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/"
        self.local_acquisition_base = config.LOCAL_ACQUISITION_BASE if hasattr(config, 'LOCAL_ACQUISITION_BASE') else "/home/romi/ayman/results/plant_acquisition"
        self.local_ply_target = config.LOCAL_PLY_TARGET if hasattr(config, 'LOCAL_PLY_TARGET') else "/home/romi/ayman/PointClouds"
        self.romi_config = config.ROMI_CONFIG if hasattr(config, 'ROMI_CONFIG') else "~/plant-3d-vision/configs/geom_pipe_real.toml"
        self.dry_run = False  # Simulation mode
        
        # Update parameters with command line arguments
        if args:
            self.update_from_args(args)
            
        # SSH Manager
        self.ssh = None
        
        # State
        self.initialized = False
    
    def update_from_args(self, args):
        """Update parameters from command line arguments"""
        if hasattr(args, 'ssh_host') and args.ssh_host:
            self.ssh_host = args.ssh_host
            
        if hasattr(args, 'ssh_user') and args.ssh_user:
            self.ssh_user = args.ssh_user
            
        if hasattr(args, 'key_path') and args.key_path:
            self.key_path = args.key_path
            
        if hasattr(args, 'remote_path') and args.remote_path:
            self.remote_work_path = args.remote_path
            
        if hasattr(args, 'local_acq') and args.local_acq:
            self.local_acquisition_base = args.local_acq
            
        if hasattr(args, 'ply_target') and args.ply_target:
            self.local_ply_target = args.ply_target
            
        if hasattr(args, 'dry_run') and args.dry_run:
            self.dry_run = args.dry_run
    
    def initialize(self):
        """Initialize SSH connection"""
        if self.initialized:
            return True
        
        try:
            self.logger.info("[START] Initializing synchronization")
            
            # Create SSH manager
            self.ssh = SSHManager(
                self.ssh_host, 
                self.ssh_user, 
                self.key_path, 
                dry_run=self.dry_run
            )
            
            # Connect
            if not self.ssh.connect():
                return False
            
            # Check and handle lock
            self.logger.info("[CHECK] Checking database lock...")
            lock_result = self.ssh.check_and_handle_lock()
            if lock_result == "exit_script":
                return False
            elif lock_result == "restart":
                return "restart"
            elif lock_result != "continue":
                self.logger.error("[ERROR] Error checking lock")
                return False
            
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error("[ERROR] Initialization error: %s", str(e))
            return False
    
    def find_latest_acquisition(self):
        """Find the most recent circular_scan_* directory"""
        base_path = self.local_acquisition_base
        pattern = "circular_scan_*"
        
        try:
            base_path = Path(base_path)
            candidates = list(base_path.glob(pattern))
            
            if not candidates:
                self.logger.error("[ERROR] No '%s' directory found in %s", pattern, base_path)
                return None, None
                
            # Sort by modification date
            latest = max(candidates, key=os.path.getmtime)
            
            # Extract timestamp from name
            timestamp = latest.name.replace("circular_scan_", "")
            
            self.logger.info("[FOUND] Latest acquisition found: %s", latest.name)
            return latest, timestamp
            
        except Exception as e:
            self.logger.error("[ERROR] Error during search: %s", str(e))
            return None, None
    
    def run_sync(self):
        """Execute the complete synchronization process"""
        restart_sync = True
        
        while restart_sync:
            restart_sync = False  # Reset flag to avoid infinite loop
            
            init_result = self.initialize()
            if init_result == "restart":
                restart_sync = True
                continue
            elif not init_result:
                return False
            
            try:
                # 1. Run Clean
                self.logger.info("[CLEANING] Step 1/6: Initial cleaning (Clean)")
                clean_args = f"Clean {self.remote_work_path} --config {self.romi_config}"
                result = self.ssh.exec_romi_command(clean_args)
                
                if result == "lock_detected":
                    self.logger.warning("[LOCK] Database lock detected during Clean")
                    lock_result = handle_lock_removal(self.ssh)
                    if lock_result == "exit_script":
                        return False
                    elif lock_result == "restart":
                        restart_sync = True
                        self.ssh.close()
                        self.initialized = False
                        continue  # Restart the loop
                elif not result:
                    self.logger.error("[ERROR] Clean task failed")
                    return False
                
                # 2. Delete old files from server
                self.logger.info("[DELETION] Step 2/6: Deleting old files")
                items_to_remove = ["images", "metadata", "files.json", "scan.toml"]
                for item in items_to_remove:
                    cmd = f"rm -rf '{self.remote_work_path}{item}'"
                    success, _ = self.ssh.exec_command(cmd)
                    if not success:
                        self.logger.warning("[WARNING] Unable to delete %s (may be absent)", item)
                
                # 3. Find latest local acquisition
                self.logger.info("[SEARCH] Step 3/6: Finding latest acquisition")
                latest_dir, timestamp = self.find_latest_acquisition()
                if not latest_dir:
                    return False
                
                # 4. Copy new files to server
                self.logger.info("[UPLOAD] Step 4/6: Uploading new data")
                items_to_copy = ["images", "metadata", "files.json", "scan.toml"]
                
                for item in items_to_copy:
                    src_path = latest_dir / item
                    dst_path = f"{self.remote_work_path}{item}"
                    
                    if not src_path.exists():
                        self.logger.warning("[WARNING] Missing item (skipped): %s", src_path)
                        continue
                    
                    self.logger.info("[UPLOAD] Copying: %s", item)
                    if not self.ssh.upload_path(src_path, dst_path):
                        self.logger.error("[ERROR] Failed to copy %s", item)
                        return False
                
                # 5. Run PointCloud
                self.logger.info("[PROCESSING] Step 5/6: Generating point cloud (PointCloud)")
                pointcloud_args = f"PointCloud {self.remote_work_path} --config {self.romi_config}"
                result = self.ssh.exec_romi_command(pointcloud_args)
                
                if result == "lock_detected":
                    self.logger.warning("[LOCK] Database lock detected during PointCloud")
                    lock_result = handle_lock_removal(self.ssh)
                    if lock_result == "exit_script":
                        return False
                    elif lock_result == "restart":
                        restart_sync = True
                        self.ssh.close()
                        self.initialized = False
                        continue  # Restart the loop
                elif not result:
                    self.logger.error("[ERROR] PointCloud task failed")
                    return False
                
                # 6. Retrieve PLY file
                self.logger.info("[DOWNLOAD] Step 6/6: Retrieving point cloud")
                
                # Find PointCloud* directory
                find_cmd = f"find '{self.remote_work_path}' -name 'PointCloud*' -type d | head -1"
                success, pointcloud_dir = self.ssh.exec_command(find_cmd)
                
                if not success or not pointcloud_dir:
                    self.logger.error("[ERROR] Unable to find PointCloud directory")
                    return False
                
                # Download PLY file
                remote_ply = f"{pointcloud_dir.strip()}/PointCloud.ply"
                local_ply = f"{self.local_ply_target}/PointCloud_{timestamp}.ply"
                
                if not self.ssh.download_file(remote_ply, local_ply):
                    self.logger.error("[ERROR] Failed to download PLY")
                    return False
                
                self.logger.info("[SUCCESS] PLY file retrieved: %s", local_ply)
                
                # 7. Clean closure
                self.ssh.close()
                self.logger.info("[FINISHED] Synchronization completed successfully")
                return True
                
            except KeyboardInterrupt:
                self.logger.info("[STOP] User interruption")
                return False
            except Exception as e:
                self.logger.error("[ERROR] Unexpected error: %s", str(e), exc_info=True)
                return False
            finally:
                if not restart_sync and self.ssh:  # Only close if not restarting
                    self.ssh.close()
    
    def shutdown(self):
        """Properly close connection"""
        if self.ssh:
            self.ssh.close()
        self.initialized = False
        self.logger.info("[FINISHED] Synchronization module shut down")