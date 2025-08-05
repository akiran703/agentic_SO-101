"""
Configuration for the robot controller. has some preset data to keep robot in default position
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Tuple,Any, Final
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

# Module-level constants
DEFAULT_ROBOT_TYPE: Final[str] = "so101" # "so100", "so101", "lekiwi"
DEFAULT_SERIAL_PORT: Final[str] = "/dev/tty.usbmodem59090526531" # only for SO ARM
DEFAULT_REMOTE_IP: Final[str] = "192.168.1.1" # only for LeKiwi

# Camera configuration constants
# Can also be different for different cameras, set it in lerobot_config
DEFAULT_CAMERA_FPS: Final[int] = 30
DEFAULT_CAMERA_WIDTH: Final[int] = 640
DEFAULT_CAMERA_HEIGHT: Final[int] = 480

@dataclass
class RobotConfig:
    
    # Camera configuration using lerobot format
    # hugging face has many robots so made it compitable with these robots "so100", "so101", "lekiwi"
    lerobot_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "type": DEFAULT_ROBOT_TYPE,
            "port": DEFAULT_SERIAL_PORT,
            "remote_ip": DEFAULT_REMOTE_IP,
            "cameras": {
                "wrist": OpenCVCameraConfig(
                    index_or_path=1,
                    fps=DEFAULT_CAMERA_FPS,
                    width=DEFAULT_CAMERA_WIDTH,
                    height=DEFAULT_CAMERA_HEIGHT,
                ),
            },
        }
    )

   
    # Format: {motor_name: (norm_min, norm_max, deg_min, deg_max)}
    MOTOR_NORMALIZED_TO_DEGREE_MAPPING: Dict[str, Tuple[float, float, float, float]] = field(
        default_factory=lambda: {
            "shoulder_pan":  (-91.7, 99.5, 0.0, 180.0),
            "shoulder_lift": (-89.4, 99.4, 0, 180.0),
            "elbow_flex":    (96.5, -92.7, 0, 180.0),
            "wrist_flex":    (-90.0, 90.0, -90.0, 90.0),
            "wrist_roll":    (100, -100, -90, 90),
            "gripper":       (31.0, 100.0, 0.0, 100.0),
        }
    )

    # Constants for smooth interpolation
    # Degrees per interpolation step
    # Maximum number of interpolation steps
    # Delay between interpolation steps (100Hz)
    MOVEMENT_CONSTANTS: Dict[str, Any] = field(
        default_factory=lambda: {
            "DEGREES_PER_STEP": 1.5,           
            "MAX_INTERPOLATION_STEPS": 150,    
            "STEP_DELAY_SECONDS": 0.01,        
        }
    )
    
    # Kinematic parameter
    KINEMATIC_PARAMS: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "default": {
                "L1": 117.0,  # Length of first lever (shoulder to elbow) in mm
                "L2": 136.0,  # Length of second lever (elbow to wrist_flex axis) in mm
                "BASE_HEIGHT_MM": 120.0, # Height from ground to shoulder_lift axis in mm
                "SHOULDER_MOUNT_OFFSET_MM": 32.0, # Example: Offset for shoulder joint from idealized zero
                "ELBOW_MOUNT_OFFSET_MM": 4.0, # Example: Offset for elbow joint from idealized zero
                "SPATIAL_LIMITS": {
                    "x": (-20.0, 250.0),  # Min/Max X coordinate (mm) for wrist_flex origin
                    "z": (30.0, 370.0),   # Min/Max Z coordinate (mm) for wrist_flex origin
                }
            }
        }
    )
    
    
    # Predefined robot positions 
    PRESET_POSITIONS: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "1": { "gripper": 0.0, "wrist_roll": 90.0, "wrist_flex": 0.0, "elbow_flex": 0.0, "shoulder_lift": 0.0, "shoulder_pan": 90.0 },
            "2": { "gripper": 0.0, "wrist_roll": 90.0, "wrist_flex": 0.0, "elbow_flex": 45.0, "shoulder_lift": 45.0, "shoulder_pan": 90.0 },
            "3": { "gripper": 40.0, "wrist_roll": 90.0, "wrist_flex": 90.0, "elbow_flex": 45.0, "shoulder_lift": 45.0, "shoulder_pan": 90.0 },
            "4": { "gripper": 40.0, "wrist_roll": 90.0, "wrist_flex": -60.0, "elbow_flex": 20.0, "shoulder_lift": 80.0, "shoulder_pan": 90.0 },
        }
    )

    # Robot description for AI/LLM context
    robot_description: str = ("""
Follow these instructions precisely. Never deviate.

You control a 3D printed robot with 5 DOF + gripper. Max forward reach ~250 mm.
Shoulder and elbow links are 12 cm and 14 cm. Gripper fingers ~8 cm.
Use these to estimate distances. E.g., if the object is near but not in the gripper, you can safely move 5–10 cm forward.

Robot has 1 camera:
- wrist: close view of gripper

Robot is attached to the left side of a table. The dimensions of the table are the following: length is 100 cm and width is 60 cm.
The table has a grid that makes breaking the environment down easier. There are 15 squares in total. There are 3 rows and 5 columns. The dimensions of each grid is 20cm by 20 cm.
Items will generally be placed in the 3th and 4th column. The robot is always in column one. 


Instructions:
- Move slowly and iteratively
- Close gripper completely to grab objects
- Check results after each move before proceeding
- When the object inside your gripper it will not be visible on top and front cameras and will cover the whole view for the wrist one
- Split into smaller steps and reanalyze after each one
- Use only the latest images to evaluate success
- Always plan movements to avoid collisions
- Move above object with gripper tilted up (10–15°) to avoid collisions. Stay >25 cm above ground when moving or rotating
- Never move with gripper near the ground
- Drop and restart plan if unsure or failed
"""
    )

# global instance
robot_config = RobotConfig()