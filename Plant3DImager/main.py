#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the robotic photography and targeting system
"""

import os
import sys
import argparse
import subprocess

def main():
    """Main function"""
    print("=== Robotic Photography and Targeting System ===")
    
    # Create main parser
    parser = argparse.ArgumentParser(description="Robotic photography and targeting system")
    
    # Add mode argument
    parser.add_argument("--mode", choices=["acquisition", "targeting", "manual", "sync", "workflow"], required=True,
                      help="Execution mode: image acquisition, leaf targeting, manual control, server synchronization, or complete workflow")
    
    # Parse only the mode argument
    args, remaining_args = parser.parse_known_args()
    
    # Build script path
    script_paths = {
        "acquisition": os.path.join("scripts", "run_acquisition.py"),
        "targeting": os.path.join("scripts", "run_targeting.py"),
        "manual": os.path.join("scripts", "run_manual.py"),
        "sync": os.path.join("scripts", "run_sync.py"),
        "workflow": os.path.join("scripts", "run_workflow.py")
    }
    
    script_path = script_paths[args.mode]
    
    # Check if script exists
    if not os.path.exists(script_path):
        print(f"Error: Script {script_path} does not exist.")
        return 1
    
    # Build command with all remaining arguments
    cmd = [sys.executable, script_path] + remaining_args
    print(f"Executing: {' '.join(cmd)}")
    
    # Use subprocess for better argument handling
    return subprocess.call(cmd)

if __name__ == "__main__":
    sys.exit(main())