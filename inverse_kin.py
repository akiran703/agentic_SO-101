import logging
import json
from typing import Dict, List, Optional, Tuple, Any 
import numpy as np
import math
import os

from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBus
from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig
from config_robot import robot_config
import time
from camera_controller import CameraController
import traceback
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__) # Use a named logger

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
    
    #calling pre-defined values from the config_robot python file
    L1 = robot_config.L1
    L2 = robot_config.L2
    SL = robot_config.SPATIAL_LIMITS
    ODL = robot_config.OPERATIONAL_DEGREE_LIMITS 
    PP = robot_config.PRESET_POSITIONS
    BHMM = robot_config.BASE_HEIGHT_MM
    SMOMMR = math.asin(robot_config.SHOULDER_MOUNT_OFFSET_MM /L1)
    EMOMMR = math.asin(robot_config.ELBOW_MOUNT_OFFSET_MM/ L2)
    
    #constructor
    #UGP is updated goal position
    def __init__(self,UGP):
        self.current_pos_deg: Dict[str, float] = {}
        self.current_cart_mm = {"x": 0.0, "z": 0.0}
        self.motor_names = robot_config.motors.keys()
        
        bus_cfg = FeetechMotorsBusConfig(port=robot_config.port, motors=robot_config.motors,)
        self.motor_bus = FeetechMotorsBus(bus_cfg)
        self.motor_bus.connect()
        
        #try to open calibration file
        try:
            with open(robot_config.calibration_file, "r") as f:
                self.motor_bus.set_calibration(json.load(f))
        except:
            error_msg = f"Calibration file {robot_config.calibration_file} not found"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        self.reboot_robot_state_cache(UGP=UGP)
        
        #log of output 
        current_state_dict = self.get_current_robot_state().robot_state
        logging.info(f"RobotController initialized. State: {current_state_dict}")
        
        #setup camera
        self.camera_controller = CameraController(camera_configs=robot_config.cameras)
        self.camera_controller.connect()
        
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
        
            
            
        
        
    
    