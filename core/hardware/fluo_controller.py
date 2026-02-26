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
FLUO_INTENSITY = 20   # Intensité LED actinic pour mesures sur feuilles

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
        Séquence de mesure pour le ciblage foliaire :
          1. 10s  obscurité         (intensité = 0)
          2. 0.6s pulse saturant    (intensité = 255)
          3. 60s  actinic           (intensité = FLUO_INTENSITY)
          4. 0.6s pulse saturant    (intensité = 255)
          5. 60s  récupération      (intensité = 0)

        Args:
            pulse_intensity (int): intensité actinic phase 3 (défaut : FLUO_INTENSITY)

        Returns:
            list: séquence compatible avec fluo:execute-sequence
        """
        if pulse_intensity is None:
            pulse_intensity = FLUO_INTENSITY

        sequence = [
            {
                "num_points": 75,                    # 15s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX,
                "actinic": 0                         # obscurité initiale
            },
            {
                "num_points": 3,                     # 0.6s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX,
                "actinic": 255                       # 1er pulse saturant
            },
            {
                "num_points": 300,                   # 60s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX,
                "actinic": pulse_intensity           # lumière actinic
            },
            {
                "num_points": 3,                     # 0.6s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX,
                "actinic": 255                       # 2e pulse saturant
            },
            {
                "num_points": 300,                   # 60s à 5Hz
                "frequency": FLUO_FREQUENCY_MAX,
                "actinic": 0                         # récupération obscurité
            },
        ]

        return sequence

    def measure_simple(self, pulse_intensity=None):
        """
        Perform leaf targeting fluorescence measurement with standard protocol
        Protocol:
          10s dark (0) + 0.6s sat pulse (255) + 60s actinic + 0.6s sat pulse (255) + 60s dark (0)
          Total theoretical duration: 131.2s, 656 points at 5Hz

        Args:
            pulse_intensity (int): LED intensity 0-255 (default: FLUO_INTENSITY=20)

        Returns:
            dict: Complete measurement result
        """
        if pulse_intensity is None:
            pulse_intensity = FLUO_INTENSITY

        print(f"🔄 Starting leaf fluorescence measurement (intensity={pulse_intensity})...")

        try:
            sequence = self.create_measurement_sequence(pulse_intensity)

            start_time = time.time()
            result = self.execute("fluo:execute-sequence", {"sequence": sequence})
            execution_time = time.time() - start_time

            if isinstance(result, dict) and "measurements" in result:
                measurements = result.get("measurements", [])
                timestamps = result.get("timestamps",
                    [i * (1.0 / FLUO_FREQUENCY_MAX) for i in range(len(measurements))])

                measurement_result = {
                    "success": True,
                    "measurements": measurements,
                    "timestamps": timestamps,
                    "sequence_params": {
                        "pulse_intensity": pulse_intensity,
                        "sat_pulse_intensity": 255,
                        "dark_intensity": 0,
                        "initial_dark_duration": 15.0,    # 75 points * 0.2s
                        "sat_pulse_duration": 0.6,        # 3 points * 0.2s
                        "actinic_duration": 60.0,         # 300 points * 0.2s
                        "recovery_duration": 60.0,        # 300 points * 0.2s
                        "frequency": FLUO_FREQUENCY_MAX,
                        "total_points": len(measurements),
                        "segments_count": len(sequence)
                    },
                    "timing_info": {
                        "execution_time": execution_time,
                        "theoretical_duration": 136.2,   # 15 + 0.6 + 60 + 0.6 + 60
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