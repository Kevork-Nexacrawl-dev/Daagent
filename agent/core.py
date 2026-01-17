"""
Core agent with tool-calling loop and dynamic model selection.
"""

from typing import List, Dict, Any, Optional
import json
from openai import OpenAI

from rich.live import Live
from rich.markdown import Markdown
from rich.console import Console

from agent.config import Config, TaskType
from agent.prompts import build_system_prompt
from agent.tool_registry import ToolRegistry
from agent.provider_manager import ProviderManager
from agent.query_classifier import QueryClassifier, QueryType
from agent.response_cache import ResponseCache
from agent.checkpoint import TaskCheckpoint
from agent.partial_result_handler import PartialResultHandler
from agent.errors import PartialSuccess
import hashlib


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
        
        # NEW: Use provider manager instead of single provider
        self.provider_manager = ProviderManager()
        self.provider_manager.load_state()  # Load previous rate limits
        
        # NEW: Initialize optimization components
        self.query_classifier = QueryClassifier()
        self.response_cache = ResponseCache(ttl_hours=Config.CACHE_TTL_HOURS)
        
        self.conversation_history = []  # Conversation history for context
        
        # Initialize tool registry for auto-discovery (lazy loading)
        self.tool_registry = ToolRegistry()
        self.available_tools = []
        self._tools_loaded = False  # Flag to track if tools are loaded
        
        # Only load tools if not using lazy loading
        if not Config.ENABLE_LAZY_TOOLS:
            self._ensure_tools_loaded()
        
        print("🤖 Unified Agent initialized")
        print(f"   Mode: {'DEV' if Config.DEV_MODE else 'PROD'}")
        print(f"   Tools: {'Not loaded yet (lazy)' if Config.ENABLE_LAZY_TOOLS else f'{len(self.available_tools)} available'}")
        print(f"   Providers: {len(self.provider_manager.providers)} loaded")
        print(f"   Optimizations: {'ENABLED' if Config.ENABLE_QUERY_CLASSIFICATION else 'DISABLED'}")
    
    def _ensure_tools_loaded(self):
        """Ensure tools are loaded (lazy loading)"""
        if not self._tools_loaded:
            self._register_tools()
            self._tools_loaded = True
    
    def _register_tools(self):
        """Register all available tools using auto-discovery"""
        # Auto-discover tools from tools/native/ directory
        discovered_tools = self.tool_registry.discover_tools()
        
        # Register tool schemas for OpenAI function calling
        for tool_name, tool_info in discovered_tools.items():
            self.available_tools.append(tool_info['schema'])
            print(f"   ✓ Registered tool: {tool_name}")
        
        # Discover MCP warehouse tools (only if MCP is enabled)
        if Config.ENABLE_MCP and Config.MCP_WAREHOUSE_PATH:
            self.tool_registry.discover_mcp_warehouse(Config.MCP_WAREHOUSE_PATH)
        
        # Update available_tools with all discovered tools
        self.available_tools = self.tool_registry.get_all_schemas()
    
    def run(self, user_message: str, task_type: Optional[TaskType] = None) -> str:
        """
        Optimized execution loop with query classification and caching.
        
        Args:
            user_message: User's request
            task_type: Optional explicit task type (auto-detected if None)
        
        Returns:
            Agent's final response
        """
        
        # Step 1: Classify query for optimization
        if Config.ENABLE_QUERY_CLASSIFICATION:
            query_type = QueryClassifier.classify(user_message)
            print(f"🔍 Query classified as: {query_type.value} ({QueryClassifier.get_execution_mode(query_type)})")
        else:
            query_type = QueryType.COMPLEX  # Default to full ReAct when disabled
        
        # Step 2: Check cache for instant responses
        if Config.ENABLE_RESPONSE_CACHE and QueryClassifier.should_check_cache(query_type):
            cached_response = self.response_cache.get(user_message)
            if cached_response:
                print("⚡ Cache hit! Returning instant response")
                return cached_response
        
        # Step 3: Detect or use provided task type
        if task_type is None:
            task_type = self._detect_task_type(user_message)
        
        # Step 4: Assess task complexity for provider selection
        complexity = self._assess_complexity(user_message, task_type)
        
        # Step 5: Get optimal provider with fallback logic
        provider = self.provider_manager.get_next_provider(complexity)
        client = provider.get_client()
        model = provider.get_model_name(task_type.value)
        
        print(f"\n{'='*60}")
        print(f"🎯 Task Type: {task_type.value} (complexity: {complexity})")
        print(f"🏢 Provider: {provider.provider_name}")
        print(f"🧠 Model: {model}")
        print(f"{'='*60}\n")
        
        # Step 6: Execute based on query type
        if query_type == QueryType.INFORMATIONAL and Config.ENABLE_LAZY_TOOLS:
            # Lite mode: Single LLM call, no tools (skip tool loading)
            response = self._execute_lite_mode(user_message, client, model, task_type, provider)
        else:
            # Full ReAct mode: Ensure tools are loaded, then use tool calling loop
            self._ensure_tools_loaded()
            response = self._execute_react_mode(user_message, client, model, task_type, provider, query_type)
        
        # Step 7: Cache response if applicable
        if Config.ENABLE_RESPONSE_CACHE and query_type == QueryType.CACHED:
            self.response_cache.put(user_message, response)
        
        return response
    
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
    
    def _assess_complexity(self, message: str, task_type: TaskType) -> str:
        """
        Assess task complexity for provider selection.
        
        Returns:
            "simple", "medium", or "complex"
        """
        message_lower = message.lower()
        
        # Complex indicators
        complex_keywords = [
            "research", "analyze", "compare", "multiple", "comprehensive",
            "detailed", "step-by-step", "thorough", "extensive", "deep"
        ]
        
        # Simple indicators
        simple_keywords = [
            "quick", "simple", "basic", "brief", "short", "fast"
        ]
        
        # Task type complexity
        if task_type == TaskType.CODE_EDITING:
            # Code editing is typically complex
            base_complexity = "complex"
        elif task_type == TaskType.BROWSER_AUTOMATION:
            # Browser automation can be complex
            base_complexity = "medium"
        else:
            # Conversational is usually medium
            base_complexity = "medium"
        
        # Adjust based on keywords
        if any(kw in message_lower for kw in complex_keywords):
            return "complex"
        elif any(kw in message_lower for kw in simple_keywords):
            return "simple"
        else:
            return base_complexity
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if an exception is a rate limit error.
        
        Args:
            error: The exception to check
            
        Returns:
            True if this appears to be a rate limit error
        """
        error_msg = str(error).lower()
        return any(keyword in error_msg for keyword in ["rate limit", "429", "quota exceeded"])
    
    def _estimate_tokens(self, messages: List[Dict], response: str) -> int:
        """
        Rough token estimation for cost tracking.
        
        This is approximate - actual token counts vary by model.
        """
        total_chars = 0
        
        # Count characters in messages
        for msg in messages:
            if isinstance(msg, dict):
                for key, value in msg.items():
                    if isinstance(value, str):
                        total_chars += len(value)
                    elif isinstance(value, list):
                        # Handle tool calls
                        for item in value:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    if isinstance(v, str):
                                        total_chars += len(v)
        
        # Add response
        total_chars += len(response)
        
        # Rough conversion: ~4 chars per token
        return total_chars // 4
    
    def _stream_response(self, client, model: str, messages: List[Dict],
                        tools=None, tool_choice=None) -> tuple[str, List]:
        """
        Stream LLM response with real-time display and JSON events for web UI.

        Args:
            client: LLM client
            model: Model name
            messages: Message history
            tools: Tool schemas (optional)
            tool_choice: Tool choice mode (optional)

        Returns:
            Tuple of (complete_response, tool_calls_list)
        """
        accumulated_content = ""
        tool_calls_accumulator = []

        # Create streaming request
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=Config.TEMPERATURE,
            stream=True  # Enable streaming
        )

        # Display streamed response in real-time
        console = Console()
        with Live("", refresh_per_second=20, console=console) as live:
            for chunk in stream:
                delta = chunk.choices[0].delta

                # Accumulate content
                if delta.content:
                    accumulated_content += delta.content
                    live.update(Markdown(accumulated_content))

                    # Output JSON event for web UI
                    event = {"type": "text", "content": delta.content}
                    print(json.dumps(event), flush=True)

                # Collect tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        # Initialize or update tool call
                        if tc.index >= len(tool_calls_accumulator):
                            tool_calls_accumulator.append({
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name if tc.function.name else "",
                                    "arguments": tc.function.arguments if tc.function.arguments else ""
                                }
                            })
                        else:
                            # Append to existing tool call arguments
                            if tc.function.arguments:
                                tool_calls_accumulator[tc.index]["function"]["arguments"] += tc.function.arguments

        print()  # Newline after streaming completes

        return accumulated_content, tool_calls_accumulator
    
    def _execute_lite_mode(self, user_message: str, client, model: str, task_type: TaskType, provider) -> str:
        """
        Execute in lite mode: single LLM call without tools.
        
        Args:
            user_message: User's query
            client: LLM client
            model: Model name
            task_type: Task type
            provider: Provider instance
            
        Returns:
            LLM response
        """
        print("🚀 Lite mode: Single LLM call (no tools)")
        
        messages = self._build_messages_optimized(user_message, include_tools=False)
        
        try:
            if Config.ENABLE_STREAMING:
                print("\n🤖 Assistant:")
                final_response, _ = self._stream_response(
                    client, model, messages, tools=None
                )
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=None,  # Explicitly no tools
                    temperature=Config.TEMPERATURE
                )
                
                if response is None:
                    raise Exception("API returned None response")
                
                final_response = response.choices[0].message.content
            
            # Log usage
            tokens_used = self._estimate_tokens(messages, final_response)
            self.provider_manager.log_usage(provider.provider_name.lower(), tokens_used)
            
            # Save conversation history
            self.conversation_history.extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": final_response}
            ])
            
            print("\n✅ Lite mode completed\n")
            print(self.provider_manager.get_status_report())
            self.provider_manager.save_state()
            
            return final_response
            
        except Exception as e:
            if self._is_rate_limit_error(e):
                provider = self.provider_manager.handle_rate_limit(provider.provider_name.lower(), e)
                return self._execute_lite_mode(user_message, provider.get_client(), 
                                             provider.get_model_name(task_type.value), task_type, provider)
            
            print(f"❌ Lite mode error: {e}")
            print(self.provider_manager.get_status_report())
            self.provider_manager.save_state()
            
            return f"I encountered an error: {e}"
    
    def _execute_react_mode(self, user_message: str, client, model: str, task_type: TaskType, 
                           provider, query_type: QueryType) -> str:
        """
        Execute in full ReAct mode with tool calling loop.
        
        Args:
            user_message: User's query
            client: LLM client
            model: Model name
            task_type: Task type
            provider: Provider instance
            query_type: Classified query type
            
        Returns:
            Final response after tool calling loop
        """
        print("🔄 Full ReAct mode: Tool calling loop")
        
        messages = self._build_messages_optimized(user_message, 
                                                 include_tools=self._should_include_tools(query_type))
        
        iteration = 0
        max_iterations = Config.MAX_ITERATIONS
        
        # Initialize checkpoint for partial success tracking
        task_id = hashlib.md5(user_message.encode()).hexdigest()[:12]
        checkpoint = TaskCheckpoint(task_id)
        print(f"📍 Checkpoint ID: {task_id}")
        
        while iteration < max_iterations:
            iteration += 1
            print(f"[Iteration {iteration}/{max_iterations}]")
            
            try:
                should_use_tools = self._should_include_tools(query_type)
                tools = self._get_tools_for_request(query_type) if should_use_tools else None
                
                if Config.ENABLE_STREAMING:
                    print(f"\n🤖 Assistant (iteration {iteration}):")
                    content, tool_calls_data = self._stream_response(
                        client, model, messages, 
                        tools=tools,
                        tool_choice="auto" if should_use_tools else None
                    )
                    
                    # Create message object from streamed data
                    class StreamedMessage:
                        def __init__(self, content, tool_calls):
                            self.content = content
                            self.tool_calls = []
                            
                            if tool_calls:
                                for tc in tool_calls:
                                    class ToolCall:
                                        def __init__(self, data):
                                            self.id = data["id"]
                                            self.type = data["type"]
                                            class Function:
                                                def __init__(self, func_data):
                                                    self.name = func_data["name"]
                                                    self.arguments = func_data["arguments"]
                                            self.function = Function(data["function"])
                                    
                                    self.tool_calls.append(ToolCall(tc))
                    
                    message = StreamedMessage(content, tool_calls_data)
                else:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto" if should_use_tools else None,
                        temperature=Config.TEMPERATURE
                    )
                    
                    if response is None:
                        raise Exception("API returned None response - possible rate limit or model issue")
                    
                    message = response.choices[0].message
                
                # Check if agent wants to use tools
                if message.tool_calls and self._should_include_tools(query_type):
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
                        
                        # Execute tool with retry logic and fallbacks
                        try:
                            tool_result = self.tool_registry.execute_tool_safe(
                                tool_name, 
                                use_fallbacks=True, 
                                **tool_args
                            )
                            
                            # Track successful tool execution
                            tool_result_parsed = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
                            
                            # Check if tool result indicates failure
                            is_tool_error = (
                                isinstance(tool_result_parsed, dict) and
                                tool_result_parsed.get("status") == "error"
                            )
                            
                            if is_tool_error:
                                # Track as failed step
                                checkpoint.add_step(
                                    step_name=f"Tool: {tool_name}",
                                    result=tool_result_parsed,
                                    success=False
                                )
                                
                                # Return partial results if we have any completed steps
                                if checkpoint.has_completed_steps():
                                    checkpoint.save_to_file()
                                    partial_response = PartialResultHandler.format_response(
                                        checkpoint,
                                        final_error=f"Tool '{tool_name}' returned error: {tool_result_parsed.get('message', 'Unknown error')}"
                                    )
                                    
                                    print("\n⚠️ Returning partial results\n")
                                    print(self.provider_manager.get_status_report())
                                    self.provider_manager.save_state()
                                    
                                    return partial_response
                                
                                # No completed steps - continue with error result
                                checkpoint.add_step(
                                    step_name=f"Tool: {tool_name}",
                                    result=tool_result_parsed,
                                    success=False
                                )
                            else:
                                # Track as successful step
                                checkpoint.add_step(
                                    step_name=f"Tool: {tool_name}",
                                    result=tool_result_parsed,
                                    success=True
                                )

                            # Output tool call event for web UI
                            tool_event = {
                                "type": "tool",
                                "name": tool_name,
                                "args": tool_args,
                                "result": str(tool_result)[:200]  # Truncate for display
                            }
                            print(json.dumps(tool_event), flush=True)

                        except (FatalError, Exception) as e:
                            # Track failed tool execution
                            checkpoint.add_step(
                                step_name=f"Tool: {tool_name}",
                                result=str(e),
                                success=False
                            )

                            # Return partial results if we have any completed steps
                            if checkpoint.has_completed_steps():
                                checkpoint.save_to_file()
                                partial_response = PartialResultHandler.format_response(
                                    checkpoint,
                                    final_error=f"Tool '{tool_name}' failed: {e}"
                                )

                                print("\n⚠️ Returning partial results\n")
                                print(self.provider_manager.get_status_report())
                                self.provider_manager.save_state()

                                return partial_response

                            # No completed steps - return normal error
                            tool_result = json.dumps({
                                "success": False,
                                "error": f"Fatal error: {e}",
                                "suggestion": "This error cannot be retried. Check tool arguments."
                            })

                            # Output tool call event for web UI (error case)
                            tool_event = {
                                "type": "tool",
                                "name": tool_name,
                                "args": tool_args,
                                "result": str(tool_result)[:200]  # Truncate for display
                            }
                            print(json.dumps(tool_event), flush=True)
                        
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
                
                # Log usage for cost tracking
                tokens_used = self._estimate_tokens(messages, final_response)
                self.provider_manager.log_usage(provider.provider_name.lower(), tokens_used)
                
                # Save conversation history
                self.conversation_history.extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": final_response}
                ])
                
                print(f"\n✅ Task completed in {iteration} iteration(s)\n")
                
                # Save checkpoint for successful completion
                checkpoint.save_to_file()
                
                # Show cost report
                print(self.provider_manager.get_status_report())
                
                # Save state for persistence
                self.provider_manager.save_state()
                
                return final_response
            
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for rate limit errors
                if self._is_rate_limit_error(e):
                    # Handle rate limit with fallback
                    provider = self.provider_manager.handle_rate_limit(
                        provider.provider_name.lower(), e
                    )
                    client = provider.get_client()
                    model = provider.get_model_name(task_type.value)
                    
                    print(f"🔄 Retrying with {provider.provider_name}...")
                    continue
                
                # Other errors - fail gracefully
                print(f"❌ Error in iteration {iteration}: {e}")
                
                # Show status even on failure
                print(self.provider_manager.get_status_report())
                self.provider_manager.save_state()
                
                return f"I encountered an error: {e}"
        
        # Max iterations reached
        print(self.provider_manager.get_status_report())
        self.provider_manager.save_state()
        
        return "⚠️ Max iterations reached. Task may be incomplete."
    
    def _should_include_tools(self, query_type: QueryType) -> bool:
        """
        Determine if tools should be included based on query type and config.
        
        Args:
            query_type: Classified query type
            
        Returns:
            True if tools should be included
        """
        if not Config.ENABLE_LAZY_TOOLS:
            return True  # Always include when lazy loading disabled
        
        return QueryClassifier.should_use_tools(query_type)
    
    def _get_tools_for_request(self, query_type: QueryType) -> list:
        """
        Get appropriate tool schemas for the request.
        
        Args:
            query_type: Classified query type
            
        Returns:
            List of tool schemas
        """
        if not self._should_include_tools(query_type):
            return []
        
        # For now, return all tools. Could be optimized further
        # to return only relevant tools based on query type
        return self.available_tools
    
    def _build_messages_optimized(self, user_message: str, include_tools: bool = True) -> List[Dict[str, str]]:
        """
        Build message list optimized for the execution mode.
        
        Args:
            user_message: User's message
            include_tools: Whether tools are being used (affects prompt)
            
        Returns:
            List of messages
        """
        # Get composed system prompt from prompt manager
        system_prompt = build_system_prompt()
        
        # For lite mode, could add a note about no tools available
        if not include_tools:
            system_prompt += "\n\nNOTE: You are in lite mode. No tools are available for this query. Focus on providing direct, informative responses based on your knowledge."
        
        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history,
            {"role": "user", "content": user_message}
        ]
        
        return messages
    
    def reset_conversation(self) -> None:
        """
        Reset conversation history.
        """
        self.conversation_history = []
        print("Conversation history cleared")