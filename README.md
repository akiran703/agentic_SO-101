# Contorl a robotic arm with a reasoning model


## Overview

How we do this? We use a Model Context Protocol (MCP) as the bridge between the code that conrtols the robot arm ( SO-ARM101 and SO-ARM100) to the reasoning model that acts as the brain. Setting up a MCP server provides a standardized interface for robot control operations, allowing the reasoning model to interact with physical robotics hardware through natural language commands.

## Features

- **Robot Arm Control**: Direct control of servo motors and actuators
- **Camera Integration**: Real-time video feed for visual feedback
- **Position Management**: Precise control of arm positions and movements
- **Safety Features**: Built-in safety limits and emergency stop functionality
- **Multiple Robot Support**: Compatible with various robot arm models

## Demo

![me](https://github.com/akiran703/agentic_SO-101/blob/main/gif_folder/mcp_water_bottle-VEED.gif)

https://www.veed.io/view/d9f9d34b-ec5c-42a6-8fad-7d564420a668?panel=share


![me](https://github.com/akiran703/agentic_SO-101/blob/main/gif_folder/mcp_follow_hand-VEED.gif)

https://www.veed.io/view/eb4bd6ba-4cd2-4454-86e5-d58ef7778452?panel=share


![me](https://github.com/akiran703/agentic_SO-101/blob/main/gif_folder/no_cpu_mcp_detect-VEED.gif)


https://www.veed.io/view/ba0a4b59-265f-4119-94be-7ebabc89abd9?panel=share



## Supported Hardware

- SO-ARM100 Robot Arm
- LeKiwi Robot Arm
- USB Serial connections
- USB/IP cameras for visual feedback

## Installation

### Prerequisites

- Python 3.8 or higher
- USB serial drivers for your robot arm
- Camera drivers (if using visual feedback)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/robot_mcp.git
cd robot_mcp
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3.Update MOTOR_NORMALIZED_TO_DEGREE_MAPPING in config_robot.py to match your robot calibration. Run the const_check.py to make sure all motors are working by moving the arm freely. Follow the Hugging face doc page for calibration assitance: https://huggingface.co/docs/lerobot/so101 or https://huggingface.co/docs/lerobot/so100
```python
python check_positions.py
```
You can also you the keyboard.py to control the arm with a keyboard to catch any issues.
```python
python keyboard.py
```


4. Update `config_robot.py` with your specific settings:
```python
# Serial port configuration
SERIAL_PORT = "/dev/ttyUSB0"  # port of MOTOR BUS connected to the 

# Camera configuration( since i have two cameras, i labeled as so )
 lerobot_config: Dict[str, Any] = field(
        default_factory=lambda: {
            "type": DEFAULT_ROBOT_TYPE,
            "port": DEFAULT_SERIAL_PORT,
            "cameras": {
                "wrist": OpenCVCameraConfig(
                    index_or_path=1,
                    fps=DEFAULT_CAMERA_FPS,
                    width=DEFAULT_CAMERA_WIDTH,
                    height=DEFAULT_CAMERA_HEIGHT,
                ),
                "top": OpenCVCameraConfig(
                    index_or_path=0,
                    fps=DEFAULT_CAMERA_FPS,
                    width=DEFAULT_CAMERA_WIDTH,
                    height=DEFAULT_CAMERA_HEIGHT,
                ),
                
                
            },
        }
    )


# Robot-specific settings
ROBOT_TYPE = "SO-ARM101"  # or "SO-ARM100"
BAUD_RATE = 9600
```

## Configuration

# MCP Client Setup

### DEV MODE
Now you can try to control the robot manually using the keyboard. Test it before moving on to the MCP step, to make sure it works properly.
```Bash
mcp dev mcp_server.py
```

#### Claude Desktop

Add the following to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "SO-ARM101 robot controller": {
      "url": "http://127.0.0.1:3001/sse"
    }
  }
}
```


#Configuration for reasoning model
Create a .env file in the project root with your API keys:

### API Keys 
ANTHROPIC_API_KEY=your_anthropic_api_key_here

### MCP Server Configuration (optional)
MCP_SERVER_IP=127.0.0.1
MCP_PORT=3001


## Usage

# Start Server
```Bash
mcp run mcp_server.py --transport sse
```

#start reasoning model interface
```Python
python user_interface.py --thinking-budget 2048
```

Once configured, you can interact with your robot through natural language:

**Example Commands:**
- "Move the robot arm to position (100, 50, 30)"
- "Take a photo with the camera"
- "Move joint 1 to 45 degrees"
- "Return to home position"
- "Show current arm status"

## Available Tools

The MCP server has the following tools :

### `get_initial_instructions`
loads the prompt from the robot_config.py file


### `move_robot`
Move the robot arm to a specific position.
- **Parameters**: 
  - move_gripper_up_mm (float): move the gripper up by * mm
  - move_gripper_forward_mm (float): move the gripper forward by * mm
  - tilt_gripper_down_angle (float): move the gripper down by * mm
  - rotate_gripper_clockwise_angle (float): rotate the gripper  * degree counterclockwise
  - rotate_robot_right_angle (float): rotate the gripper * degree clockwise


### `control_gripper`
open the gripper 
- **Parameters**:
  - `‎gripper_openness_pct` (int): 0-100


### `dimm_protocol`
Moves the robot to a location near DIMMS and trys to understand if the DIMM is seated.



### `get_robot_state`
Get the current position of the robot arm and images of what the robot currently sees.
- **Returns**: data about the robot in json format




## Safety

⚠️ **Important Safety Notes:**
- Always ensure the robot workspace is clear before issuing movement commands
- Keep emergency stop accessible
- Test movements manually before using AI control
- Monitor the robot during AI-controlled operations
- Respect joint limits and workspace boundaries

## Troubleshooting

### Connection Issues
- Verify the correct serial port in `config_robot.py`
- Check that your robot is powered on and connected
- Ensure proper USB drivers are installed

### Camera Problems
- Verify camera index in `config_robot.py`
- Test camera separately with system tools
- Check camera permissions/access rights

### MCP Server Not Starting
- Verify Python path and dependencies
- Check configuration file syntax
- Review server logs for error messages



## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Anthropic](https://anthropic.com) for the Model Context Protocol specification
- [Hugging face](https://huggingface.co/docs/lerobot/so101) for intructions to build and configure the robot
- [ilia](youtube.com/watch?v=EmpQQd7jRqs&feature=youtu.be) for the inspiration of the project 

## Related Projects

- [MCP Specification](https://github.com/anthropics/mcp) - Official MCP documentation
- [Claude Desktop](https://claude.ai) - AI assistant with MCP support
- [Other MCP Servers](https://github.com/topics/mcp-server) - Community MCP implementations

## Support

For questions and support:
- Open an issue on GitHub
- Check the [MCP documentation](https://github.com/anthropics/mcp)
- Review robot arm manuals for hardware-specific questions

---

**Note**: This is experimental software. Use at your own risk and always prioritize safety when working with robotic hardware.



