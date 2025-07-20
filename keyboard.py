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
from robot_controller import RobotController
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
        self.key_mappings[keyboard.KeyCode.from_char('q')] =  ("gripper_delta", self.gripper_step_pct),  # Open incrementally
        self.key_mappings[keyboard.KeyCode.from_char('e')] = ("gripper_delta", -self.gripper_step_pct), # Close incrementally

        # Camera snapshot
        self.key_mappings[keyboard.KeyCode.from_char('c')] = ("camera_snapshot", None)
            
        # Preset positions
        self.key_mappings[keyboard.KeyCode.from_char('1')] =  ("preset", "1")
        self.key_mappings[keyboard.KeyCode.from_char('2')] = ("preset", "2")
        self.key_mappings[keyboard.KeyCode.from_char('3')] =  ("preset", "3")
        self.key_mappings[keyboard.KeyCode.from_char('4')] = ("preset", "4")
        

   
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