#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified fluorescence sensor controller for leaf targeting integration
Follows ROMI architecture: inherits from RcomClient like CNC/gimbal controllers
"""

from rcom.rcom_client import RcomClient
import json
import time

class FluoController(RcomClient):
    """
    Simplified interface for Ambit fluorescence sensor
    Inherits from RcomClient like other ROMI hardware controllers (CNC, gimbal)
    
    Usage: 
        fluo = FluoController()
        measurements = fluo.measure_simple()
        status = fluo.get_device_status()
    """
    
    def __init__(self, topic="fluo", id="fluo"):
        """
        Initialize connection to fluorescence sensor using ROMI RCom pattern
        
        Args:
            topic (str): RCom topic name (default "fluo")  
            id (str): RCom service ID (default "fluo")
        """
        # Call parent constructor (standard ROMI pattern)
        super().__init__(topic, id)
        print(f"FluoController connected to service '{topic}' (id: {id})")
    
    def get_device_status(self):
        """
        Get real-time device connection status (from romi_fluo.py)
        
        Returns:
            dict: Status information with 'connected' and 'status' keys
        """
        try:
            result = self.execute("fluo:get-device-status", {})
            if isinstance(result, dict):
                return {
                    "connected": result.get("connected", False),
                    "status": result.get("status", "Unknown status")
                }
            return {"connected": False, "status": "Communication error"}
        except Exception as e:
            print(f"Error getting device status: {e}")
            return {"connected": False, "status": f"Error: {e}"}
    
    def measure_simple(self):
        """
        Perform simple fluorescence measurement using active configuration (from romi_fluo.py)
        
        Returns:
            list: List of measured fluorescence values, or empty list if error
        """
        try:
            print("🔄 Starting fluorescence measurement with default parameters...")
            
            # Use the correct RCom execute method (like in romi_fluo.py)
            result = self.execute("fluo:measure", {})
            
            if isinstance(result, dict):
                measurements = result.get("measurements", [])
                print(f"✅ Fluorescence measurement completed: {len(measurements)} points")
                return measurements
            else:
                print("❌ Error: Invalid response format from sensor")
                return []
                
        except Exception as e:
            print(f"❌ Error during fluorescence measurement: {e}")
            return []


# Simple test function (proof of concept)
if __name__ == "__main__":
    print("=== Fluorescence Sensor Simple Test ===")
    
    try:
        # Connect to sensor (ROMI pattern)
        fluo = FluoController("fluo", "fluo")
        
        # Check device status
        print("Checking device status...")
        status = fluo.get_device_status()
        print(f"  Connected: {status['connected']}")
        print(f"  Status: {status['status']}")
        
        if status['connected']:
            # Perform simple measurement
            print("Taking fluorescence measurement...")
            measurements = fluo.measure_simple()
            if measurements:
                print(f"✅ Measurement successful: {len(measurements)} points")
                print(f"  First value: {measurements[0]:.6f}")
                print(f"  Last value: {measurements[-1]:.6f}")
                print(f"  Average: {sum(measurements)/len(measurements):.6f}")
            else:
                print("❌ No measurements received")
        else:
            print("⚠️  Device not connected, skipping measurement")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    print("Test completed")
