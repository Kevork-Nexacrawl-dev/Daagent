"""
Core agent with tool-calling loop and dynamic model selection.
"""

from typing import List, Dict, Any, Optional
import json
from openai import OpenAI

from agent.config import Config, TaskType
from agent.prompts import build_system_prompt
from agent.tool_registry import ToolRegistry


class UnifiedAgent:
    """
    General-purpose agent with:
    - Dynamic model selection based on task type
    - Tool calling loop (ReAct pattern)
    - Prompt layering for behavior control
    """
    
    def __init__(self):
        """Initialize agent with config and prompt manager"""
        Config.validate()
        
        # Get provider instance (NEW)
        self.provider = Config.get_provider()
        self.client = self.provider.get_client()
        
        self.conversation_history = []
        
        # Initialize tool registry for auto-discovery
        self.tool_registry = ToolRegistry()
        self.available_tools = []
        
        self._register_tools()
        
        print("🤖 Unified Agent initialized")
        print(f"   Provider: {self.provider.provider_name}")
        print(f"   Mode: {'DEV' if Config.DEV_MODE else 'PROD'}")
        print(f"   Tools: {len(self.available_tools)} available")
    
    def _register_tools(self):
        """Register all available tools using auto-discovery"""
        # Auto-discover tools from tools/native/ directory
        discovered_tools = self.tool_registry.discover_tools()
        
        # Register tool schemas for OpenAI function calling
        for tool_name, tool_info in discovered_tools.items():
            self.available_tools.append(tool_info['schema'])
            print(f"   ✓ Registered tool: {tool_name}")
        
        # Discover MCP warehouse tools
        if Config.ENABLE_MCP and Config.MCP_WAREHOUSE_PATH:
            self.tool_registry.discover_mcp_warehouse(Config.MCP_WAREHOUSE_PATH)
        
        # Update available_tools with all discovered tools
        self.available_tools = self.tool_registry.get_all_schemas()
    
    def run(self, user_message: str, task_type: Optional[TaskType] = None) -> str:
        """
        Main execution loop.
        
        Args:
            user_message: User's request
            task_type: Optional explicit task type (auto-detected if None)
        
        Returns:
            Agent's final response
        """
        
        # Detect or use provided task type
        if task_type is None:
            task_type = self._detect_task_type(user_message)
        
        # Get appropriate model for this task
        model = self.provider.get_model_name(task_type.value)
        
        print(f"\n{'='*60}")
        print(f"🎯 Task Type: {task_type.value}")
        print(f"🏢 Provider: {self.provider.provider_name}")
        print(f"🧠 Model: {model}")
        print(f"{'='*60}\n")
        
        # Build messages with prompt layers
        messages = self._build_messages(user_message)
        
        # Tool calling loop
        iteration = 0
        max_iterations = Config.MAX_ITERATIONS
        
        while iteration < max_iterations:
            iteration += 1
            print(f"[Iteration {iteration}/{max_iterations}]")
            
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self.available_tools if self.available_tools else None,
                    tool_choice="auto",
                    temperature=Config.TEMPERATURE
                )
                
                if response is None:
                    raise Exception("API returned None response - possible rate limit or model issue")
                
                message = response.choices[0].message
                
                # Check if agent wants to use tools
                if message.tool_calls:
                    print(f"🔧 Agent calling {len(message.tool_calls)} tool(s)...")
                    
                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    })
                    
                    # Execute each tool call
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        print(f"   → {tool_name}({tool_args})")
                        
                        # Execute tool (we'll implement tool registry next)
                        tool_result = self._execute_tool(tool_name, tool_args)
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(tool_result)
                        })
                    
                    # Continue loop to let agent process tool results
                    continue
                
                # No tool calls - agent has final answer
                final_response = message.content
                
                # Save to conversation history
                self.conversation_history.extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": final_response}
                ])
                
                print(f"\n✅ Task completed in {iteration} iteration(s)\n")
                return final_response
            
            except Exception as e:
                error_msg = f"Error in iteration {iteration}: {str(e)}"
                print(f"❌ {error_msg}")
                return f"I encountered an error: {error_msg}"
        
        return "⚠️ Max iterations reached. Task may be incomplete."
    
    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """Build message list with system prompt and conversation history"""
        
        # Get composed system prompt from prompt manager
        system_prompt = build_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history,
            {"role": "user", "content": user_message}
        ]
        
        return messages
    
    def _detect_task_type(self, message: str) -> TaskType:
        """
        Intelligently detect task type from user message.
        This determines which model gets used.
        """
        
        message_lower = message.lower()
        
        # Browser automation keywords
        browser_keywords = [
            "apply", "job", "fill", "form", "click", "navigate",
            "browser", "website", "web", "page", "automation"
        ]
        
        # Code editing keywords
        code_keywords = [
            "edit", "file", "refactor", "update", "code", "modify",
            "create", "function", "fix", "bug", "implement", "write", "code",
            "debug", "add", "feature"
        ]
        
        if any(kw in message_lower for kw in browser_keywords):
            return TaskType.BROWSER_AUTOMATION
        
        if any(kw in message_lower for kw in code_keywords):
            return TaskType.CODE_EDITING
        
        # Default to conversational (research, Q&A, etc.)
        return TaskType.CONVERSATIONAL
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool by name using the tool registry.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        return self.tool_registry.execute_tool(tool_name, **arguments)
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("🔄 Conversation history cleared")