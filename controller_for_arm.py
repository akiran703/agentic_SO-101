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
from config import robot_config
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
        
        # State tracking
        self.positions_deg: Dict[str, float] = {name: 0.0 for name in self.names_of_joint}
        self.positions_norm: Dict[str, float] = {name: 0.0 for name in self.names_of_joint}
        self.cartesian_mm: Dict[str, float] = {"x": 0.0, "z": 0.0}
        
        if read_only:
            # In read-only mode, connect and disable torque for manual movement
            logger.info("Initializing in READ-ONLY mode")
            self._connect_robot_readonly()
            self._refresh_state()
        else:
            # Normal mode - full initialization
            self._connect_robot()
            self._refresh_state()

        logger.info(f"RobotController initialized. Type: {self.robot_type}, Read-only: {read_only}")

    def __enter__(self) -> 'RobotController':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect(reset_pos=True)