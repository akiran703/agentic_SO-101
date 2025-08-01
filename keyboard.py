#!/usr/bin/env python3
"""
Keyboard controller for intuitive robot control.
"""

import sys
import time
import os
import logging
from datetime import datetime
from typing import Dict, Any
from pynput import keyboard
from controller_for_arm import RobotController
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

#created this class to control arm with keyboard inputs
class KeyboardController:
   #initalizing object state
    def __init__(self, robot_controller: RobotController):
        self.robot = robot_controller
        self.running = False
        
        self.spatial_step_mm = 2.0
        self.angle_step_deg = 2.0
        self.gripper_step_pct = 3.0
        
        # Create a directory if it doesn't exist
        self.snapshots_dir = "camera_snapshots"
        os.makedirs(self.snapshots_dir, exist_ok=True)
        
        # Key mappings using exact same keys as original
        self.key_mappings = {}
        
        # Cartesian movements
        self.key_mappings[keyboard.KeyCode.from_char('w')] = ("intuitive_move", {"move_gripper_forward_mm": self.spatial_step_mm})
        self.key_mappings[keyboard.KeyCode.from_char('s')] = ("intuitive_move", {"move_gripper_forward_mm": -self.spatial_step_mm})
        self.key_mappings[keyboard.Key.up] = ("intuitive_move", {"move_gripper_up_mm": self.spatial_step_mm})
        self.key_mappings[keyboard.Key.down] = ("intuitive_move", {"move_gripper_up_mm": -self.spatial_step_mm})
         
           
        # counter clockwise movement 
        self.key_mappings[keyboard.Key.left] = ("intuitive_move", {"rotate_robot_right_angle": -self.angle_step_deg})
        #clockwise movement
        self.key_mappings[keyboard.Key.right] = ("intuitive_move", {"rotate_robot_right_angle": self.angle_step_deg})
          
            
        # Tilt gripper up
        self.key_mappings[keyboard.KeyCode.from_char('r')] = ("intuitive_move", {"tilt_gripper_down_angle": -self.angle_step_deg})
        #Tilt gripper down
        self.key_mappings[keyboard.KeyCode.from_char('f')] = ("intuitive_move", {"tilt_gripper_down_angle": self.angle_step_deg})
            
        # Gripper rotation counterclock wise
        self.key_mappings[keyboard.KeyCode.from_char('a')] = ("intuitive_move", {"rotate_gripper_clockwise_angle": -self.angle_step_deg})
        #gripper rotation clockwise
        self.key_mappings[keyboard.KeyCode.from_char('d')] =  ("intuitive_move", {"rotate_gripper_clockwise_angle": self.angle_step_deg})
            
        # Gripper control
        self.key_mappings[keyboard.KeyCode.from_char('q')] =  ("gripper_delta", self.gripper_step_pct)  # Open incrementally
        self.key_mappings[keyboard.KeyCode.from_char('e')] = ("gripper_delta", -self.gripper_step_pct) # Close incrementally

        # Camera snapshot
        self.key_mappings[keyboard.KeyCode.from_char('c')] = ("camera_snapshot", None)
            
        # Preset positions
        self.key_mappings[keyboard.KeyCode.from_char('1')] =  ("preset", "1")
        self.key_mappings[keyboard.KeyCode.from_char('2')] = ("preset", "2")
        self.key_mappings[keyboard.KeyCode.from_char('3')] =  ("preset", "3")
        self.key_mappings[keyboard.KeyCode.from_char('4')] = ("preset", "4")
    
    
    #handles the events of when a key is pressed    
    def on_press(self, key: Any) -> bool:
        
        if key == keyboard.Key.esc:
            self.stop()
            return False  # Stop listener

        if key in self.key_mappings:
            action_type, params = self.key_mappings[key]
            
            try:
                if action_type == "intuitive_move":
                    result = self.robot.execute_interpolated(**params, use_interpolation=False)
                    if not result.ok:
                        print(f"Movement error: {result.msg}")
                        
                elif action_type == "gripper_delta":
                    delta = params
                    result = self.robot.increment_joints_by_delta({'gripper': delta})
                    if not result.ok:
                        print(f"Gripper error: {result.msg}")
                        
                elif action_type == "preset":
                    preset_key = params
                    result = self.robot.apply_named_preset(preset_key)
                    if result.ok:
                        print(f"Applied preset {preset_key}")
                    else:
                        print(f"Preset error: {result.msg}")
                        
                elif action_type == "camera_snapshot":
                    self.take_camera_snapshot()
                    
            except Exception as e:
                logger.error(f"Error executing command: {e}", exc_info=True)
                
        return True

    
    def take_camera_snapshot(self) -> None:
        try:
            images = self.robot.get_camera_images()
            if not images:
                print("No camera images available")
                return
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_count = 0
            
            for camera_name, img_array in images.items():
                try:
                    pil_img = Image.fromarray(img_array)
                    filename = os.path.join(self.snapshots_dir, f"{camera_name}_{timestamp}.jpg")
                    pil_img.save(filename)
                    saved_count += 1
                    print(f"Saved {camera_name} snapshot: {filename}")
                except Exception as e:
                    logger.error(f"Failed to save snapshot for '{camera_name}': {e}")
                    
            if saved_count > 0:
                print(f"📸 Saved {saved_count} camera snapshot(s) to {self.snapshots_dir}/")
                
        except Exception as e:
            logger.error(f"Camera snapshot error: {e}", exc_info=True)
            print("Failed to take camera snapshot")
    
    
    #function to start keyboard control
    def start(self) -> None:
        # Print controls once at startup
        print("\n" + "="*50)
        print("🎮 KEYBOARD CONTROLLER ACTIVE")
        print("="*50)
        print("📍 CARTESIAN MOVEMENT:")
        print(f"   W/S: Gripper Forward/Backward ({self.spatial_step_mm} mm)")
        print(f"   ↑/↓: Gripper Up/Down ({self.spatial_step_mm} mm)")
        print()
        print("🔄 ROTATIONS:")
        print(f"   ←/→: Rotate Robot CCW/CW ({self.angle_step_deg}°)")
        print(f"   R/F: Tilt Gripper Up/Down ({self.angle_step_deg}°)")
        print(f"   A/D: Rotate Gripper CCW/CW ({self.angle_step_deg}°)")
        print()
        print("🤏 GRIPPER:")
        print(f"   Q/E: Open/Close ({self.gripper_step_pct}%)")
        print()
        print("📸 CAMERA & PRESETS:")
        print("   C: Camera Snapshot")
        print("   1-4: Preset Positions")
        print()
        print("⚠️  ESC: Exit")
        print("="*50)
        
        self.running = True
        try:
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.start()
            print("✅ Keyboard controller started. Press keys to control robot.")
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}", exc_info=True)
            self.running = False

    #stop keyboard controller
    def stop(self) -> None:
        if self.running:
            print("\n🛑 Stopping keyboard controller...")
            self.running = False
            if hasattr(self, 'listener') and self.listener.is_alive():
                try:
                    self.listener.stop()
                except Exception as e:
                    logger.error(f"Error stopping listener: {e}")

    #makes sure it exists completely 
    def wait_for_exit(self) -> None:
        if hasattr(self, 'listener'):
            try:
                self.listener.join()
            except Exception as e:
                logger.error(f"Error waiting for listener: {e}")
                
                
def main():
    #executes all with error handling 
    print("🚀 Starting Keyboard Controller...")
    
    robot_instance = None
    kb_controller = None
    
    try:
        # Initialize robot controller
        print("🔌 Connecting to robot...")
        robot_instance = RobotController()
        print("✅ Robot connected successfully")
        
        # Initialize keyboard controller
        kb_controller = KeyboardController(robot_instance)
        kb_controller.start()
        
        # Keep main thread alive while keyboard listener runs
        while kb_controller.running:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n⚠️  KeyboardInterrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Critical error in keyboard controller: {e}", exc_info=True)
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        if kb_controller and kb_controller.running:
            print("Cleaning up keyboard controller...")
            kb_controller.stop()
        if robot_instance:
            print("Disconnecting robot...")
            robot_instance.disconnect(reset_pos=True)
        print("Keyboard controller finished.")

if __name__ == "__main__":
    sys.exit(main())