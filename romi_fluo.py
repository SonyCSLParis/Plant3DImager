#!/usr/bin/env python3
"""
Python wrapper for Ambit fluorescence sensor - ROMI style
Inherits from RcomClient like CNC for auto-discovery
Professional interface with simplified parameters (no actinic confusion)
CORRIGÉ: Gestion adaptative des timeouts et suppression du paramètre actinic
"""

from rcom.rcom_client import RcomClient
import json
import time

class FluoSensor(RcomClient):
    """
    Interface for Ambit fluorescence sensor via RCom
    Inherits from RcomClient like CNC for consistency
    
    Usage: 
        fluo = FluoSensor("fluo", "fluo")
        measurements = fluo.measure()
    """
    
    def __init__(self, topic="fluo", id="fluo"):
        """
        Initialize connection to fluorescence sensor
        
        Args:
            topic (str): RCom topic name (default "fluo")  
            id (str): RCom service ID (default "fluo")
        """
        # Call parent constructor (like CNC)
        super().__init__(topic, id)
        print(f"FluoSensor connected to service '{topic}' (id: {id})")
    
    def _calculate_timeout(self, length=100, frequency=10.0, safety_margin=15):
        """
        Calculate adaptive timeout based on measurement parameters
        NOUVEAU: Timeout adaptatif synchronisé avec le code C++
        
        Args:
            length (int): Number of measurement points
            frequency (float): Sampling frequency in Hz
            safety_margin (int): Safety margin in seconds (default 15s)
            
        Returns:
            int: Timeout in seconds (minimum 20s)
        """
        estimated_time = length / frequency
        timeout = int(estimated_time + safety_margin)
        return max(timeout, 20)  # Minimum 20s même pour mesures courtes
    
    def measure(self):
        """
        Perform fluorescence measurement with active configuration
        AMÉLIORÉ: Affiche les informations de timeout pour l'utilisateur
        Note: Le timeout adaptatif est géré côté C++ dans Ambit.cpp
        
        Returns:
            list: List of measured fluorescence values
        """
        try:
            # Calculer et afficher les informations de timeout pour l'utilisateur
            try:
                config = self.get_active_config_details()
                if config:
                    length = config.get('length', 100)
                    frequency = config.get('frequency', 10.0)
                    timeout = self._calculate_timeout(length, frequency)
                    estimated_duration = length / frequency
                    print(f"🔄 Starting measurement: {length} points @ {frequency}Hz")
                    print(f"⏱️  Estimated duration: {estimated_duration:.1f}s (C++ timeout: {timeout}s)")
                else:
                    print("🔄 Starting measurement with active configuration...")
            except:
                print("🔄 Starting measurement...")
            
            # Execute sans paramètre timeout (géré côté C++)
            result = self.execute("fluo:measure", {})
            if isinstance(result, dict):
                measurements = result.get("measurements", [])
                print(f"✅ Measurement completed: {len(measurements)} points")
                return measurements
            return []
        except Exception as e:
            print(f"❌ Error during measurement: {e}")
            return []
    
    def measure_with_params(self, intensity=0.5, length=100, frequency=10.0, persist=False):
        """
        Perform measurement with specific parameters
        CORRIGÉ: Interface simplifiée sans paramètre actinic
        AMÉLIORÉ: Affiche les informations de timeout (géré côté C++)
        
        Args:
            intensity (float): LED intensity (0.0-1.0) - single light parameter
            length (int): Number of measurement points (1-2000)  
            frequency (float): Sampling frequency in Hz (1.0-200.0)
            persist (bool): Save parameters as persistent
            
        Returns:
            list: List of measured fluorescence values
        """
        # Interface simplifiée - SANS actinic (CORRIGÉ)
        params = {
            "intensity": intensity,    # Seul paramètre lumière
            "length": length,
            "frequency": frequency,
            "persist": persist
        }
        
        try:
            # Calculer et afficher les informations pour l'utilisateur
            timeout = self._calculate_timeout(length, frequency)
            estimated_duration = length / frequency
            print(f"🔄 Starting measurement: {length} points @ {frequency}Hz ({estimated_duration:.1f}s estimated)")
            print(f"⏱️  C++ adaptive timeout: {timeout}s (+15s safety margin)")
            
            # Execute sans paramètre timeout (géré côté C++)
            result = self.execute("fluo:measure-with-params", params)
            if isinstance(result, dict):
                measurements = result.get("measurements", [])
                print(f"✅ Measurement completed: {len(measurements)} points")
                return measurements
            return []
        except Exception as e:
            print(f"❌ Error during parameterized measurement: {e}")
            return []
    
    def list_configs(self):
        """
        List all available configurations
        
        Returns:
            list: Names of available configurations
        """
        try:
            result = self.execute("fluo:list-configs", {})
            if isinstance(result, dict):
                return result.get("configs", [])
            return []
        except Exception as e:
            print(f"Error listing configurations: {e}")
            return []
    
    def get_config(self, name):
        """
        Get configuration details by name
        
        Args:
            name (str): Configuration name
            
        Returns:
            dict: Configuration details or None if error
        """
        try:
            result = self.execute("fluo:get-config", {"name": name})
            if isinstance(result, dict):
                return result.get("config", None)
            return None
        except Exception as e:
            print(f"Error retrieving configuration '{name}': {e}")
            return None
    
    def create_config(self, config):
        """
        Create new custom configuration
        
        Args:
            config (dict): Configuration with keys name, description, intensity, length, frequency, persist
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.execute("fluo:create-config", config)
            if isinstance(result, dict):
                return result.get("success", False)
            return False
        except Exception as e:
            print(f"Error creating configuration: {e}")
            return False
    
    def update_config(self, config):
        """
        Update existing configuration
        
        Args:
            config (dict): Modified configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.execute("fluo:update-config", config)
            if isinstance(result, dict):
                return result.get("success", False)
            return False
        except Exception as e:
            print(f"Error updating configuration: {e}")
            return False
    
    def delete_config(self, name):
        """
        Delete custom configuration
        
        Args:
            name (str): Configuration name to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.execute("fluo:delete-config", {"name": name})
            if isinstance(result, dict):
                return result.get("success", False)
            return False
        except Exception as e:
            print(f"Error deleting configuration '{name}': {e}")
            return False
    
    def set_active_config(self, name):
        """
        Set active configuration (persistent)
        
        Args:
            name (str): Configuration name to activate
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.execute("fluo:set-active-config", {"name": name})
            if isinstance(result, dict):
                return result.get("success", False)
            return False
        except Exception as e:
            print(f"Error setting active configuration to '{name}': {e}")
            return False
    
    def get_active_config(self):
        """
        Get active configuration name
        
        Returns:
            str: Active configuration name or None if error
        """
        try:
            result = self.execute("fluo:get-active-config", {})
            if isinstance(result, dict):
                return result.get("active_config", None)
            return None
        except Exception as e:
            print(f"Error getting active configuration: {e}")
            return None
    
    def get_active_config_details(self):
        """
        Get complete details of active configuration
        
        Returns:
            dict: Active configuration details or None if error
        """
        try:
            result = self.execute("fluo:get-active-config-details", {})
            if isinstance(result, dict):
                return result.get("config", None)
            return None
        except Exception as e:
            print(f"Error getting active configuration details: {e}")
            return None
    
    def get_device_status(self):
        """
        Get real-time device connection status
        AMÉLIORÉ: Utilise la nouvelle méthode RPC implémentée côté C++
        
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


# Usage example and testing
if __name__ == "__main__":
    print("=== Fluorescence Sensor Test ===")
    
    try:
        # Connect to sensor (like CNC)
        fluo = FluoSensor("fluo", "fluo")
        
        print("\n1. Available configurations:")
        configs = fluo.list_configs()
        for config in configs:
            print(f"  - {config}")
        
        print(f"\n2. Active configuration: {fluo.get_active_config()}")
        
        print("\n3. Active configuration details:")
        active_details = fluo.get_active_config_details()
        if active_details:
            print(json.dumps(active_details, indent=2))
        
        print("\n4. Device status:")
        status = fluo.get_device_status()
        print(f"  Connected: {status['connected']}")
        print(f"  Status: {status['status']}")
        
        if status['connected']:
            print("\n5. Quick test with short configuration:")
            # Use quick config for fast test
            fluo.set_active_config("quick")
            print("Configuration changed to 'quick' for fast test")
            
            fluorescence_data = fluo.measure()
            if fluorescence_data:
                print(f"  Number of points: {len(fluorescence_data)}")
                print(f"  First value: {fluorescence_data[0]:.6f}")
                print(f"  Last value: {fluorescence_data[-1]:.6f}")
                print(f"  Average: {sum(fluorescence_data)/len(fluorescence_data):.6f}")
            else:
                print("  No data received with 'quick' config")
            
            print("\n6. Custom parameter measurement with adaptive timeout:")
            # Interface simplifiée - SANS actinic (CORRIGÉ)
            custom_data = fluo.measure_with_params(
                intensity=0.6,   # 60% LED intensity - seul paramètre lumière
                length=20,       # 20 points pour test rapide  
                frequency=10.0   # 10 Hz
                # timeout calculé automatiquement: (20/10.0) + 15 = ~17s minimum 20s
            )
            if custom_data:
                print(f"  Number of points: {len(custom_data)}")
                print(f"  Average: {sum(custom_data)/len(custom_data):.6f}")
            else:
                print("  No data received with custom parameters")
        else:
            print("⚠️  Device not connected - skipping measurements")
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print("Test completed")
