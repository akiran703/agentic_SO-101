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
    "store movement in a dictionary to create a high level controller to work in degress and per-joint limits"
    
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
    def __init__(self,UGP):
        self.current_pos_deg = {}
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
        
        
        
            
            
        
        
    
    