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
from llm_provider.factory import create_llm_provider


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
    def _filter_images_from_conversation(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove images from conversation to prevent token accumulation."""
        filtered_conversation = []
        for msg in conversation:
            if isinstance(msg.get('content'), list):
                filtered_content = [
                    content for content in msg['content'] 
                    if not (isinstance(content, dict) and content.get('type') in ['image', 'image_url'])
                ]
                if filtered_content:
                    if len(filtered_content) == 1 and filtered_content[0].get('type') == 'text':
                        filtered_conversation.append({
                            "role": msg["role"],
                            "content": filtered_content[0].get('text', '')
                        })
                    else:
                        filtered_conversation.append({
                            "role": msg["role"],
                            "content": filtered_content
                        })
            else:
                filtered_conversation.append(msg)
        return filtered_conversation

    async def process_with_llm(self, user_input: str) -> str:
        """Process user input with LLM with full agent logic."""
        system_prompt = """You are an AI assistant with access to tools. 
        Use them as needed to control a robot and complete tasks.
        You can request more instruction and information using the tool.

        Use robot position information e.g. look at the height to decide if you can grab the object on the ground.
        
        CRITICAL: Follow the user's instructions EXACTLY as given. Do not make assumptions about what the user wants based on what you see in images.
        
        If the user says "move 3cm forward", just move 3cm forward. Do not decide to grab objects or perform other actions unless explicitly asked.
        
        Some tasks are simple - just complete them and stop. Some tasks are complex - move step by step, evaluate the results of your action after each step.
        Make sure that the step is successfully completed before moving to the next step.
        After each step ask yourself what was the original user's task and where do you stand now.
        Generate short summary about the recent action and the RELATIVE positions of all important objects you can see.
        """
        
        self.conversation_history.append({"role": "user", "content": user_input})

        max_iterations = 100
        for iteration in range(max_iterations):
            try:
                thinking_enabled = self.thinking_budget > 0 and iteration % self.thinking_every_n == 0
                temperature = 1.0 if thinking_enabled else 0.1
                
                response = await self.llm_provider.generate_response(
                    messages=[{"role": "system", "content": system_prompt}] + self.conversation_history,
                    tools=self.llm_provider.format_tools(self.tools),
                    temperature=temperature,
                    thinking_enabled=thinking_enabled,
                    thinking_budget=self.thinking_budget
                )

                assistant_message = {"role": "assistant", "content": response.content or ""}
                if response.tool_calls:
                    assistant_message["tool_calls"] = response.tool_calls
                
                self.conversation_history.append(assistant_message)
                
                if response.usage:
                    usage_parts = []
                    if response.usage.get("input_tokens"):
                        usage_parts.append(f"Input: {response.usage['input_tokens']}")
                    if response.usage.get("output_tokens"):
                        usage_parts.append(f"Output: {response.usage['output_tokens']}")
                    if response.usage.get("thinking_tokens"):
                        usage_parts.append(f"Thinking: {response.usage['thinking_tokens']}")
                    if response.usage.get("image_count"):
                        usage_parts.append(f"Images: {response.usage['image_count']}")
                    if response.usage.get("total_tokens"):
                        usage_parts.append(f"Total: {response.usage['total_tokens']}")
                    
                    if usage_parts:
                        print(f"📊 Tokens - {' | '.join(usage_parts)}")
                
                # If there are no tool calls, we are done with this turn.
                if not assistant_message.get("tool_calls"):
                    return response.content or ""

                tool_calls = self.llm_provider.format_tool_calls_for_execution(assistant_message['tool_calls'])
                
                tool_outputs = []
                for tool_call in tool_calls:
                    print(f"🔧 Calling {tool_call['name']} with params: {tool_call['input']}")
                    tool_output_parts = await self.execute_mcp_tool(tool_call["name"], tool_call["input"])
                    tool_outputs.append(tool_output_parts)
                
                tool_results_with_images, image_parts = self.llm_provider.format_tool_results_for_conversation(tool_calls, tool_outputs)

                # Only keep images from the last tool call (most recent images)
                if image_parts and len(tool_outputs) > 1:
                    # Get images only from the last tool output
                    last_tool_images = []
                    if tool_outputs:
                        for part in tool_outputs[-1]:  # Last tool output
                            if part.get('type') == 'image' and 'source' in part:
                                last_tool_images.append(part)
                    image_parts = last_tool_images

                if image_parts and self.image_viewer:
                    self.image_viewer.update(image_parts)

                # If we got response with images: remove ALL images from history and add new ones at the end
                if image_parts:
                    self.conversation_history = self._filter_images_from_conversation(self.conversation_history)

                self.conversation_history.append({"role": "tool", "content": tool_results_with_images})

            except Exception as e:
                print(f"❌ Error in agent loop: {str(e)}")
                return f"An error occurred: {str(e)}"

        return f"Completed {max_iterations} iterations without a final answer."
    
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
