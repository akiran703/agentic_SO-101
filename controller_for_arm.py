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
    #UGP is updated goal position
    def __init__(self,UGP):
        robot_config.KINEMATIC_PARAMS.get()
        
        
        
        
    def dictionary_returns_robot_state(self) -> Dict[str,Any]:
        #"we return a dictonary with the following values: raw motor angles,cartesian position,human readable state for LLM"
        
        #robot current state
        rcs = {}
        rcs['robot_rotation_clockwise_deg'] = self.current_pos_deg['shoulder_pan'] - 90
        rcs['gripper_heights_mm'] = self.current_cart_mm['z']
        rcs['gripper_linear_position_mm'] = self.current_cart_mm['x']
        
        #shoulder lift degree
        sld = self.current_pos_deg['shoulder_lift']
        #elbow flex deg
        efd = self.current_pos_deg['elbow_flex']
        #wrist flex deg
        wfd = self.current_pos_deg['wrist_flex']
        
        #gripper tilt val
        gtv = sld + wfd - efd
        rcs['gripper_tilt_deg'] = gtv
        rcs['gripper_rotation_deg'] = self.current_cart_deg['wrist_roll']                
        rcs['gripper_openness_pct'] = self.current_pos_deg['gripper']
        
        #formatted dict with robot arm data
        final_dict_robot_state = {}
        
        final_dict_robot_state['joint_positions_deg'] = {n: round(pos, 1) for n,pos in self.current_pos_deg.items()}
        final_dict_robot_state['cartesian_mm'] = {n: round(pos, 1) for n,pos in self.current_cart_mm.items()}
        final_dict_robot_state['human_readable_state'] = {n: round(pos, 1) for n,pos in rcs.items()}
        
        return final_dict_robot_state
    
    
    def reboot_robot_state_cache(self,UGP=False):
        #"calculate the forward kinematics,read joints, and update cache"
        temp_pos = {}
        
        try:
            rv = self.motor_bus.read("Present_Position",self.motor_names)
            for i,n in enumerate(self.motor_names):
                temp_pos[n] = float(np.asarray(rv[i]).flatten()[0])
        except Exception as e:
            logging.error(f"Failed to read motors positions ({e})")
            return
            
        self.current_pos_deg = temp_pos
        
        #use forward kinematics to update cartesian coord
        fk_x,fk_z = self.forward_kinematics(self.current_pos_deg["shoulder_lift"],self.current_pos_deg["elbow_flex"])
        
        if UGP:
            try:
                goals = [self.current_pos_deg[n] for n in self.motor_names]
                self.motor_bus.write("Goal_Position", goals, self.motor_names)
            except Exception as e_goal:
                logging.error(f"Could not update the goal position on hardware : {e_goal}")
        
        return
    
    
    
        
            
            
        
        
    
    