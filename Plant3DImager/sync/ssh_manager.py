#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSH connection manager with improved error handling
"""

import paramiko
import os
import time
import logging
from pathlib import Path

class SSHManager:
    """SSH connection manager with improved error handling"""
    
    def __init__(self, host, username, key_path, dry_run=False):
        self.host = host
        self.username = username
        self.key_path = key_path
        self.dry_run = dry_run
        self.ssh = None
        self.sftp = None
        self.logger = logging.getLogger("sync.ssh")
        
    def connect(self):
        """Establish SSH and SFTP connection"""
        if self.dry_run:
            self.logger.info("[DRY RUN] Simulated SSH connection to %s@%s", self.username, self.host)
            return True
            
        try:
            self.logger.info("Connecting to %s@%s...", self.username, self.host)
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.host, 
                username=self.username, 
                key_filename=self.key_path,
                timeout=300
            )
            
            # Check that connection works
            _, stdout, _ = self.ssh.exec_command("echo 'SSH connection test'")
            result = stdout.read().decode().strip()
            if not result:
                self.logger.error("SSH connection test failed")
                return False
                
            self.sftp = self.ssh.open_sftp()
            self.logger.info("[CONNECTION] SSH/SFTP connection established successfully")
            return True
        except Exception as e:
            self.logger.error("[ERROR] SSH connection error: %s", str(e))
            return False
    
    def exec_romi_command(self, command_args):
        """
        Execute a romi_run_task command with correct environment
        
        Args:
            command_args: Arguments for romi_run_task (e.g. "Clean /path/to/scan --config /path/to/config")
        
        Returns:
            True if successful, False otherwise, "lock_detected" if lock detected
        """
        if self.dry_run:
            self.logger.info("[SIMULATION] romi_run_task %s", command_args)
            return True
            
        if not self.ssh:
            self.logger.error("[ERROR] No active SSH connection")
            return False
            
        try:
            self.logger.info("[EXECUTION] romi_run_task %s", command_args)
            
            # Create channel with PTY for full environment
            channel = self.ssh.get_transport().open_session()
            channel.get_pty()
            
            # Command with correct environment (based on our previous tests)
            # MODIFICATION: Added export CUDA_VISIBLE_DEVICES=0 to restrict to first GPU
            full_command = (
                "bash -l -c '"
                "export PYTHONPATH=/home/ayman/plant-3d-vision && "
                "export CUDA_VISIBLE_DEVICES=0 && "  # Added this line to select only first GPU
                "unset ROMI_DB && "
                "cd /home/ayman/plant-3d-vision && "
                f"/home/ayman/.local/bin/romi_run_task {command_args}"
                "'"
            )
            
            channel.exec_command(full_command)
            
            # Display output in real time and capture to detect lock
            output_lines = []
            stderr_lines = []
            
            while True:
                if channel.recv_ready():
                    data = channel.recv(1024).decode('utf-8')
                    print(data, end='')
                    output_lines.append(data)
                    
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(1024).decode('utf-8')
                    print(f"STDERR: {data}", end='')
                    stderr_lines.append(data)
                    
                if channel.exit_status_ready():
                    break
                    
                time.sleep(0.1)  # Small pause to avoid CPU overload
            
            # After end, read anything remaining
            time.sleep(0.5)  # Wait a bit longer to be sure
            while channel.recv_ready():
                data = channel.recv(1024).decode('utf-8')
                output_lines.append(data)
                print(data, end='')
            while channel.recv_stderr_ready():
                data = channel.recv_stderr(1024).decode('utf-8')
                stderr_lines.append(data)
                print(f"STDERR: {data}", end='')
            
            exit_status = channel.recv_exit_status()
            channel.close()
            
            # Check if there's a lock error in all output
            full_output = "".join(output_lines + stderr_lines)
            
            # Debug: display what we captured (in debug mode only)
            if exit_status != 0:
                self.logger.debug("Captured output for analysis: %s", full_output[:500] + "..." if len(full_output) > 500 else full_output)
            
            # Detect different lock error patterns
            lock_patterns = [
                "DBBusyError",
                "File lock exists", 
                "DB is busy, cannot connect",
                "File exists: '/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/lock'",
                "FileExistsError: [Errno 17] File exists:",
                "/lock'"  # Simpler pattern for lock file path
            ]
            
            for pattern in lock_patterns:
                if pattern in full_output:
                    self.logger.warning("[LOCK] Lock pattern detected: %s", pattern)
                    return "lock_detected"
            
            if exit_status == 0:
                self.logger.info("[SUCCESS] romi_run_task command succeeded")
                return True
            else:
                self.logger.error("[ERROR] romi_run_task command failed with code %d", exit_status)
                return False
                
        except Exception as e:
            self.logger.error("[ERROR] Error executing ROMI command: %s", str(e))
            return False
    
    def exec_command(self, command):
        """Execute a simple system command"""
        if self.dry_run:
            self.logger.info("[SIMULATION] %s", command)
            return True, "[SIMULATION] Simulated output"
            
        if not self.ssh:
            self.logger.error("[ERROR] No active SSH connection")
            return False, "No SSH connection"
            
        try:
            self.logger.info("[COMMAND] %s", command)
            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=300)
            
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                return True, output
            else:
                self.logger.error("[ERROR] Command failed (code %d): %s", exit_status, errors)
                return False, errors
                
        except Exception as e:
            self.logger.error("[ERROR] Error: %s", str(e))
            return False, str(e)
    
    def upload_path(self, local_path, remote_path):
        """Recursive upload of a file or directory"""
        if self.dry_run:
            self.logger.info("[SIMULATION] Upload %s → %s", local_path, remote_path)
            return True
            
        if not self.sftp:
            self.logger.error("[ERROR] No active SFTP connection")
            return False
            
        try:
            local_path = Path(local_path)
            
            if local_path.is_file():
                # Simple file upload
                self.logger.info("[UPLOAD] File: %s → %s", local_path.name, remote_path)
                self.sftp.put(str(local_path), remote_path)
                return True
                
            elif local_path.is_dir():
                # Recursive directory upload
                self.logger.info("[UPLOAD] Directory: %s → %s", local_path.name, remote_path)
                
                # Create remote directory
                self.exec_command(f"mkdir -p '{remote_path}'")
                
                # Traverse and upload all files
                for item in local_path.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(local_path)
                        remote_item = f"{remote_path}/{rel_path}".replace('\\', '/')
                        remote_dir = os.path.dirname(remote_item)
                        
                        # Create parent directory if needed
                        self.exec_command(f"mkdir -p '{remote_dir}'")
                        
                        # Upload file
                        try:
                            self.sftp.put(str(item), remote_item)
                        except Exception as e:
                            self.logger.error("[ERROR] Upload error %s: %s", item, str(e))
                            return False
                            
                return True
            else:
                self.logger.error("[ERROR] Local path not found: %s", local_path)
                return False
                
        except Exception as e:
            self.logger.error("[ERROR] Error during upload: %s", str(e))
            return False
    
    def download_file(self, remote_path, local_path):
        """Download a file from the server"""
        if self.dry_run:
            self.logger.info("[SIMULATION] Download %s → %s", remote_path, local_path)
            return True
            
        if not self.sftp:
            self.logger.error("[ERROR] No active SFTP connection")
            return False
            
        try:
            # Create local parent directory
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            self.logger.info("[DOWNLOAD] %s → %s", remote_path, local_path)
            self.sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            self.logger.error("[ERROR] Download error: %s", str(e))
            return False
    
    def check_and_handle_lock(self):
        """Check if there's a lock and offer to remove it"""
        if self.dry_run:
            return "continue"
            
        # Check for lock file existence
        lock_file = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/lock"
        check_cmd = f"test -f '{lock_file}'"
        success, _ = self.exec_command(check_cmd)
        
        if success:  # File exists (test -f returns 0 if file exists)
            self.logger.warning("[LOCK] Lock file detected: %s", lock_file)
            return handle_lock_removal(self)  # Returns "exit_script" or other
        else:
            # No lock, continue
            return "continue"
    
    def close(self):
        """Close connections"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        self.logger.info("[CLOSED] Connections closed")


def handle_lock_removal(ssh_manager):
    """Handle lock removal with user confirmation"""
    print("\n" + "="*80)
    print("WARNING - DATABASE LOCK DETECTED")
    print("="*80)
    print("The presence of a lock may indicate:")
    print("  • A ROMI task is currently running")
    print("  • A previous task ended abnormally")
    print("  • The system was abruptly interrupted")
    print("\nWARNING: Removing the lock while a task is running can corrupt data!")
    print("="*80)
    
    while True:
        try:
            response = input("\nDo you want to remove the lock? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                # Remove lock
                lock_file = "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/lock"
                unlock_cmd = f"rm -f '{lock_file}'"
                success, _ = ssh_manager.exec_command(unlock_cmd)
                
                if success:
                    print("\n[SUCCESS] Lock successfully removed")
                    
                    # Ask if user wants to restart automatically
                    restart_response = input("\nDo you want to restart the synchronization automatically? (yes/no): ").strip().lower()
                    if restart_response in ['yes', 'y']:
                        print("\n[INFO] Restarting synchronization...")
                        return "restart"
                    else:
                        print("\n[INFO] Exiting. You can restart the script manually with:")
                        print("       Command: python scripts/run_sync.py")
                        return "exit_script"
                else:
                    print("\n[ERROR] Unable to remove lock")
                    print("         Check permissions or contact administrator.")
                    return "exit_script"
                
            elif response in ['no', 'n']:
                print("\n[STOP] Operation cancelled. Lock not removed.")
                print("        Synchronization cannot continue while the lock exists.")
                return "exit_script"
            else:
                print("[ERROR] Unrecognized response. Please type 'yes' or 'no'")
                
        except KeyboardInterrupt:
            print("\n\n[STOP] Operation cancelled by user")
            return "exit_script"