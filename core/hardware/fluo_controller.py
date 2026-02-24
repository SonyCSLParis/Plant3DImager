#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fluorescence sensor controller for leaf targeting integration
Follows ROMI architecture: inherits from RcomClient like CNC/gimbal controllers
Integrates sequence-based measurements with timing constraints
"""

from rcom.rcom_client import RcomClient
import json
import time
from datetime import datetime

# Contraintes fluorescence (issues de fluo_controller_generique)
FLUO_FREQUENCY_MAX = 5  # Hz maximum
FLUO_SEGMENTS_MAX = 16  # segments maximum
FLUO_POINTS_MAX = 1999  # points totaux maximum

# Paramètres par défaut pour mesures de ciblage
FLUO_INTENSITY = 140  # Intensité LED pour mesures sur feuilles

class FluoController(RcomClient):
    """
    Interface fluorescence avec séquences temporelles contrôlées
    Hérite de RcomClient selon architecture ROMI (CNC, gimbal)
    
    Usage: 
        fluo = FluoController()
        result = fluo.measure_simple()  # Mesure avec intensité par défaut
        status = fluo.get_device_status()
    """
    
    def __init__(self, topic="fluo", id="fluo"):
        """
        Initialize connection to fluorescence sensor using ROMI RCom pattern
        
        Args:
            topic (str): RCom topic name (default "fluo")  
            id (str): RCom service ID (default "fluo")
        """
        super().__init__(topic, id)
        print(f"FluoController connected to service '{topic}' (id: {id})")
        print(f"Constraints: {FLUO_FREQUENCY_MAX}Hz max, {FLUO_SEGMENTS_MAX} segments max, {FLUO_POINTS_MAX} points max")
    
    def get_device_status(self):
        """
        Get real-time device connection status
        
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
    
    def create_measurement_sequence(self, pulse_intensity=None):
        """
        Create standardized measurement sequence for leaf targeting
        Sequence: 5s dark → 1min pulse at intensity → 1min dark at intensity 1
        
        Args:
            pulse_intensity (int): LED intensity 0-255 (default: FLUO_INTENSITY=140)
            
        Returns:
            list: Sequence compatible with fluo:execute-sequence
        """
        if pulse_intensity is None:
            pulse_intensity = FLUO_INTENSITY
            
        sequence = [
            {
                "num_points": 25,          # 5s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX, 
                "actinic": 1               # Phase noire initiale
            },
            {
                "num_points": 300,         # 60s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX, 
                "actinic": pulse_intensity # Phase lumineuse
            },
            {
                "num_points": 300,         # 60s à 5Hz  
                "frequency": FLUO_FREQUENCY_MAX,
                "actinic": 1               # Phase noire finale
            }
        ]
        
        return sequence
    
    def measure_simple(self, pulse_intensity=None):
        """
        Perform leaf targeting fluorescence measurement with standard protocol
        Protocol: 25 points dark (5s) + 300 points pulse (60s) + 300 points dark (60s) at 5Hz
        
        Args:
            pulse_intensity (int): LED intensity 0-255 (default: FLUO_INTENSITY=140)
            
        Returns:
            dict: Complete measurement result with:
                - measurements: list of fluorescence values
                - timestamps: timing for each point (seconds)
                - sequence_params: measurement parameters
                - timing_info: execution timing
                - success: boolean result status
        """
        if pulse_intensity is None:
            pulse_intensity = FLUO_INTENSITY
            
        print(f"🔄 Starting leaf fluorescence measurement (intensity={pulse_intensity})...")
        
        try:
            # Créer séquence standardisée
            sequence = self.create_measurement_sequence(pulse_intensity)
            
            # Timing début
            start_time = time.time()
            
            # Exécution via RCom
            result = self.execute("fluo:execute-sequence", {"sequence": sequence})
            
            # Timing fin
            execution_time = time.time() - start_time
            
            if isinstance(result, dict) and "measurements" in result:
                measurements = result.get("measurements", [])
                timestamps = result.get("timestamps", 
                    [i * 0.2 for i in range(len(measurements))])  # 5Hz = 0.2s
                
                # Construction résultat enrichi
                measurement_result = {
                    "success": True,
                    "measurements": measurements,
                    "timestamps": timestamps,
                    "sequence_params": {
                        "pulse_intensity": pulse_intensity,
                        "dark_intensity": 1,
                        "initial_dark_duration": 5.0,   # 25 points * 0.2s
                        "pulse_duration": 60.0,         # 300 points * 0.2s
                        "final_dark_duration": 60.0,    # 300 points * 0.2s
                        "frequency": FLUO_FREQUENCY_MAX,
                        "total_points": len(measurements),
                        "segments_count": len(sequence)
                    },
                    "timing_info": {
                        "execution_time": execution_time,
                        "theoretical_duration": 125.0,  # 5.0 + 60.0 + 60.0
                        "start_timestamp": datetime.now().isoformat()
                    },
                    "device_info": "Ambit Fluorescence Sensor",
                    "pattern_type": "leaf_targeting_measurement"
                }
                
                print(f"✅ Fluorescence completed: {len(measurements)} points, {execution_time:.1f}s")
                return measurement_result
                
            else:
                print("❌ Error: Invalid response from sensor")
                return {
                    "success": False,
                    "measurements": [],
                    "timestamps": [],
                    "error": "Invalid sensor response",
                    "timing_info": {"execution_time": execution_time}
                }
                
        except Exception as e:
            print(f"❌ Error during fluorescence measurement: {e}")
            return {
                "success": False,
                "measurements": [],
                "timestamps": [],
                "error": str(e),
                "timing_info": {"execution_time": time.time() - start_time if 'start_time' in locals() else 0}
            }


# Test simple si exécuté directement
if __name__ == "__main__":
    print("=== Fluorescence Controller Test ===")
    
    try:
        # Connection ROMI
        fluo = FluoController("fluo", "fluo")
        
        # Status check
        print("Checking device status...")
        status = fluo.get_device_status()
        print(f"  Connected: {status['connected']}")
        print(f"  Status: {status['status']}")
        
        if status['connected']:
            # Test measurement avec intensité par défaut
            print(f"Testing measurement (intensity={FLUO_INTENSITY})...")
            result = fluo.measure_simple()
            
            if result['success']:
                measurements = result['measurements']
                timing = result['timing_info']
                params = result['sequence_params']
                
                print(f"✅ Success: {params['total_points']} points")
                print(f"  Duration: {timing['execution_time']:.1f}s (theo: {timing['theoretical_duration']}s)")
                print(f"  First: {measurements[0]:.6f}, Last: {measurements[-1]:.6f}")
                print(f"  Average: {sum(measurements)/len(measurements):.6f}")
            else:
                print(f"❌ Measurement failed: {result.get('error', 'Unknown error')}")
        else:
            print("⚠️ Device not connected, skipping measurement")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    print("Test completed")