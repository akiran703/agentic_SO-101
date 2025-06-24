import logging
import json
from typing import Dict, List, Optional, Tuple, Any 
import numpy as np
import math
import os

from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBus
from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig
from config import robot_config
import time
from camera_controller import CameraController
import traceback
from dataclasses import dataclass, field