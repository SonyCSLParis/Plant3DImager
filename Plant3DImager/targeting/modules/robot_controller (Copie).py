# targeting/modules/robot_controller.py
import time
import math
import numpy as np
import os
import json
from datetime import datetime

class RobotController:
    def __init__(self, cnc=None, camera=None, gimbal=None, fluo_sensor=None, output_dirs=None, speed=0.1, update_interval=0.1):
        """
        Initialize robot controller with optional fluorescence sensor support
        """
        self.cnc = cnc
        self.camera = camera
        self.gimbal = gimbal
        self.fluo_sensor = fluo_sensor
        self.speed = speed
        self.update_interval = update_interval
        
        # Photos directory
        self.photos_dir = None
        if output_dirs and 'images' in output_dirs:
            self.photos_dir = output_dirs['images']
        
        # Analysis directory for fluorescence data
        self.analysis_dir = None
        if output_dirs and 'analysis' in output_dirs:
            self.analysis_dir = output_dirs['analysis']
        
        # State
        self.initialized = cnc is not None and camera is not None and gimbal is not None
        self.fluo_available = fluo_sensor is not None
        
        if self.initialized:
            print("Robot controller initialized.")
            if self.fluo_available:
                print("Fluorescence sensor available.")
            else:
                print("Photo-only mode.")
        else:
            print("Robot controller partially initialized.")
    
    def _segment_path_by_actions(self, path):
        """Segment trajectory by action points (photo/fluoro)"""
        segments = []
        action_indices = []
        
        # Find action indices
        for i, point_info in enumerate(path):
            if point_info["type"] in ["photo_point", "fluoro_point", "return_photo_point"]:
                action_indices.append(i)
        
        if not action_indices:
            return [path]
        
        # Create segments
        start_idx = 0
        
        for action_idx in action_indices:
            # Segment from start to action (inclusive)
            segment = path[start_idx:action_idx + 1]
            segments.append(segment)
            start_idx = action_idx
        
        # Final segment from last action to end
        if start_idx < len(path) - 1:
            final_segment = path[start_idx:]
            segments.append(final_segment)
        
        return segments
    
    def _execute_segment(self, segment):
        """Execute trajectory segment using travel() with move_to fallback"""
        if len(segment) <= 1:
            return True
        
        waypoints = [point_info["position"] for point_info in segment]
        
        # Essayer travel() d'abord
        success = self.cnc.travel(waypoints, wait=True)
        if success:
            return True
        
        print("Travel failed, using move_to fallback...")
        
        # Fallback : move_to pour chaque point
        for point in waypoints:
            success = self.cnc.move_to(point[0], point[1], point[2], wait=True)
            if not success:
                print("Move_to also failed!")
                return False
        
        return True
    
    def _execute_photo_actions(self, point_info, auto_photo, stabilization_time):
        """Execute photo actions at photo_point"""
        leaf_data = point_info.get("leaf_data", {})
        leaf_centroid = leaf_data.get("centroid")
        leaf_id = leaf_data.get("id")
        
        if not leaf_centroid:
            print("No leaf centroid data for photo point")
            return False
        
        final_pos = self.cnc.get_position()
        
        print(f"\n--- Photo position for leaf {leaf_id} ---")
        print(f"Orienting toward centroid: {leaf_centroid}")
        
        # Orient gimbal toward leaf
        success = self.gimbal.aim_at_target(final_pos, leaf_centroid, wait=True, invert_tilt=True)
        if not success:
            print("Error orienting toward leaf")
            return False
        
        # Stabilization
        print(f"Stabilizing for {stabilization_time} seconds...")
        time.sleep(stabilization_time)
        
        # Take photo
        if auto_photo:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"leaf_{leaf_id}_{timestamp}.jpg"
            
            camera_pose = {
                'x': final_pos['x'],
                'y': final_pos['y'],
                'z': final_pos['z'],
                'pan_angle': self.gimbal.current_pan,
                'tilt_angle': self.gimbal.current_tilt
            }
            
            photo_path, _ = self.camera.take_photo(filename, camera_pose)
            if photo_path:
                print(f"Photo taken: {photo_path}")
        
        # Rotate tilt 180° for fluorescence preparation
        print("Rotating tilt 180° for fluorescence preparation...")
        success = self.gimbal.send_command(0, 180, wait_for_goal=True)
        if not success:
            print("Warning: Could not rotate tilt for fluorescence preparation")
        
        return True
    
    def _execute_fluoro_actions(self, point_info):
        """Execute fluorescence actions at fluoro_point with new sequence protocol"""
        leaf_data = point_info.get("leaf_data", {})
        leaf_id = leaf_data.get("id")
        
        final_pos = self.cnc.get_position()
        
        print(f"\n--- Fluorescence measurement for leaf {leaf_id} ---")
        
        if self.fluo_available:
            print("Performing sequence-based fluorescence measurement...")
            
            # Utiliser la nouvelle interface avec résultat enrichi
            fluo_result = self.fluo_sensor.measure_simple()
            
            if fluo_result and fluo_result.get('success', False):
                measurements = fluo_result['measurements']
                
                # Sauvegarder avec données enrichies
                fluo_data = self.save_fluorescence_data(
                    fluo_result, leaf_id, final_pos, 0
                )
                
                # Statistiques pour log
                sequence_params = fluo_result.get('sequence_params', {})
                timing_info = fluo_result.get('timing_info', {})
                
                print(f"Fluorescence completed: {len(measurements)} points")
                print(f"Protocol: {sequence_params.get('pulse_duration', 0)}s pulse + {sequence_params.get('dark_duration', 0)}s dark")
                print(f"Timing: {timing_info.get('execution_time', 0):.1f}s (theo: {timing_info.get('theoretical_duration', 0)}s)")
                print(f"Average fluorescence: {np.mean(measurements):.6f}")
                
                return True
            else:
                error_msg = fluo_result.get('error', 'Unknown error') if fluo_result else 'No response'
                print(f"Error: Fluorescence measurement failed - {error_msg}")
                return False
        else:
            print("No fluorescence sensor available")
            return True
    
    def _execute_return_photo_actions(self, point_info):
        """Execute actions at return photo point (tilt reset to normal position)"""
        leaf_data = point_info.get("leaf_data", {})
        leaf_id = leaf_data.get("id")
        
        print(f"\n--- Return to photo position for leaf {leaf_id} ---")
        print("Rotating tilt back to normal position...")
        
        success = self.gimbal.send_command(0, -180, wait_for_goal=True)
        if success:
            print("Tilt rotated back successfully - Ready for next leaf")
        else:
            print("Warning: Could not rotate tilt back")
        
        return success
    
    def execute_path(self, path, leaf_centroids=None, leaf_ids=None, auto_photo=True, stabilization_time=3.0):
        """
        Execute complete trajectory with curved paths and full measurement protocol
        
        Args:
            path: List of dictionaries with curved trajectory
            leaf_centroids: Ignored (data in path)
            leaf_ids: Ignored (data in path) 
            auto_photo: Take photos automatically
            stabilization_time: Stabilization time
            
        Returns:
            True if successful
        """
        if not self.initialized:
            print("Error: Robot not initialized.")
            return False
        
        try:
            # Segment trajectory by action points
            segments = self._segment_path_by_actions(path)
            print(f"Trajectory segmented into {len(segments)} parts")
            
            for i, segment in enumerate(segments):
                print(f"\n--- Executing segment {i+1}/{len(segments)} ---")
                
                # Execute segment with travel()
                if len(segment) > 1:
                    success = self._execute_segment(segment)
                    if not success:
                        print(f"Error executing segment {i+1}")
                        continue
                
                # Check segment end point type for actions
                last_point = segment[-1]
                point_type = last_point["type"]
                
                if point_type == "photo_point":
                    self._execute_photo_actions(last_point, auto_photo, stabilization_time)
                    
                elif point_type == "fluoro_point":
                    self._execute_fluoro_actions(last_point)
                    
                elif point_type == "return_photo_point":
                    self._execute_return_photo_actions(last_point)
            
            return True
            
        except Exception as e:
            print(f"Error executing trajectory: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_fluorescence_data(self, fluo_result, leaf_id, position, leaf_index):
        """
        Save enriched fluorescence measurements to JSON file
        
        Args:
            fluo_result (dict): Complete result from FluoController.measure_simple()
            leaf_id: Leaf identifier  
            position: Robot position dict
            leaf_index: Leaf index number
            
        Returns:
            dict: Complete saved data
        """
        timestamp = datetime.now().isoformat()
        
        # Extraire données du capteur
        measurements = fluo_result.get('measurements', [])
        timestamps = fluo_result.get('timestamps', [])
        sequence_params = fluo_result.get('sequence_params', {})
        timing_info = fluo_result.get('timing_info', {})
        device_info = fluo_result.get('device_info', 'Unknown sensor')
        pattern_type = fluo_result.get('pattern_type', 'unknown')
        
        # JSON enrichi combinant robot + capteur
        enriched_fluo_data = {
            # Données robot (format original)
            "timestamp": timestamp,
            "leaf_id": leaf_id if leaf_id is not None else f"leaf_{leaf_index + 1}",
            "leaf_index": leaf_index,
            "position": {
                "x": position['x'],
                "y": position['y'], 
                "z": position['z']
            },
            "camera_angles": {
                "pan": self.gimbal.current_pan,
                "tilt": self.gimbal.current_tilt
            },
            "measurements": measurements,
            "statistics": {
                "count": len(measurements),
                "mean": float(np.mean(measurements)) if measurements else 0,
                "std": float(np.std(measurements)) if measurements else 0,
                "min": float(np.min(measurements)) if measurements else 0,
                "max": float(np.max(measurements)) if measurements else 0
            },
            
            # Nouvelles données capteur (enrichissement)
            "timestamps": timestamps,
            "sequence_params": sequence_params,
            "timing_info": timing_info,
            "device_info": device_info,
            "pattern_type": pattern_type,
            
            # Métadonnées intégration
            "format_version": "2.0",
            "integration": "ROMI_leaf_targeting"
        }
        
        # Save to file
        if self.analysis_dir:
            timestamp_safe = timestamp.replace(':', '-')
            filename = f"fluorescence_leaf_{enriched_fluo_data['leaf_id']}_{timestamp_safe}.json"
            filepath = os.path.join(self.analysis_dir, filename)
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(enriched_fluo_data, f, indent=2)
                print(f"Enriched fluorescence data saved: {filepath}")
            except Exception as e:
                print(f"Warning: Could not save fluorescence data: {e}")
        
        return enriched_fluo_data
    
    def shutdown(self):
        """Properly shut down the robot"""
        print("Shutting down robot...")
        
        if self.cnc is not None:
            try:
                print("Moving to (0,0,0) and homing...")
                self.cnc.move_to(0, 0, 0)
                self.cnc.home()
            except Exception as e:
                print(f"Error during homing: {e}")
        
        if self.gimbal is not None:
            try:
                print("Resetting camera position...")
                self.gimbal.reset_position()
            except Exception as e:
                print(f"Error resetting camera: {e}")
        
        return True