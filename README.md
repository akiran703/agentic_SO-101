Contorl a robotic arm with a LLM

How we do this? We use a Model Context Protocol (MCP) as the bridge between the code that conrtols the robot arm ( SO-ARM101 and SO-ARM100) to the reasoning model that acts as the brain. Setting up a MCP server provides a standardized interface for robot control operations, allowing the reasoning model to interact with physical robotics hardware through natural language commands.




Features

Robot Arm Control: Direct control of servo motors and actuators
Camera Integration: Real-time video feed for visual feedback
Position Management: Precise control of arm positions and movements
Safety Features: Built-in safety limits and emergency stop functionality
Multiple Robot Support: Compatible with 2 robot arm models

Supported Hardware

SO-ARM100 Robot Arm
USB Serial connections
USB/IP cameras for visual feedback

Installation
Prerequisites

Python 3.8 or higher
USB serial drivers for your robot arm
Camera drivers (if using visual feedback)

Setup

Clone this repository:

bashgit clone https://github.com/yourusername/robot_mcp.git
cd robot_mcp

Install required dependencies:

bashpip install -r requirements.txt

Configure your robot connection by copying and editing the config file:

bashcp config.py.example config.py

Update config.py with your specific settings:

python# Serial port configuration
SERIAL_PORT = "/dev/ttyUSB0"  # Linux/Mac
# SERIAL_PORT = "COM3"        # Windows

# Camera configuration
CAMERA_INDEX = 0  # Usually 0 for built-in camera, 1+ for USB cameras

# Robot-specific settings
ROBOT_TYPE = "SO-ARM100"  
BAUD_RATE = 9600
Configuration
MCP Client Setup
Claude Desktop
Add the following to your Claude Desktop configuration file:
MacOS: ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%/Claude/claude_desktop_config.json
json{
  "mcpServers": {
    "robot-control": {
      "command": "python",
      "args": ["/path/to/robot_mcp/mcp_robot_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/robot_mcp"
      }
    }
  }
}

Usage
Once configured, you can interact with your robot through natural language in your AI assistant:
Example Commands:

"Move the robot arm to position (100, 50, 30)"
"Take a photo with the camera"
"Move joint 1 to 45 degrees"
"Return to home position"
"Show current arm status"

Available Tools
The MCP server exposes the following tools to AI agents:
move_arm
Move the robot arm to a specific position.

Parameters:

x, y, z (float): Target coordinates
speed (optional, int): Movement speed (1-100)



move_joint
Move a specific joint to a target angle.

Parameters:

joint_id (int): Joint number (1-6)
angle (float): Target angle in degrees



get_position
Get the current position of the robot arm.

Returns: Current x, y, z coordinates and joint angles

take_photo
Capture an image from the connected camera.

Returns: Base64 encoded image data

home_position
Move the robot arm to its home/default position.
emergency_stop
Immediately stop all robot movements.

DEMO
![me](https://github.com/akiran703/agentic_SO-101/blob/main/gif_folder/mcp_water_bottle-VEED.gif)

https://www.veed.io/view/d9f9d34b-ec5c-42a6-8fad-7d564420a668?panel=share


![me](https://github.com/akiran703/agentic_SO-101/blob/main/gif_folder/mcp_follow_hand-VEED.gif)

https://www.veed.io/view/eb4bd6ba-4cd2-4454-86e5-d58ef7778452?panel=share


![me](https://github.com/akiran703/agentic_SO-101/blob/main/gif_folder/no_cpu_mcp_detect-VEED.gif)



https://www.veed.io/view/ba0a4b59-265f-4119-94be-7ebabc89abd9?panel=share



Safety
⚠️ Important Safety Notes:

Always ensure the robot workspace is clear before issuing movement commands
Keep emergency stop accessible
Test movements manually before using AI control
Monitor the robot during AI-controlled operations
Respect joint limits and workspace boundaries

Troubleshooting
Connection Issues

Verify the correct serial port in config.py
Check that your robot is powered on and connected
Ensure proper USB drivers are installed

Camera Problems

Verify camera index in config.py
Test camera separately with system tools
Check camera permissions/access rights

MCP Server Not Starting

Verify Python path and dependencies
Check configuration file syntax
Review server logs for error messages


Development
Project Structure
robot_mcp/
├── mcp_robot_server.py    # Main MCP server implementation
├── robot_controller.py    # Robot control logic
├── camera_manager.py      # Camera handling
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
└── README.md            # This file
Contributing


License
This project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgments

Anthropic for the Model Context Protocol specification
Robot arm manufacturers for hardware documentation
The open-source robotics community



# Robot MCP Server

A Model Context Protocol (MCP) server for controlling robot arms through AI agents like Claude Desktop, Cursor, and Windsurf.

## Overview

This MCP server enables LLM-based AI agents to control robot arms such as the SO-ARM100 and LeKiwi models. The server provides a standardized interface for robot control operations, allowing AI assistants to interact with physical robotics hardware through natural language commands.

## Features

- **Robot Arm Control**: Direct control of servo motors and actuators
- **Camera Integration**: Real-time video feed for visual feedback
- **Position Management**: Precise control of arm positions and movements
- **Safety Features**: Built-in safety limits and emergency stop functionality
- **Multiple Robot Support**: Compatible with various robot arm models

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

3. Configure your robot connection by copying and editing the config file:
```bash
cp config.py.example config.py
```

4. Update `config.py` with your specific settings:
```python
# Serial port configuration
SERIAL_PORT = "/dev/ttyUSB0"  # Linux/Mac
# SERIAL_PORT = "COM3"        # Windows

# Camera configuration
CAMERA_INDEX = 0  # Usually 0 for built-in camera, 1+ for USB cameras

# Robot-specific settings
ROBOT_TYPE = "SO-ARM100"  # or "LeKiwi"
BAUD_RATE = 9600
```

## Configuration

### MCP Client Setup

#### Claude Desktop

Add the following to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "robot-control": {
      "command": "python",
      "args": ["/path/to/robot_mcp/mcp_robot_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/robot_mcp"
      }
    }
  }
}
```

#### Cursor/Windsurf

Add to your MCP configuration:

```json
{
  "robot-control": {
    "command": "python",
    "args": ["/path/to/robot_mcp/mcp_robot_server.py"]
  }
}
```

## Usage

Once configured, you can interact with your robot through natural language in your AI assistant:

**Example Commands:**
- "Move the robot arm to position (100, 50, 30)"
- "Take a photo with the camera"
- "Move joint 1 to 45 degrees"
- "Return to home position"
- "Show current arm status"

## Available Tools

The MCP server exposes the following tools to AI agents:

### `move_arm`
Move the robot arm to a specific position.
- **Parameters**: 
  - `x`, `y`, `z` (float): Target coordinates
  - `speed` (optional, int): Movement speed (1-100)

### `move_joint`
Move a specific joint to a target angle.
- **Parameters**:
  - `joint_id` (int): Joint number (1-6)
  - `angle` (float): Target angle in degrees

### `get_position`
Get the current position of the robot arm.
- **Returns**: Current x, y, z coordinates and joint angles

### `take_photo`
Capture an image from the connected camera.
- **Returns**: Base64 encoded image data

### `home_position`
Move the robot arm to its home/default position.

### `emergency_stop`
Immediately stop all robot movements.

## Safety

⚠️ **Important Safety Notes:**
- Always ensure the robot workspace is clear before issuing movement commands
- Keep emergency stop accessible
- Test movements manually before using AI control
- Monitor the robot during AI-controlled operations
- Respect joint limits and workspace boundaries

## Troubleshooting

### Connection Issues
- Verify the correct serial port in `config.py`
- Check that your robot is powered on and connected
- Ensure proper USB drivers are installed

### Camera Problems
- Verify camera index in `config.py`
- Test camera separately with system tools
- Check camera permissions/access rights

### MCP Server Not Starting
- Verify Python path and dependencies
- Check configuration file syntax
- Review server logs for error messages

## Development

### Project Structure
```
robot_mcp/
├── mcp_robot_server.py    # Main MCP server implementation
├── robot_controller.py    # Robot control logic
├── camera_manager.py      # Camera handling
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Anthropic](https://anthropic.com) for the Model Context Protocol specification
- Robot arm manufacturers for hardware documentation
- The open-source robotics community

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



