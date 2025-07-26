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
    def get_full_state(self) -> Dict[str, Any]:
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

     #get current robot state and pass it back to movement class
    def get_current_robot_state(self) -> MoveResult:
        self.refresh_state()
        return MoveResult(True, "Current robot state retrieved.", robot_state=self.get_full_state())

    #set points absolute 
    def set_joints_absolute(self, positions_deg: Dict[str, float], use_interpolation: bool = True) -> MoveResult:
        if self.read_only:
            return MoveResult(False, "Arm in read-only mode", robot_state=self.get_full_state())
            
        if not self.robot:
            return MoveResult(False, "Arm not connected", robot_state=self.get_full_state())
        
        # Filter valid joints
        valid_positions = {}
        for name, pos in positions_deg.items():
            if name in self.names_of_joint:
                valid_positions[name] = pos
            
        
        if not valid_positions:
            return MoveResult(True, "No valid joints to move", robot_state=self.get_full_state())

        # Validate that positions are within LeRobot's accepted ranges
        is_valid, error_msg = self.check_if_valid_position(valid_positions)
        if not is_valid:
            return MoveResult(False, error_msg, robot_state=self.get_full_state())

        try:
            if use_interpolation:
                self.interpolated_movement(valid_positions)
            else:
                action = self.build_and_store_action(valid_positions)
                self.robot.send_action(action)
            
            # Update state optimistically
            self.positions_deg.update(valid_positions)
            for name, deg in valid_positions.items():
                self.positions_norm[name] = self.degree_to_norm(name, deg)
            
            # Update cartesian if needed
            if "shoulder_lift" in valid_positions or "elbow_flex" in valid_positions:
                fk_x, fk_z = self.kinematics.forward_kin(self.positions_deg["shoulder_lift"],self.positions_deg["elbow_flex"])
                self.cartesian_mm = {"x": fk_x, "z": fk_z}

        except Exception as e:
            logger.error(f"Move failed: {e}", exc_info=True)
            self.refresh_state()
            return MoveResult(False, f"Move failed: {e}", robot_state=self.get_full_state())
        
        return MoveResult(True, "Move completed", robot_state=self.get_full_state())

     #make sure movements are smooth
    def interpolated_movement(self, target_positions: Dict[str, float]) -> None:
        if self.read_only:
            raise RuntimeError("Arm is in read-only mode")
            
        if not self.robot:
            raise RuntimeError("Arm not connected")
            
        start_positions = {}
        for name in target_positions.keys():
            start_positions[name] = self.positions_deg[name]
        
        max_change = max(abs(target_positions[name] - start_positions[name]) for name in target_positions.keys())
        steps = max(1, min(
            self.movement_constant["MAX_INTERPOLATION_STEPS"],
            int(max_change / self.movement_constant["DEGREES_PER_STEP"])
        ))
       
        
        steps = max(1, min(self.movement_constant["MAX_INTERPOLATION_STEPS"],int(max_change / self.movement_constant["DEGREES_PER_STEP"])))
        
        interpolated = {}
        for i in range(1, steps + 1):
            for name in target_positions.keys():
                interpolated[name] = start_positions[name] + (target_positions[name] - start_positions[name]) * (i / steps)
               
            
            # Validate each interpolation step to avoid sending invalid commands
            is_valid, error_msg = self.check_if_valid_position(interpolated)
            if not is_valid:
                logger.warning(f"Interpolation step {i}/{steps} would exceed range limits, stopping interpolation")
                break
                
            action = self.build_and_store_action(interpolated)
            self.robot.send_action(action)
            time.sleep(self.movement_constant["STEP_DELAY_SECONDS"])

    #increase the joints by delta 
    def increment_joints_by_delta(self, deltas_deg: Dict[str, float]) -> MoveResult:
        if self.read_only:
            return MoveResult(False, "Cannot move arm in read-only mode", robot_state=self.get_full_state())
            
        target_positions = {}
        warnings = []
        
        for joint_name, delta in deltas_deg.items():
            if joint_name not in self.names_of_joint:
                warnings.append(f"Unknown joint '{joint_name}' ignored.")
                continue
            target_positions[joint_name] = self.positions_deg[joint_name] + delta
        
        if not target_positions:
            return MoveResult(False, "No valid joints for increment.", warnings, self.get_full_state())
        
        result = self.set_joints_absolute(target_positions)
        result.warnings.extend(warnings)
        return result

    
    #execute
    def execute_interpolated(self,move_gripper_up_mm: Optional[float] = None,move_gripper_forward_mm: Optional[float] = None,
        tilt_gripper_down_angle: Optional[float] = None, rotate_gripper_clockwise_angle: Optional[float] = None,
        rotate_robot_right_angle: Optional[float] = None,use_interpolation: bool = True) -> MoveResult:
        
        if self.read_only:
            return MoveResult(False, "Cannot move robot in read-only mode", robot_state=self.get_full_state())
            
        target_positions = self.positions_deg.copy()
        
        # Handle cartesian movements
        if move_gripper_up_mm is not None or move_gripper_forward_mm is not None:
            target_x = self.cartesian_mm["x"] + (move_gripper_forward_mm or 0.0)
            target_z = self.cartesian_mm["z"] + (move_gripper_up_mm or 0.0)
            
            # Validate target
            is_valid, msg = self.kinematics.is_valid_target_cart(target_x, target_z)
            if not is_valid:
                return MoveResult(False, f"Invalid target: {msg}", robot_state=self.get_full_state())
            
            try:
                sl_target, ef_target = self.kinematics.inverse_kin(target_x, target_z)
                target_positions["shoulder_lift"] = sl_target
                target_positions["elbow_flex"] = ef_target
                
                # Wrist compensation
                sl_change = sl_target - self.positions_deg["shoulder_lift"]
                ef_change = ef_target - self.positions_deg["elbow_flex"]
                target_positions["wrist_flex"] = self.positions_deg["wrist_flex"] - (sl_change - ef_change)
                
            except Exception as e:
                return MoveResult(False, f"Kinematics error: {e}", robot_state=self.get_full_state())
        
        # Handle direct joint movements
        if tilt_gripper_down_angle is not None:
            target_positions["wrist_flex"] += tilt_gripper_down_angle
        if rotate_gripper_clockwise_angle is not None:
            target_positions["wrist_roll"] += rotate_gripper_clockwise_angle
        if rotate_robot_right_angle is not None:
            target_positions["shoulder_pan"] += rotate_robot_right_angle
        
        return self.set_joints_absolute(target_positions, use_interpolation)
    
    
    #use a preset position 
    def apply_named_preset(self, preset_key: str) -> MoveResult:
        if self.read_only:
            return MoveResult(False, "Cannot move robot in read-only mode", robot_state=self.get_full_state())
            
        if preset_key not in self.presets:
            return MoveResult(False, f"Unknown preset: '{preset_key}'", robot_state=self.get_full_state())
        
        preset_positions = self.presets[preset_key]
        logger.info(f"Applying preset '{preset_key}': {preset_positions}")
        return self.set_joints_absolute(preset_positions)
    
    #takes a picture based when observing 
    def get_camera_images(self) -> Dict[str, np.ndarray]:
        if not self.robot:
            return {}
            
        try:
            observation = self.robot.get_observation()
            camera_images = {}
            
         
            # SO100/SO101: direct camera names as numpy arrays
            camera_names = list(robot_config.lerobot_config.get("cameras", {}).keys())
            camera_images = {}
            for key, value in observation.items():
                camera_name = key.replace("observation.images.", "")
                
                if camera_name in camera_names and isinstance(value, np.ndarray) and value.ndim == 3:
                    camera_images[camera_name] = value
                
                elif key in camera_names and isinstance(value, np.ndarray) and value.ndim == 3:
                    camera_images[key] = value
            
            return camera_images
        except Exception as e:
            logger.error(f"Error getting camera images: {e}", exc_info=True)
            return {}

    #disconnect
    def disconnect(self, reset_pos: bool = True) -> None:
        if not self.robot:
            return
            
        logger.info("Disconnecting robot...")
        
        # Don't move to rest position in read-only mode
        if reset_pos and not self.read_only:
            try:
                result = self.apply_named_preset("1")
                if not result.ok:
                    logger.warning(f"Rest position failed: {result.msg}")
            except Exception as e:
                logger.error(f"Error during rest position: {e}", exc_info=True)
        elif reset_pos and self.read_only:
            logger.info("Skipping rest position in read-only mode")
        
        try:
            self.robot.disconnect()
            logger.info("Robot disconnected successfully")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
        finally:
            self.robot = None