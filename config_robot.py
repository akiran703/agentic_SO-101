"""
Configuration for the robot controller. has some preset data to keep robot in default position
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Tuple
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig


@dataclass
class RobotConfig:
    """Configuration for the robot controller."""

    # Serial port (change the port according to what you have)
    my_port = "/dev/tty.usbmodem59090526531"
    
    # robot type
    ROBOT_TYPE = "lekiwi"
    
    # only for LeKiwi
    DEFAULT_REMOTE_IP = "192.168.1.1" 
    
    # absolute path to the calibration file
    calibration_file = os.path.join(os.path.dirname(__file__), "main_follower.json")
    
    #default camera values 
    CAMERA_FPS = 30
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT= 360
    
    motors_to_degrees = field({
            "shoulder_pan": (-91.7, 99.5, 0.0, 180.0),
            "shoulder_lift": (-89.4, 99.4, 0, 180.0),
            "elbow_flex": (96.5, -92.7, 0, 180.0),
            "wrist_flex": (-90.0, 90.0, -90.0, 90.0),
            "wrist_roll":  (100, -100, -90, 90),
            "gripper":  (31.0, 100.0, 0.0, 100.0)
        })
    
    # Constants for smooth interpolation
    # Degrees per interpolation step
    # Maximum number of interpolation steps
    # Delay between interpolation steps (100Hz)
    MOVEMENT_CONSTANTS = field(
        default_factory=lambda: {
            "DEGREES_PER_STEP": 1.5,          
            "MAX_INTERPOLATION_STEPS": 150,    
            "STEP_DELAY_SECONDS": 0.01,        
        }
    )
    
    # Camera configuration using lerobot format
    # hugging face has many robots so made it compitable with these robots "so100", "so101", "lekiwi"
    lerobot_config = field(
        default_factory=lambda: {
            "type": "so100",
            "port": "/dev/tty.usbmodem59090526531",
            "remote_ip": "192.168.1.1",
            "cameras": {
                "front": OpenCVCameraConfig(
                    index_or_path=0,
                    fps=30,
                    width=640,
                    height=360,
                ),
                "wrist": OpenCVCameraConfig(
                    index_or_path=1,
                    fps=30,
                    width=640,
                    height=360,
                ),
                "top": OpenCVCameraConfig(
                    index_or_path=2,
                    fps=30,
                    width=640,
                    height=360,
                ),
            },
        }
    )
    
    
    # Kinematic parameter
    KINEMATIC_PARAMS = field(
        default_factory=lambda: 
        {
            "default": 
            {
                "L1": 117.0,  # Length of first lever (shoulder to elbow) in mm
                "L2": 136.0,  # Length of second lever (elbow to wrist_flex axis) in mm
                "BASE_HEIGHT_MM": 120.0, # Height from ground to shoulder_lift axis in mm
                "SHOULDER_MOUNT_OFFSET_MM": 32.0, # Example: Offset for shoulder joint from idealized zero
                "ELBOW_MOUNT_OFFSET_MM": 4.0, # Example: Offset for elbow joint from idealized zero
                "SPATIAL_LIMITS": 
                {
                    "x": (-20.0, 250.0),  # Min/Max X coordinate (mm) for wrist_flex origin
                    "z": (30.0, 370.0),   # Min/Max Z coordinate (mm) for wrist_flex origin
                }
            }
        }
    )
    
    PRESET_POSITIONS: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "1": { "gripper": 0.0, "wrist_roll": 90.0, "wrist_flex": 0.0, "elbow_flex": 0.0, "shoulder_lift": 0.0, "shoulder_pan": 90.0 },
            "2": { "gripper": 0.0, "wrist_roll": 90.0, "wrist_flex": 0.0, "elbow_flex": 45.0, "shoulder_lift": 45.0, "shoulder_pan": 90.0 },
            "3": { "gripper": 40.0, "wrist_roll": 90.0, "wrist_flex": 90.0, "elbow_flex": 45.0, "shoulder_lift": 45.0, "shoulder_pan": 90.0 },
            "4": { "gripper": 40.0, "wrist_roll": 90.0, "wrist_flex": -60.0, "elbow_flex": 20.0, "shoulder_lift": 80.0, "shoulder_pan": 90.0 },
        }
    )
    
    

    robot_description: str = ("""
        Follow these instructions precisely. Never deviate.

        You control a 3D printed robot with 5 DOF + gripper. Max forward reach ~250 mm.
        Shoulder and elbow links are 12 cm and 14 cm. Gripper fingers ~8 cm.
        Use these to estimate distances. E.g., if the object is near but not in the gripper, you can safely move 5–10 cm forward.

        Robot has 3 cameras:
        - front: at the base, looks forward
        - wrist: close view of gripper
        - top view: shows whole robot

        Instructions:
        - Move slowly and iteratively
        - Close gripper completely to grab objects
        - Check results after each move before proceeding
        - Split into smaller steps and reanalyze after each one
        - Use only the latest images to evaluate success
        - Always plan movements to avoid collisions
        - Move above object with gripper tilted up (10–15°) to avoid collisions. Stay >25 cm above ground when moving or rotating
        - Never move with gripper near the ground
        - Drop and restart plan if unsure or failed
        """
    )
    
    


    
# Create a global instance
robot_config = RobotConfig()

