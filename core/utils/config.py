#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON configuration loading module shared between acquisition and targeting modules
"""

import json
import os
import sys

# Path to configuration file - at project root
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.json')

# Global variables to store configuration
_config_data = {}
_config_loaded = False

# Default values
_defaults = {
    "TARGET_POINT": [0.375, 0.35, 0.30],
    "CENTER_POINT": [0.375, 0.35, 0.00],
    "CIRCLE_RADIUS": 0.30,
    "NUM_POSITIONS": 80,
    "Z_OFFSET": 0.20,
    "ARDUINO_PORT": "/dev/ttyACM0",
    "CNC_SPEED": 0.1,
    "UPDATE_INTERVAL": 0.1,
    "STABILIZATION_TIME": 3.0,
    "RESULTS_DIR": "results",
    "ACQUISITION_DIR": "plant_acquisition",
    "TARGETING_DIR": "leaf_targeting",
    "ENABLE_FLUORESCENCE": True,
    "SSH_HOST": "10.0.7.22",
    "SSH_USER": "ayman",
    "KEY_PATH": "/home/romi/.ssh/id_rsa",
    "REMOTE_WORK_PATH": "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/",
    "LOCAL_ACQUISITION_BASE": "results/plant_acquisition",
    "LOCAL_PLY_TARGET": "results/pointclouds",
    "ROMI_CONFIG": "~/plant-3d-vision/configs/geom_pipe_real.toml"
}

def _load_config():
    """
    Load configuration from JSON file
    """
    global _config_data, _config_loaded
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            _config_data = json.load(f)
        _config_loaded = True
        print(f"Configuration loaded from {CONFIG_FILE}")
    except FileNotFoundError:
        print(f"Configuration file not found: {CONFIG_FILE}")
        print("Creating file with default values...")
        _config_data = _defaults.copy()
        save_config(_config_data)
        _config_loaded = True
    except json.JSONDecodeError as e:
        print(f"Format error in configuration file: {e}")
        print("Using default values")
        _config_data = _defaults.copy()
        _config_loaded = False

def get(key, default=None):
    """
    Returns the configuration value for the specified key
    
    Args:
        key: Configuration key
        default: Default value if key doesn't exist
    
    Returns:
        Configuration value
    """
    if not _config_loaded:
        _load_config()
    
    # Use provided default value or the one from _defaults
    if default is None and key in _defaults:
        default = _defaults[key]
        
    value = _config_data.get(key, default)
    
    # Convert lists to tuples for certain keys
    if key in ["TARGET_POINT", "CENTER_POINT"] and isinstance(value, list):
        value = tuple(value)
        
    return value

def save_config(config_dict):
    """
    Save configuration changes to JSON file
    
    Args:
        config_dict: Dictionary containing new configuration values
    
    Returns:
        True if save is successful, False otherwise
    """
    global _config_data
    
    try:
        if not _config_loaded:
            _load_config()
        
        # Update configuration with new values
        _config_data.update(config_dict)
        
        # Save updated configuration
        with open(CONFIG_FILE, 'w') as f:
            json.dump(_config_data, f, indent=4)
            
        print(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

# Load configuration at startup
_load_config()

# Expose configuration variables as module attributes
TARGET_POINT = get("TARGET_POINT")
CENTER_POINT = get("CENTER_POINT")
CIRCLE_RADIUS = get("CIRCLE_RADIUS")
NUM_POSITIONS = get("NUM_POSITIONS")
Z_OFFSET = get("Z_OFFSET")
ARDUINO_PORT = get("ARDUINO_PORT")
CNC_SPEED = get("CNC_SPEED")
UPDATE_INTERVAL = get("UPDATE_INTERVAL")
STABILIZATION_TIME = get("STABILIZATION_TIME")
RESULTS_DIR = get("RESULTS_DIR")
ACQUISITION_DIR = get("ACQUISITION_DIR")
TARGETING_DIR = get("TARGETING_DIR")
ENABLE_FLUORESCENCE = get("ENABLE_FLUORESCENCE")
SSH_HOST = get("SSH_HOST")
SSH_USER = get("SSH_USER")
KEY_PATH = get("KEY_PATH")
REMOTE_WORK_PATH = get("REMOTE_WORK_PATH")
LOCAL_ACQUISITION_BASE = get("LOCAL_ACQUISITION_BASE")
LOCAL_PLY_TARGET = get("LOCAL_PLY_TARGET")
ROMI_CONFIG = get("ROMI_CONFIG")