#!/usr/bin/env python3
"""
Test ultra-simple: prendre une photo
Usage: python simple_test_photo.py
"""

from camera_controller import CameraController
import time

# Initialiser et connecter la caméra
camera = CameraController()
camera.connect()
camera.set_output_directory("test_photos")

# Prendre une photo
print("📸 Prise de photo...")
photo_path, _ = camera.take_photo("test_simple.jpg")

if photo_path:
    print(f"✅ Photo sauvée: {photo_path}")
else:
    print("❌ Échec de la photo")

# Fermer proprement
camera.shutdown()
