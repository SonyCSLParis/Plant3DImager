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
            if point_info["type"] in ["photo_point", "fluoro_point"]:
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
        """Execute trajectory segment using travel()"""
        if len(segment) <= 1:
            return True
        
        waypoints = [point_info["position"] for point_info in segment]
        return self.cnc.travel(waypoints, wait=True)
    
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
        """Execute fluorescence actions at fluoro_point"""
        leaf_data = point_info.get("leaf_data", {})
        leaf_id = leaf_data.get("id")
        
        final_pos = self.cnc.get_position()
        
        print(f"\n--- Fluorescence measurement for leaf {leaf_id} ---")
        
        if self.fluo_available:
            print("Performing fluorescence measurement...")
            measurements = self.fluo_sensor.measure_simple()
            
            if measurements:
                fluo_data = self.save_fluorescence_data(
                    measurements, leaf_id, final_pos, 0
                )
                print(f"Fluorescence completed: {len(measurements)} points")
                print(f"Average: {np.mean(measurements):.6f}")
            else:
                print("Error: No fluorescence data received")
        else:
            print("No fluorescence sensor available")
        
        return True
    
    def _execute_post_fluoro_actions(self, next_point_info):
        """Execute post-fluorescence actions (tilt reset)"""
        print("Rotating tilt back to normal position...")
        success = self.gimbal.send_command(0, -180, wait_for_goal=True)
        if success:
            print("Tilt rotated back successfully")
        else:
            print("Warning: Could not rotate tilt back")
        
        return True
    
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
                    
                    # Check if next segment exists and reset tilt
                    if i + 1 < len(segments):
                        next_segment = segments[i + 1]
                        if next_segment:
                            self._execute_post_fluoro_actions(next_segment[0])
            
            return True
            
        except Exception as e:
            print(f"Error executing trajectory: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_fluorescence_data(self, measurements, leaf_id, position, leaf_index):
        """Save fluorescence measurements to JSON file"""
        timestamp = datetime.now().isoformat()
        
        fluo_data = {
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
                "mean": float(np.mean(measurements)),
                "std": float(np.std(measurements)),
                "min": float(np.min(measurements)),
                "max": float(np.max(measurements))
            }
        }
        
        # Save to file
        if self.analysis_dir:
            filename = f"fluorescence_leaf_{fluo_data['leaf_id']}_{timestamp.replace(':', '-')}.json"
            filepath = os.path.join(self.analysis_dir, filename)
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(fluo_data, f, indent=2)
                print(f"Fluorescence data saved: {filepath}")
            except Exception as e:
                print(f"Warning: Could not save fluorescence data: {e}")
        
        return fluo_data
    
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