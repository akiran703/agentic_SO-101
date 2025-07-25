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
    
    #run the mcp tool           
    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        
        if not self.session:
            return [{"type": "text", "text": "Error: Not connected to MCP server"}]

        try:
            result = await self.session.call_tool(tool_name, arguments)
            content_parts = []
            image_count = 0

            if hasattr(result.content, '__iter__') and not isinstance(result.content, (str, bytes)):
                for item in result.content:
                    if hasattr(item, 'data') and hasattr(item, 'mimeType'):
                        image_count += 1
                        content_parts.append(
                        {
                            "type": "image",
                            "source": 
                            {
                                "type": "base64",
                                "media_type": item.mimeType,
                                "data": item.data
                            }
                        })
                    elif hasattr(item, 'text'):
                        content_parts.append({"type": "text", "text": item.text})
                    else:
                        content_parts.append({"type": "text", "text": str(item)})
            else:
                content_parts.append({"type": "text", "text": str(result.content)})

            print(f"🔧 {tool_name}: returned {f'{image_count} images + ' if image_count else ''}text")
            return content_parts

        except Exception as e:
            print(f"❌ Error executing {tool_name}: {str(e)}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    
    #clean up 
    def cleanup(self):
        if self.image_viewer:
            self.image_viewer.cleanup()

    #running cmd line interface
    async def run_cli(self):
        print(f"\n🤖 AI Agent with {self.llm_provider.provider_name}")
        print("=" * 50)
        print("Connecting to MCP server...")

        try:
            async with sse_client(self.mcp_url) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()
                    tools_response = await session.list_tools()
                    self.tools = [tool.model_dump() for tool in tools_response.tools]
                    
                    print("✅ Connected to MCP server")
                    print(f"Available tools: {', '.join(tool['name'] for tool in self.tools)}")
                    print("\nType your instructions or 'quit' to exit.")

                    while True:
                        user_input = input("\n> ").strip()
                        if not user_input:
                            continue
                        if user_input.lower() in ['quit', 'exit']:
                            print("Goodbye!")
                            break

                        print("🤔 Processing...")
                        response_text = await self.process_with_llm(user_input)
                        if not response_text or len(response_text.strip()) == 0:
                            print(f"\n✅ Task completed")

        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            print(f"Make sure the MCP server is running at {self.mcp_url}")
        finally:
            self.cleanup()
