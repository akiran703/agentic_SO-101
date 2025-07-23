from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import os
import sys
import argparse
from typing import Dict, List, Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from llm_providers.factory import create_llm_provider

try:
    from agent_utils import ImageViewer
    IMAGE_VIEWER_AVAILABLE = True
except ImportError:
    IMAGE_VIEWER_AVAILABLE = False

#creating a AI agent with a system prompt 
class AIAgent:

    def __init__(self, model: str = "claude-3-7-sonnet-latest", show_images: bool = False, mcp_server_ip: str = "127.0.0.1", mcp_port: int = 3001,thinking_budget: int = 1024, thinking_every_n: int = 1,api_key: str = None):
        self.model = model
        self.mcp_url = f"http://{mcp_server_ip}:{mcp_port}/sse"
        self.thinking_budget = thinking_budget
        self.thinking_every_n = thinking_every_n
        self.conversation_history = []
        self.tools = []
        self.session = None
        
        self.llm_provider = create_llm_provider(model, api_key)
        
        self.show_images = show_images and IMAGE_VIEWER_AVAILABLE
        self.image_viewer = ImageViewer() if self.show_images else None
        
        if show_images and not IMAGE_VIEWER_AVAILABLE:
            print("⚠️  Image display requested but agent_utils.py not available")