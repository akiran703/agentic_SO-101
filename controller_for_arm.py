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
    
    def norm_to_deg(self,joint_name,normalized) -> float:
        norm_min, norm_max, deg_min, deg_max = self.motor_mapping[joint_name]
        if norm_max == norm_min:
            return deg_min
        degree_value = deg_min + ((normalized - norm_min) * (deg_max - deg_min)) / (norm_max - norm_min)
        return degree_value
        
    
    
        
        
        
        
         
    
    
    
        
            
            
        
        
    
    