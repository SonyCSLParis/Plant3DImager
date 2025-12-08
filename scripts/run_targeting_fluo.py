#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to run leaf targeting with fluorescence sensor integration
Simple proof of concept implementation
"""

import os
import sys
import argparse

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from targeting.leaf_targeting_with_fluo import LeafTargetingWithFluo, parse_arguments

def main():
    """Main function for fluorescence-enabled targeting"""
    print("=== Leaf Targeting System with Fluorescence Sensor ===")
    print("🧬 This version includes automated fluorescence measurements")
    print("   Protocol: Photo → Rotate 180° → Fluorescence measurement → Rotate back")
    print()
    
    # Parse arguments
    args = parse_arguments()
    
    # Display configuration
    print("Configuration:")
    print(f"  Point cloud: {args.point_cloud}")
    print(f"  Simulation mode: {args.simulate}")
    print(f"  Auto photo: {args.auto_photo}")
    print(f"  Fluorescence: {'Disabled' if args.no_fluorescence else 'Enabled'}")
    print()
    
    # Create and run targeting
    targeting = LeafTargetingWithFluo(args)
    success = targeting.run_targeting()
    
    if success:
        print("\n🎉 Targeting with fluorescence completed successfully!")
    else:
        print("\n❌ Targeting failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
