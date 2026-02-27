#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to execute manual robot control
"""

import os
import sys
import argparse

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from manual_control.manual_controller import ManualController
from core.utils import config

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Manual robot control")
    
    parser.add_argument("--arduino-port", "-a", type=str, default=config.ARDUINO_PORT,
                      help=f"Arduino port (default: {config.ARDUINO_PORT})")
    
    parser.add_argument("--speed", "-s", type=float, default=config.CNC_SPEED,
                      help=f"CNC movement speed in m/s (default: {config.CNC_SPEED})")
    
    return parser.parse_args()

def main():
    """Main function"""
    print("=== Manual Robot Control ===")
    
    # Parse arguments
    args = parse_arguments()
    
    # Create and run manual controller
    controller = ManualController(args)
    success = controller.run_manual_control()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())