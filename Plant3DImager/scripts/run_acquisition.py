#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to execute circular image acquisition
"""

import os
import sys
import argparse

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from acquisition.circle_acquisition import CircleAcquisition
from core.utils import config

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Circular Image Acquisition")
    
    parser.add_argument("--circles", "-c", type=int, choices=[1, 2], default=1,
                      help=f"Number of circles to photograph (1 or 2, default: 1)")
    
    parser.add_argument("--positions", "-p", type=int, default=config.NUM_POSITIONS, 
                      help=f"Number of positions per circle (default: {config.NUM_POSITIONS})")
    
    parser.add_argument("--radius", "-r", type=float, default=config.CIRCLE_RADIUS,
                      help=f"Circle radius in meters (default: {config.CIRCLE_RADIUS})")
    
    parser.add_argument("--z-offset", "-z", type=float, default=config.Z_OFFSET,
                      help=f"Z offset between the two circles in meters (default: {config.Z_OFFSET})")
    
    parser.add_argument("--arduino-port", "-a", type=str, default=config.ARDUINO_PORT,
                      help=f"Arduino port (default: {config.ARDUINO_PORT})")
    
    parser.add_argument("--speed", "-s", type=float, default=config.CNC_SPEED,
                      help=f"CNC movement speed in m/s (default: {config.CNC_SPEED})")
    
    return parser.parse_args()

def main():
    """Main function"""
    print("=== Circular Image Acquisition ===")
    
    # Parse arguments
    args = parse_arguments()
    
    # Create and run acquisition
    acquisition = CircleAcquisition(args)
    success = acquisition.run_acquisition()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())