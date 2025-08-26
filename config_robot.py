"""
Configuration for the robot controller. has some preset data to keep robot in default position
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Tuple,Any, Final
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

# Module-level constants
DEFAULT_ROBOT_TYPE: Final[str] = "so101" # "so100", "so101"
DEFAULT_SERIAL_PORT: Final[str] = "/dev/tty.usbmodem59090526531" # only for SO ARM


# Camera configuration constants
# Can also be different for different cameras, set it in lerobot_config
DEFAULT_CAMERA_FPS: Final[int] = 30
DEFAULT_CAMERA_WIDTH: Final[int] = 1920
DEFAULT_CAMERA_HEIGHT: Final[int] = 1080

@dataclass
class RobotConfig:
    
    # Camera configuration using lerobot format
    # hugging face has many robots so made it compitable with these robots "so100", "so101"
    lerobot_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "type": DEFAULT_ROBOT_TYPE,
            "port": DEFAULT_SERIAL_PORT,
            "cameras": {
                "wrist": OpenCVCameraConfig(
                    index_or_path=1,
                    fps=DEFAULT_CAMERA_FPS,
                    width=DEFAULT_CAMERA_WIDTH,
                    height=DEFAULT_CAMERA_HEIGHT,
                ),
                "top": OpenCVCameraConfig(
                    index_or_path=0,
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
            "gripper":       (0.0, 100.0, -31.0, 100.0),
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
            "1": { "gripper": 0, "wrist_roll": -3.0, "wrist_flex": 32.0, "elbow_flex": 29.0, "shoulder_lift": 58.0, "shoulder_pan": 89.0 },
            "2": { "gripper": 0, "wrist_roll": -6.0, "wrist_flex": 84.0, "elbow_flex": 114.0, "shoulder_lift": 103.0, "shoulder_pan": 92.0 },
            "3": { "gripper": 0, "wrist_roll": -35.0, "wrist_flex": 73.0, "elbow_flex": 92.0, "shoulder_lift": 111.6, "shoulder_pan": 88.0 },
            "4": { "gripper": 0, "wrist_roll": 20.0, "wrist_flex": 73.0, "elbow_flex": 99.0, "shoulder_lift": 103.0, "shoulder_pan": 99.0 },
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
-top: shows the robot and the environment

Robot is attached to the left side of a table. The dimensions of the table are the following: length is 100 cm and width is 60 cm.
The table has a grid that makes breaking the environment down easier. There are 15 squares in total. There are 3 rows and 5 columns. The dimensions of each grid is 20cm by 20 cm.
Items will generally be placed in the 3rd and 4th column. The robot is always in column one.

## TARGET IDENTIFICATION - DIMM Memory Modules:

**DIMM Visual Characteristics on Motherboard:**
- **Shape:** Long, narrow rectangular circuit board (~13cm length, ~3cm height)
- **Color:** Typically green, black, or blue PCB with metallic gold/silver contact pins
- **Mounting:** Inserted vertically into white/black DIMM slots with plastic clips on ends
- **Orientation:** Stands perpendicular to motherboard surface
- **Contact Pins:** Visible gold/silver metallic edge connectors along bottom
- **Labels:** Often has manufacturer stickers/text on the side facing up
- **Clips:** White or black plastic retention clips on both ends of slot
- **Notch:** Small notch/gap in contact pins prevents incorrect insertion

## DIMM SEATING INSPECTION PROTOCOL:

**If task requires checking if DIMM is properly seated, use the DIMM protocol tool

**After taking all 4 pictures, assess DIMM seating by checking:**
- Both retention clips are fully engaged and locked
- DIMM is flush and level in the slot
- No visible gaps between DIMM bottom and slot
- Contact pins are fully inserted (not visible above slot level)
- DIMM stands straight and perpendicular to motherboard
- No tilting or uneven insertion

## VISUAL PROXIMITY DETECTION - Use camera feedback to judge distances:

**APPROACH INDICATORS:**
- **Object Size:** Target appears larger in frame as you approach - use this as primary distance gauge
- **Detail Resolution:** Surface textures, edges become sharper and more defined when closer
- **Focus Quality:** Objects become clearer with better edge definition at optimal distance
- **Gripper Reference:** Compare object size to visible gripper fingers (8cm) for scale estimation

**DISTANCE ZONES with Visual Cues:**
- **Far (>15cm):** Object small in frame, minimal detail visible - safe for faster approach
- **Medium (5-15cm):** Object details emerging, gripper fingers visible for scale - moderate speed
- **Near (2-5cm):** Fine details clear, object fills significant portion of frame - slow precision movements
- **Grasp Zone (<2cm):** Maximum detail visible, object very large in frame - micro-adjustments only

**SAFETY VISUAL CHECKS:**
- If object suddenly grows much larger = collision risk, stop immediately  
- When object edges become very sharp and detailed = near contact
- Use gripper finger visibility as collision warning system

## MOVEMENT PROTOCOL:
- Move slowly and iteratively, checking visual feedback after each move
- Close gripper completely to grab objects
- Split into smaller steps and reanalyze visual feedback after each one
- Use only the latest images to evaluate success and distance
- Move above object with gripper tilted up (10–15°) to avoid collisions. Stay >25 cm above ground when moving or rotating
- Never move with gripper near the ground
- When object is inside gripper, it will not be visible and will cover the whole wrist camera view
- Drop and restart plan if visual feedback is unclear, inconsistent, or indicates failure
"""
    )

# global instance
robot_config = RobotConfig()