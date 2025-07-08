import logging
import json
from typing import Dict, List, Optional, Tuple, Any 
import numpy as np
import math
import os
import time

from lerobot.common.robots import Robot
from lerobot.common.robots.so100_follower import SO100Follower, SO100FollowerConfig
from lerobot.common.robots.so101_follower import SO101Follower, SO101FollowerConfig


from config_robot import robot_config
from only_kin import KinematicsM

import traceback
from dataclasses import dataclass, field


#-----------------------------------------------------------------------------------------------------------------------------#

# Configure logging only if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class output_movement:
    #typing hinting some variables
    warnings: List[str] = field(default_factory=list)
    robot_state: Dict[str, Any] = field(default_factory=dict)
    ok : bool
    msg: str
    
    def convert_to_json(self) -> dict:
        final_state_robot = self.robot_state
        if not final_state_robot:
            final_state_robot = {"error" : "robot not avaliable"}
        output_json = {}
        
        #this is to make sure we are not sending empty values to the calude model
        if not self.ok:
            output_json["status"]  = "error"
        if self.robot_state:
            output_json["robot_state"]  = self.robot_state
        if self.warnings:
            output_json["warning"]  = self.warnings
        if self.msg:
            output_json["message"] = self.msg
        
        
         # Single point of logging for the returned JSON
        logger.info(f"MoveResult JSON: {json.dumps(output_json)}")
        return output_json

class ControlRobot:
    #"store movement in a dictionary to create a high level controller to work in degress and per-joint limits"
    
    ROBOT_TYPES = {"so100_follower": (SO100Follower, SO100FollowerConfig),"so101_follower": (SO101Follower, SO101FollowerConfig)}
    
    #calling pre-defined values from the config_robot python file
   
    
    #constructor
    #param will be bool to make sure states are not being overriden
    def __init__(self,READ_ONLY: bool = False):
        #gets the robots 
        self.robot_type = robot_config.lerobot_config.get("type")
        self.robot = None
        self.read_only = READ_ONLY
        
        
        #pull values from the confg file
        #get motor mapping 
        self.motor_mapping = robot_config.motors_to_degrees
        #get joint 
        self.names_of_joint = List(self.motor_mapping.keys())
        #get presets
        self.presets = robot_config.PRESET_POSITIONS
        #for smooth interpolation
        self.movement_constant = robot_config.MOVEMENT_CONSTANTS
        
        #passing the dictionary from confg_robot to the KinematicsM class
        params_for_kin = robot_config.KINEMATIC_PARAMS.get(self.robot_type, robot_config.KINEMATIC_PARAMS['default'])
        self.kinematics = KinematicsM(param=params_for_kin)
        
        
        #positions in deg 
        self.position_deg = {n : 0.0 for n in self.names_of_joint}
        #position 
        self.position_norm = {n: 0.0 for n in self.names_of_joint}
        #set up cartesian
        self.cartesian_MM = {'x': 0.0, 'z': 0.0}
        
        
        if READ_ONLY:
            # In read-only mode, connect and disable torque for manual movement
            logger.info("Initializing in READ-ONLY mode")
            self._connect_robot_readonly()
            self._refresh_state()
        else:
            # Normal mode - full initialization
            self._connect_robot()
            self._refresh_state()

        logger.info(f"RobotController initialized. Type: {self.robot_type}, Read-only: {READ_ONLY}")

        
    def __enter__(self) -> 'ControlRobot':
        return self
    
    def __exit__(self,exc_type,exc_val,exc_tb) -> None:
        self.disconnect(reset_pos=True)
     
    #connect to robot   
    def _connect_robot(self) -> None:
        
        keys_to_not_include = ['type']
        
        if self.robot_type == 'lewiki':
            keys_to_not_include.append('port')
        else:
            keys_to_not_include.append('remote_ip')
            
        robot_params = {k: v for k, v in robot_config.lerobot_config.items() if k not in keys_to_not_include}
        
        
        #using lerobot factory create config
        try:
            robot_class, config_class = self.ROBOT_TYPES.get(self.robot_type, (None, None))
            if not robot_class:
                raise ValueError(f'Unsupported robot type: {self.robot_type}')
            new_cfg = config_class(**robot_params)
            self.robot = robot_class(new_cfg)
            self.robot.connect()
            logger.info(f'Connected to {self.robot_type}')
        except Exception as e:
            logger.error(f'cant connect to robot: {e}'  )
            raise
    
    #disable read only 
    def _read_only_mode(self) -> None:
        try:
            self._connect_robot
            
            if self.robot_type != 'lekiwi':
                self.robot.bus.disable_torque()
                logger.info(f'{self.robot_type} is in read only mode, torque is disabled')
            else:
                logger.info('you will have to manually disable for lewiki')
        except Exception as e:
            logger.error(f"can not _connect_robot failed so read only failed")
            raise  
    
    #degree to normalized values
    def degree_to_norm(self,joint_name,degrees) -> float:
        norm_min, norm_max, deg_min, deg_max = self.motor_mapping[joint_name]
        if deg_max == deg_min:
            return norm_min
        normalized_value = norm_min + ((degrees - deg_min) * (norm_max - norm_min)) / (deg_max - deg_min)
        return normalized_value
    
    #normalized values to degree
    def norm_to_deg(self,joint_name,normalized) -> float:
        norm_min, norm_max, deg_min, deg_max = self.motor_mapping[joint_name]
        if norm_max == norm_min:
            return deg_min
        degree_value = deg_min + ((normalized - norm_min) * (deg_max - deg_min)) / (norm_max - norm_min)
        return degree_value
        
    
    #check if the target postion is capable of being executed 
    def check_if_validate_range(self,pos_in_deg,) -> tuple[bool,str]:
        errors = []
        
        for joint_name, deg_value in pos_in_deg.items():
            if joint_name not in self.motor_mapping:
                continue
                
            norm_value = self.degree_to_norm(joint_name, deg_value)

            if joint_name == "gripper":
                norm_min, norm_max = 0, 100
            else:
                norm_min, norm_max = -100, 100
            
            # Handle inverted ranges (where norm_min > norm_max)
            actual_min = min(norm_min, norm_max)
            actual_max = max(norm_min, norm_max)
            
            if norm_value < actual_min or norm_value > actual_max:
                errors.append(
                    f"{joint_name.replace('_', ' ').title()} position {deg_value:.1f}° "
                    f"(normalized: {norm_value:.1f}) is outside valid range "
                    f"{actual_min:.1f} to {actual_max:.1f}"
                )

        if errors:
            return False, "Movement impossible - out of range: " + "; ".join(errors)
        
        return True, "No errors"
    
    #we store the moves we want to make in lerobot
    def build_and_store_action(self,pos_in_deg) -> Dict[str,float]:
        act = {}
        
        for n, d in pos_in_deg.items():
            norm_val = self.degree_to_norm(n, d)
            if self.robot_type == "lekiwi":
                pos_key = f"arm_{n}.pos" 
            else:
                f"{n}.pos"
            act[pos_key] = norm_val
        
        # Add base velocities for lekiwi
        if self.robot_type == "lekiwi":
            act.update({"x.vel": 0.0, "y.vel": 0.0, "theta.vel": 0.0})
        
        return act
        
    
    #refresh robot state
    def refresh_robot_state(self) -> None:
        if not self.robot:
            return
            
        try:
            observation = self.robot.get_observation()
            
            if self.robot_type == "lekiwi":
                # LeKiwi returns a state vector in observation.state
                if "observation.state" in observation:
                    state_vector = observation["observation.state"]
                    # State order: arm_shoulder_pan.pos, arm_shoulder_lift.pos, arm_elbow_flex.pos, 
                    #              arm_wrist_flex.pos, arm_wrist_roll.pos, arm_gripper.pos, x.vel, y.vel, theta.vel
                    state_order = [
                        "arm_shoulder_pan.pos", "arm_shoulder_lift.pos", "arm_elbow_flex.pos",
                        "arm_wrist_flex.pos", "arm_wrist_roll.pos", "arm_gripper.pos",
                        "x.vel", "y.vel", "theta.vel"
                    ]
                    
                    for i, joint_name in enumerate(self.names_of_joint):
                        pos_key = f"arm_{joint_name}.pos"
                        if i < len(state_vector) and pos_key in state_order:
                            idx = state_order.index(pos_key)
                            norm_val = float(state_vector[idx])
                            self.position_norm[joint_name] = norm_val
                            self.position_norm[joint_name] = self.norm_to_deg(joint_name, norm_val)
                else:
                    # Fallback: try direct observation keys
                    for joint_name in self.names_of_joint:
                        pos_key = f"arm_{joint_name}.pos"
                        if pos_key in observation:
                            norm_val = observation[pos_key]
                            self.position_norm[joint_name] = norm_val
                            self.position_norm[joint_name] = self.norm_to_deg(joint_name, norm_val)
            else:
                # SO100/SO101: direct observation keys
                for joint_name in self.names_of_joint:
                    pos_key = f"{joint_name}.pos"
                    if pos_key in observation:
                        norm_val = observation[pos_key]
                        self.position_norm[joint_name] = norm_val
                        self.position_norm[joint_name] = self.norm_to_deg(joint_name, norm_val)
            
            # Update cartesian coordinates
            fk_x, fk_z = self.kinematics.forward_kin(
                self.position_deg["shoulder_lift"],
                self.position_deg["elbow_flex"]
            )
            self.cartesian_MM = {"x": fk_x, "z": fk_z}
            
        except Exception as e:
            logger.error(f"Failed to read robot state: {e}", exc_info=True)
    
    
    
    
    #get the robot state in human readable state
    def read_robot_human_state(self) -> dict[str,float]:
        pos_deg = getattr(self,'position_deg', {name: 0.0 for name in getattr(self, 'name_of_joints', [])})
        car_mm = getattr(self, 'cartesian_MM', {"x": 0.0, "z": 0.0})
        human_robot_dict = {
            "robot_rotation_clockwise_deg": pos_deg.get("shoulder_pan", 0.0) - 90,
            "gripper_heights_mm": car_mm.get("z", 0.0),
            "gripper_linear_position_mm": car_mm.get("x", 0.0),
            "gripper_tilt_deg": (pos_deg.get("wrist_flex", 0.0) + pos_deg.get("shoulder_lift", 0.0) - pos_deg.get("elbow_flex", 0.0)),
            "gripper_rotation_deg": pos_deg.get("wrist_roll", 0.0),
            "gripper_openness_pct": pos_deg.get("gripper", 0.0),
        }
        return human_robot_dict
    
    #ensure all the states are valid
    def get_all_valid_state(self) -> dict[str,Any]:
        pos_deg = getattr(self,'position_deg', {})
        pos_norm = getattr(self,'position_norm', {})
        car_mm = getattr(self, 'cartesian_MM', {"x": 0.0, "z": 0.0})
        all_state_dict = {   "joint_positions_deg": {name: round(pos, 1) for name, pos in pos_deg.items()},
            "joint_positions_norm": {name: round(pos, 1) for name, pos in pos_norm.items()},
            "cartesian_mm": {name: round(pos, 1) for name, pos in car_mm.items()},
            "human_readable_state": {name: round(pos, 1) for name, pos in self.read_robot_human_state().items()}
        }
        return all_state_dict
    
    #get current robot state and pass it back to movement class
    def get_current_robot_state(self) -> output_movement:
        self.refresh_robot_state()
        return output_movement(True, "updating with the current state of the robot", robot_state=self.get_all_valid_state())
    
    #make sure the arm runs smoothly
    def execute_interpolated_move(self):
        if not self.robot:
            return output_movement(False, "Robot is not online", robot_state=self.get_all_valid_state())
    
        if self.read_only:
            return output_movement(False, "Robot in read-only mode", robot_state=self.get_all_valid_state())
        return  
    
    #set the joints to absolute position
    def set_joints_absolute(self, positions_deg, use_interpolation) -> output_movement:
        if not self.robot:
            return output_movement(False, "Robot is not online", robot_state=self.get_all_valid_state())
    
        if self.read_only:
            return output_movement(False, "Robot in read-only mode", robot_state=self.get_all_valid_state())
                
        # Filter valid joints
        v_pos = {name: pos for name, pos in positions_deg.items() if name in self.names_of_joint}
        if not v_pos:
            return output_movement(True, "No valid joints to move", robot_state=self.get_all_valid_state())

        # Validate that positions are within LeRobot's accepted ranges
        is_valid, error_msg = self.check_if_validate_range(v_pos)
        if not is_valid:
            return output_movement(False, error_msg, robot_state=self.get_all_valid_state())

        try:
            if use_interpolation == True:
                #have to create this func
                self.execute_interpolated_move(v_pos)
            else:
                action = self.build_and_store_action(v_pos)
                self.robot.send_action(action)
            
            # Update state optimistically
            self.position_deg.update(v_pos)
            for name, deg in v_pos.items():
                self.position_norm[name] = self.degree_to_norm(name, deg)
            
            # Update cartesian if needed
            if "shoulder_lift" in v_pos or "elbow_flex" in v_pos:
                fk_x, fk_z = self.kinematics.forward_kin(
                    self.position_deg["shoulder_lift"],
                    self.position_deg["elbow_flex"]
                )
                self.cartesian_mm = {"x": fk_x, "z": fk_z}

        except Exception as e:
            logger.error(f"Move failed: {e}", exc_info=True)
            self._refresh_state()
            return output_movement(False, f"Move failed: {e}", robot_state=self.get_all_valid_state())
        
        return output_movement(True, "Move completed", robot_state=self.get_all_valid_state())
    
        
    
        
        
        
        
         
    
    
    
        
            
            
        
        
    
    