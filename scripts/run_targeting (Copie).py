#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to execute leaf targeting with integrated fluorescence sensor
Unified version that replaces both run_targeting.py and run_targeting_fluo.py
"""

import os
import sys
import argparse

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import unified LeafTargeting class
from targeting.leaf_targeting import LeafTargeting
from core.utils import config

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
    
    # NEW: Inverted photo logic - photos are enabled by default
    parser.add_argument('--no-photo', action='store_true', 
                       help='Disable automatic photo capture (default: photos enabled)')
    
    parser.add_argument('--louvain_coeff', type=float, default=0.5, help='Coefficient for Louvain detection (default: 0.5)')
    parser.add_argument('--distance', type=float, default=0.1, help='Distance to target leaves in meters (default: 0.1 m)')
    
    # NEW: Fluorescence disable option
    parser.add_argument('--disable-fluorescence', action='store_true', 
                       help='Disable fluorescence measurements (photo only)')
    
    return parser.parse_args()

def main():
    """Main function for unified targeting with fluorescence integration"""
    print("=== Leaf Targeting System ===")
    
    # Check fluorescence availability
    fluorescence_enabled = config.ENABLE_FLUORESCENCE
    if fluorescence_enabled:
        print("🧬 Fluorescence sensor integration enabled")
    else:
        print("📷 Photo-only mode (fluorescence disabled in config)")
    
    print()
    
    # Parse arguments
    args = parse_arguments()
    
    # Display configuration
    print("Configuration:")
    print(f"  Point cloud: {args.point_cloud}")
    print(f"  Simulation mode: {args.simulate}")
    print(f"  Auto photo: {'Disabled' if args.no_photo else 'Enabled'}")
    
    if args.disable_fluorescence:
        print(f"  Fluorescence: Disabled (--disable-fluorescence)")
    elif fluorescence_enabled:
        print(f"  Fluorescence: Enabled")
    else:
        print(f"  Fluorescence: Disabled (config)")
    
    print()
    
    # Create and run targeting
    targeting = LeafTargeting(args)
    success = targeting.run_targeting()
    
    if success:
        print("\n🎉 Targeting completed successfully!")
        
        # Display what was accomplished
        if not args.simulate:
            if not args.no_photo:
                print("📸 Photos captured and saved")
            if fluorescence_enabled and not args.disable_fluorescence:
                print("🧬 Fluorescence measurements recorded")
    else:
        print("\n❌ Targeting failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())