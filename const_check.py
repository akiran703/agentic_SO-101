import sys
import time
import logging
from controller_for_arm import ControlRobot
from config_robot import RobotConfig
import os


# Configure logging only if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


# clear terminal 
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')



#
def main():
    return 1


if __name__ == "__main__":
    sys.exit(main()) 