import logging
import json
from typing import Dict, List, Optional, Any
import numpy as np
from dataclasses import dataclass, field
import time
from lerobot.robots import Robot
from lerobot.robots.so100_follower import SO100Follower, SO100FollowerConfig
from lerobot.robots.so101_follower import SO101Follower, SO101FollowerConfig
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig

#---------------------------written classes------------------
from config_robot import robot_config
from only_kin import KinematicsM

# Configure logging only if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)



#----------------------------------------------------------------------------------------
@dataclass
class MoveResult:
   #typing hinting some variables
    ok: bool
    msg: str
    warnings: List[str] = field(default_factory=list)
    robot_state: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        json_output: Dict[str, Any] = {
            "robot_state": self.robot_state or {"error": "Robot state not available."}
        }
        if not self.ok:
            json_output["status"] = "error"
        if self.msg:
            json_output["message"] = self.msg
        if self.warnings:
            json_output["warnings"] = self.warnings

        # Single point of logging for the returned JSON
        logger.info(f"MoveResult JSON: {json.dumps(json_output)}")
        return json_output

class RobotController:
    # Robot type mapping
    ROBOT_TYPES = {"so100": (SO100Follower, SO100FollowerConfig),"so101": (SO101Follower, SO101FollowerConfig),"lekiwi": (LeKiwiClient, LeKiwiClientConfig),}

    def __init__(self, read_only: bool = False):
        self.robot_type = robot_config.lerobot_config.get("type")
        self.robot: Optional[Robot] = None
        self.read_only = read_only
        
        
        #pull values from the confg file
        #get motor mapping 
        self.motor_mapping = robot_config.MOTOR_NORMALIZED_TO_DEGREE_MAPPING
        #get joint 
        self.names_of_joint = list(self.motor_mapping.keys())
        #get presets
        self.presets = robot_config.PRESET_POSITIONS
        #for smooth interpolation
        self.movement_constant = robot_config.MOVEMENT_CONSTANTS
        
        # Initialize kinematics
        kinematic_params = robot_config.KINEMATIC_PARAMS.get(
            self.robot_type, robot_config.KINEMATIC_PARAMS["default"]
        )
        self.kinematics = KinematicsM(param=kinematic_params)
        
        #positions in deg 
        self.positions_deg: Dict[str, float] = {}
        for name in self.names_of_joint:
            self.positions_deg[name] = 0.0
        #position
        self.positions_norm: Dict[str, float] = {}
        for name in self.names_of_joint:
             self.positions_norm[name]= 0.0 
        #set up cartesian
        self.cartesian_mm: Dict[str, float] = {"x": 0.0, "z": 0.0}
        
        
                
        if read_only:
            # In read-only mode, connect and disable torque for manual movement
            logger.info("Initializing in READ-ONLY mode")
            self.connect_and_readonly()
            self.refresh_state()
        else:
            # Normal mode - full initialization
            self.connect_robot()
            self.refresh_state()

        logger.info(f"RobotController initialized. Type: {self.robot_type}, Read-only: {read_only}")

    def __enter__(self) -> 'RobotController':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect(reset_pos=True)
    
     #connect to robot   
    def connect_robot(self) -> None:
        keys_to_exclude = ["type"]

        if self.robot_type == "lekiwi":
            keys_to_exclude.append("port")
        else:
            keys_to_exclude.append("remote_ip")

        robot_params = {}
        for k, v in robot_config.lerobot_config.items():
            if k not in keys_to_exclude:
                robot_params[k] = v
        
         #using lerobot factory create config
        try:
            robot_class, config_class = self.ROBOT_TYPES.get(self.robot_type, (None, None))
            if not robot_class:
                raise ValueError(f"Unsupported robot type: '{self.robot_type}'")
            
            cfg = config_class(**robot_params)
            self.robot = robot_class(cfg)
            self.robot.connect()
            logger.info(f"Connected to {self.robot_type}")
        except Exception as e:
            logger.error(f"Failed to connect to robot: {e}")
            raise
    
    #disabled torque and reads metrics of arm       
    def connect_and_readonly(self) -> None:
        try:
            self.connect_robot()

            if self.robot_type != "lekiwi":
                self.robot.bus.disable_torque()
                logger.info(f"Connected to {self.robot_type} in READ-ONLY mode 🔓 TORQUE DISABLED: Robot can now be moved manually while monitoring positions")      
            else:
                logger.warning("LeKiwi is not supported")
        except Exception as e:
            logger.error(f"Failed to connect to robot in read-only mode womp womp: {e}")
            raise
    
    #disabled torque and reads metrics of arm       
    def connect_and_readonly(self) -> None:
        try:
            self.connect_robot()

            if self.robot_type != "lekiwi":
                self.robot.bus.disable_torque()
                logger.info(f"Connected to {self.robot_type} in READ-ONLY mode 🔓 TORQUE DISABLED: Robot can now be moved manually while monitoring positions")      
            else:
                logger.warning("LeKiwi is not supported")
        except Exception as e:
            logger.error(f"Failed to connect to robot in read-only mode womp womp: {e}")
            raise
    
    #degree to normalized values
    def degree_to_norm(self, joint_name: str, degrees: float) -> float:
        norm_min, norm_max, deg_min, deg_max = self.motor_mapping[joint_name]
        if deg_max == deg_min:
            return norm_min
        ans = norm_min + ((degrees - deg_min) * (norm_max - norm_min)) / (deg_max - deg_min)
        return ans

    #normalized values to degree
    def norm_to_deg(self, joint_name: str, normalized: float) -> float:
        """Convert normalized value to degrees."""
        norm_min, norm_max, deg_min, deg_max = self.motor_mapping[joint_name]
        if norm_max == norm_min:
            return deg_min
        degree_value = deg_min + ((normalized - norm_min) * (deg_max - deg_min)) / (norm_max - norm_min)
        return degree_value

    #check if the target postion is capable of being executed 
    def check_if_valid_position(self, positions_deg: Dict[str, float]) -> tuple[bool, str]:
    
        errors = []
        
        for jn, dv in positions_deg.items():
            if jn not in self.motor_mapping:
                continue
                
            norm_value = self.degree_to_norm(jn, dv)

            if jn == "gripper":
                norm_min, norm_max = 0, 100
            else:
                norm_min, norm_max = -100, 100
            
            # Handle inverted ranges (where norm_min > norm_max)
            actual_min = min(norm_min, norm_max)
            actual_max = max(norm_min, norm_max)
            
            if norm_value < actual_min or norm_value > actual_max:
                errors.append(f"{jn.replace('_', ' ').title()} position {dv:.1f}° " f"(normalized: {norm_value:.1f}) is outside valid range "f"{actual_min:.1f} to {actual_max:.1f}")
        
        if errors:
            return False, "Movement impossible - out of range: " + "; ".join(errors)
        
        return True, ""
    
    #we store the moves we want to make in lerobot
    def build_and_store_action(self, positions_deg: Dict[str, float]) -> Dict[str, float]:
        action = {}
        
        for name, deg in positions_deg.items():
            norm_val = self.degree_to_norm(name, deg)
            pos_key = f"{name}.pos"
            action[pos_key] = norm_val
                
        return action

    #refresh robot state
    def refresh_state(self) -> None:
        if not self.robot:
            return
            
        try:
            observation = self.robot.get_observation()
        
            # SO100/SO101: direct observation keys
            for joint_name in self.names_of_joint:
                    pos_key = f"{joint_name}.pos"
                    if pos_key in observation:
                        norm_val = observation[pos_key]
                        self.positions_norm[joint_name] = norm_val
                        self.positions_deg[joint_name] = self.norm_to_deg(joint_name, norm_val)
            
            # Update cartesian coordinates
            fk_x, fk_z = self.kinematics.forward_kin(self.positions_deg["shoulder_lift"],self.positions_deg["elbow_flex"])
            
            self.cartesian_mm = {"x": fk_x, "z": fk_z}
            
        except Exception as e:
            logger.error(f"Failed to read robot state: {e}", exc_info=True)

    #get the robot state in human readable state
    def convert_to_human_readable(self) -> Dict[str, float]:
        positions_deg = getattr(self, 'positions_deg', {name: 0.0 for name in getattr(self, 'names_of_joint', [])})
        cartesian_mm = getattr(self, 'cartesian_mm', {"x": 0.0, "z": 0.0})
        ans = {}
        
        ans['robot_rotation_clockwise_deg'] = positions_deg.get("shoulder_pan", 0.0) - 90
        ans['gripper_heights_mm'] = cartesian_mm.get("z", 0.0)
        ans['gripper_linear_position_mm'] = cartesian_mm.get("x", 0.0)
        ans['gripper_tilt_deg'] = positions_deg.get("wrist_flex", 0.0)+ positions_deg.get("shoulder_lift", 0.0) -  positions_deg.get("elbow_flex", 0.0)
        ans['gripper_rotation_deg'] = positions_deg.get("wrist_roll", 0.0)
        ans['gripper_openness_pct'] = positions_deg.get("gripper", 0.0)
        
        return ans

    #ensure all the states are valid
    def _get_full_state(self) -> Dict[str, Any]:
        # Ensure all state dictionaries exist
        positions_deg = getattr(self, 'positions_deg', {})
        positions_norm = getattr(self, 'positions_norm', {})
        cartesian_mm = getattr(self, 'cartesian_mm', {"x": 0.0, "z": 0.0})
        
        ans = {}
        jpddict = {}
        jpndict = {}
        catdict = {}
        hrsdict = {}
        
        for name, pos in positions_deg.items():
            jpddict[name] = round(pos, 1)
        
        for name, pos in positions_norm.items():
            jpndict[name] = round(pos, 1)
        
        for name, pos in cartesian_mm.items():
            catdict[name] = round(pos, 1)
            
        for name, pos in self.convert_to_human_readable().items():
            hrsdict[name] = round(pos, 1)
        
        ans["joint_positions_deg"] = jpddict
        ans["joint_positions_norm"] = jpndict
        ans["cartesian_mm"] = catdict
        ans["human_readable_state"] = hrsdict
        

        return ans