#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified camera controller for acquisition and targeting modules
FIXED: Added power_up() in connect() method
"""

import os
import time
from datetime import datetime
from romi.camera import Camera

class CameraController:
    def __init__(self):
        """Initialize the camera controller"""
        self.camera = None
        self.photos_dir = None
        self.initialized = False
    
    def connect(self):
        """Connect to the camera and initialize it"""
        if self.initialized:
            return self
        
        try:
            print("Initializing camera...")
            self.camera = Camera("camera", "camera")
            
            # FIX: Power up the camera so grab() will work
            print("Powering up camera...")
            self.camera.power_up()
            
            self.initialized = True
            return self
        except Exception as e:
            print(f"Error initializing camera: {e}")
            raise
    
    def set_output_directory(self, directory):
        """Set the output directory for photos"""
        self.photos_dir = directory
        os.makedirs(directory, exist_ok=True)
        print(f"Photos output directory: {directory}")
    
    def take_photo(self, filename=None, metadata=None):
        """Take a photo with the camera"""
        if not self.initialized:
            raise RuntimeError("Camera not initialized")
        
        try:
            print("Capturing image...")
            image = self.camera.grab()
            
            if image is not None:
                # Generate a filename if not specified
                if filename is None:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = f"photo_{timestamp}.jpg"
                
                # Add the full path
                if self.photos_dir:
                    filepath = os.path.join(self.photos_dir, filename)
                else:
                    filepath = filename
                
                # Save the image
                image.save(filepath)
                print(f"Image saved: {filepath}")
                return filepath, metadata
            else:
                print("Error: Unable to capture image")
                return None, None
                
        except Exception as e:
            print(f"Error taking photo: {e}")
            return None, None
    
    def shutdown(self):
        """Properly shut down the camera"""
        if not self.initialized:
            return True
        
        # FIX: Power down the camera properly
        if self.camera:
            try:
                print("Powering down camera...")
                self.camera.power_down()
            except Exception as e:
                print(f"Warning: Error powering down camera: {e}")
                
        self.initialized = False
        return True