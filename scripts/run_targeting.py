#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to execute leaf targeting
"""

import os
import sys
import argparse

# Add parent directory to Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import refactored LeafTargeting class
from targeting.leaf_targeting import LeafTargeting, parse_arguments

def main():
    """Main function"""
    print("=== Leaf Targeting System ===")
    
    # Parse arguments
    args = parse_arguments()
    
    # Create and run targeting
    targeting = LeafTargeting(args)
    success = targeting.run_targeting()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())