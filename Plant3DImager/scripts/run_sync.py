#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to execute server synchronization
"""

import os
import sys
import argparse

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sync.server_sync import ServerSync

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Raspberry Pi - Server Synchronization")
    
    parser.add_argument("--ssh-host", type=str,
                      help="SSH server address")
    
    parser.add_argument("--ssh-user", type=str,
                      help="SSH username")
    
    parser.add_argument("--key-path", type=str,
                      help="Path to SSH key")
    
    parser.add_argument("--remote-path", type=str,
                      help="Remote working directory path")
    
    parser.add_argument("--local-acq", type=str,
                      help="Local acquisition directory")
    
    parser.add_argument("--ply-target", type=str,
                      help="Target directory for PLY files")
    
    parser.add_argument("--dry-run", action="store_true",
                      help="Simulation mode (no actual execution)")
    
    return parser.parse_args()

def main():
    """Main function"""
    print("=== Raspberry Pi - Server Synchronization ===")
    
    # Parse arguments
    args = parse_arguments()
    
    # Create and run synchronization
    sync = ServerSync(args)
    success = sync.run_sync()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())