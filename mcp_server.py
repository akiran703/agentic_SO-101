"""
MCP server that host interactive functions to the arm
"""

from __future__ import annotations

import time
import io
import logging
from typing import List, Optional, Union

import numpy as np
from PIL import Image as PILImage

from typing import Dict, Tuple,Any, Final
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP, Image

from controller_for_arm import RobotController
from config_robot import robot_config

import atexit
import traceback
import time


logging.basicConfig(level=logging.INFO, format="%(asctime)s MCP_Server %(levelname)s: %(message)s")
logger = logging.getLogger(__name__) # Use a named logger for MCP server specifics if any

#-----------------------------------------Initialise FastMCP server-------------------------------------


mcp = FastMCP(
    name="SO-ARM101 robot controller",
    port = 3001 # can use any other port
)

# -----------------------------------Helper functions-------------------------------------------



_robot: Optional[RobotController] = None

 #Convert a numpy RGB image to MCP image format
def _np_to_mcp_image(arr_rgb: np.ndarray) -> Image:
   
    pil_img = PILImage.fromarray(arr_rgb)
    with io.BytesIO() as buf:
        pil_img.save(buf, format="JPEG")
        raw_data = buf.getvalue()
    return Image(data=raw_data, format="jpeg")


#     Lazy-initialise the global RobotController instance.
#     We avoid creating the controller at import time so the MCP Inspector can
#     start even if the hardware is not connected. The first tool/resource call
#     that actually needs the robot will trigger the connection.
   

def get_robot() -> RobotController:
    global _robot
    if _robot is None:   
        try:
            _robot = RobotController()
            logger.info(f"RobotController initialized.")

        except Exception as e:
            logger.error(f"MCP: FATAL - Error initializing robot: {e}", exc_info=True)
            raise SystemExit(f"MCP Server cannot start: RobotController failed to initialize ({e})")
            
    return _robot


    # Combine robot state with camera images into a unified response format.
    # Returns a list containing:
    # 1. MCP images from all available cameras
    # 2. JSON with robot state and operation results

    # Args:
    #     result_json: The operation result in JSON format
    #     is_movement: If True, adds a small delay before capturing images to ensure they're current
    

def get_state_with_images(result_json: dict, is_movement: bool = False) -> List[Union[Image, dict, list]]:
    robot = get_robot()
    try:
        if is_movement:
            time.sleep(1.0)  # wait until the robot moved before capturing images
        
        raw_imgs = robot.get_camera_images()
        
        #adding another check to make sure images are being fed or not
        if not raw_imgs:
            logger.warning("MCP: No camera images returned from robot controller.")
            return [result_json, "Warning: No camera images available."]
        
        mcp_images = [_np_to_mcp_image(img) for img in raw_imgs.values()]
            
        # Keep only human_readable_state inside robot_state for clients
        result_json["robot_state"] = result_json["robot_state"]["human_readable_state"]

        # Return combined response
        return [result_json] + mcp_images
    except Exception as e:
        logger.error(f"Error getting camera images: {str(e)}")
        logger.error(traceback.format_exc())
        # If camera access fails, still return state with empty image list
        return [result_json] + ["Error getting camera images"]
    


#------------------------------------Functions to just arm data-----------------------------------------


# Can be resource instead but some clients support only tools
# @mcp.resource("robot://description")
@mcp.tool(description="Get a description of the robot and instructions for the user. Run it before using any other tool.")
def get_initial_instructions() -> str:
    
    return robot_config.robot_description


@mcp.tool(description="Get current robot state with images from all cameras. Returns list of objects: json with results of the move and current state of the robot and images from all cameras")
def get_robot_state():
    robot = get_robot()
    move_result = robot.get_current_robot_state()
    result_json = move_result.to_json()
    logger.info(f"MCP: get_robot_state outcome: {result_json.get("status", "success")}, Msg: {move_result.msg}")
    return get_state_with_images(result_json, is_movement=False)



#-----------------------------move to dimm inspection location-------------------------

@mcp.tool(description="Move to the predfined locations of dimms and take pictures.You can pass 1, 2, 3, or 4 as a string into the parameters to get different angles.")
def dimm_protocol(different_location):
    DIMM_LOC = {
            "1": { "gripper": 0, "wrist_roll": -22.0, "wrist_flex": 72.0, "elbow_flex": 135.0, "shoulder_lift": 144.0, "shoulder_pan": 103.0 },
            "2": { "gripper": 0, "wrist_roll": -23.0, "wrist_flex": 50.0, "elbow_flex": 80.0, "shoulder_lift": 101.0, "shoulder_pan": 83.0 },
            "3": { "gripper": 0, "wrist_roll": -3.0, "wrist_flex": -14.0, "elbow_flex": 0.0, "shoulder_lift": 61.0, "shoulder_pan": 94.0 },
            "4": { "gripper": 0, "wrist_roll": -3.0, "wrist_flex": 98.0, "elbow_flex": 145.0, "shoulder_lift": 134.0, "shoulder_pan": 88.0 },
        }

    robot = get_robot()
    move_result = robot.get_current_robot_state()
    result_json = move_result.to_json()
    different_location = str(different_location)
    robot.set_joints_absolute(DIMM_LOC[different_location])
    return get_state_with_images(result_json, is_movement=False)


@mcp.tool(description="Move to the predfined locations of dimms and take pictures.You can pass 1, 2, 3, or 4 as a string into the parameters to get different angles.")
def dimm_protocol(different_location):
    CPU_LOC = {
            "1": { 
        "gripper": 0, 
        "wrist_roll": -8.0, 
        "wrist_flex": 35.0, 
        "elbow_flex": 75.0, 
        "shoulder_lift": 105.0, 
        "shoulder_pan": 90.0 
    },
            "2": { 
        "gripper": 0, 
        "wrist_roll": -12.0, 
        "wrist_flex": 70.0, 
        "elbow_flex": 115.0, 
        "shoulder_lift": 130.0, 
        "shoulder_pan": 92.0 
    },
            "3": { 
        "gripper": 0, 
        "wrist_roll": -15.0, 
        "wrist_flex": 20.0, 
        "elbow_flex": 50.0, 
        "shoulder_lift": 85.0, 
        "shoulder_pan": 91.0 
    },
            "4": { 
        "gripper": 0, 
        "wrist_roll": -5.0, 
        "wrist_flex": 55.0, 
        "elbow_flex": 95.0, 
        "shoulder_lift": 115.0, 
        "shoulder_pan": 88.0 
    },
            "5": { 
        "gripper": 0, 
        "wrist_roll": -18.0, 
        "wrist_flex": 85.0, 
        "elbow_flex": 125.0, 
        "shoulder_lift": 135.0, 
        "shoulder_pan": 94.0 
    },
        }

    robot = get_robot()
    move_result = robot.get_current_robot_state()
    result_json = move_result.to_json()
    different_location = str(different_location)
    robot.set_joints_absolute(CPU_LOC[different_location])
    return get_state_with_images(result_json, is_movement=False)
    



#------------------------------------functions to move the arm------------------------------------------


@mcp.tool(
        description="""
        Move the robot with intuitive controls.
        Args:
            move_gripper_up_mm (float, optional): Distance to move gripper up (positive) or down (negative) in mm
            move_gripper_forward_mm (float, optional): Distance to move gripper forward (positive) or backward (negative) in mm
            tilt_gripper_down_angle (float, optional): Angle to tilt gripper down (positive) or up (negative) in degrees
            rotate_gripper_right_angle (float, optional): Angle to rotate gripper clockwise (positive) or counterclockwise (negative) in degrees
            rotate_robot_right_angle (float, optional): Angle to rotate entire robot clockwise/right (positive) or counterclockwise/left (negative) in degrees
        Expected input format:
        {
            "move_gripper_up_mm": "10", # Will move up 1 cm
            "move_gripper_forward_mm": "-5", # Will move backward 5 mm
            "tilt_gripper_down_angle": "10", # Will tilt gripper down 10 degrees
            "rotate_gripper_clockwise_angle": "-15", # Will rotate gripper counterclockwise 15 degrees
            "rotate_robot_right_angle": "15" # Will rotate robot clockwise (to the right) 15 degrees
        }
        Returns:
            list: List containing:
                - JSON object with:
                    - status: Optional status in case of error
                    - message: Optional message
                    - warnings: Optional list of any warnings
                    - robot_state: Current robot state in human readable format
                - Camera images
    """
        )
def move_robot(move_gripper_up_mm=None, move_gripper_forward_mm=None, tilt_gripper_down_angle=None, rotate_gripper_clockwise_angle=None, rotate_robot_right_angle=None):
    
    robot = get_robot()
    logger.info(f"MCP Tool: move_robot received: up={move_gripper_up_mm}, fwd={move_gripper_forward_mm}, "
                f"tilt={tilt_gripper_down_angle}, grip_rot={rotate_gripper_clockwise_angle}, "
                f"robot_rot={rotate_robot_right_angle}")

    # All parameters are optional for execute_intuitive_move
    # Convert MCP tool parameters to match the arguments of execute_intuitive_move
    move_params = {}
    move_params["move_gripper_up_mm"] = float(move_gripper_up_mm) if move_gripper_up_mm is not None else None
    move_params[ "move_gripper_forward_mm"] = float(move_gripper_forward_mm) if move_gripper_forward_mm is not None else None
    move_params["tilt_gripper_down_angle"] = float(tilt_gripper_down_angle) if tilt_gripper_down_angle is not None else None
    move_params["rotate_gripper_clockwise_angle"] = float(rotate_gripper_clockwise_angle) if rotate_gripper_clockwise_angle is not None else None
    move_params["rotate_robot_right_angle"]  = float(rotate_robot_right_angle) if rotate_robot_right_angle is not None else None
    
    
    # Filter out None values to pass only specified arguments to the robot controller method
    actual_move_params = {k: v for k, v in move_params.items() if v is not None}
    
    if not actual_move_params:
        current_state_result = robot.get_current_robot_state()
        result_json = current_state_result.to_json()
        result_json["message"] = "No movement parameters provided to move_robot tool."
        logger.info(f"MCP: move_robot outcome: {result_json.get('status', 'success')}, Msg: {result_json.get('message', '')}")
        return get_state_with_images(result_json, is_movement=False)

    move_execution_result = robot.execute_interpolated(**actual_move_params)
    result_json = move_execution_result.to_json()
    
    logger.info(f"MCP: move_robot final outcome: {result_json.get('status', 'success')}, Msg: {result_json.get('message', '')}, Warnings: {len(result_json.get('warnings', []))}")
    
    return get_state_with_images(result_json, is_movement=True)


@mcp.tool(description="Control the robot's gripper openness from 0% (completely closed) to 100% (completely open). Expected input format: {gripper_openness_pct: '50'}. Returns list of objects: json with results of the move and current state of the robot and images from all cameras")
def control_gripper(gripper_openness_pct):
    robot = get_robot()
    
    try:
        openness = float(gripper_openness_pct)
        logger.info(f"MCP Tool: control_gripper called with openness={gripper_openness_pct}%")
        
        move_result = robot.set_joints_absolute({'gripper': openness})
        result_json = move_result.to_json()
        logger.info(f"MCP: control_gripper outcome: {result_json.get('status', 'success')}, Msg: {move_result.msg}, Warnings: {len(move_result.warnings)}")
        return get_state_with_images(result_json, is_movement=True)
        
    except (ValueError, TypeError) as e:
        logger.error(f"MCP: control_gripper received invalid input: {gripper_openness_pct}, error: {str(e)}")
        return {"status": "error", "message": f"Invalid gripper openness value: {str(e)}"}


#------------------------------------shutdown------------------------------------------

#disconnect
def _cleanup():
   
    global _robot
    if _robot is not None:
        try:
            _robot.disconnect()
        except Exception as e_disc:
            logger.error(f"MCP: Exception during _robot.disconnect(): {e_disc}", exc_info=True)

atexit.register(_cleanup)

#-------------------------------------Main-----------------------------------------


if __name__ == "__main__":
    logger.info("Starting MCP Robot Server...")
    try:
        mcp.run()
    except SystemExit as e:
        logger.error(f"MCP Server failed to start: {e}")
    except Exception as e_main:
        logger.error(f"MCP Server CRITICAL RUNTIME ERROR: {e_main}", exc_info=True) 