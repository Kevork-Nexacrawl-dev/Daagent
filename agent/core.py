"""
Core agent with tool-calling loop and dynamic model selection.
"""

from typing import List, Dict, Any, Optional
import json
import sys
import os
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
from agent.model_selector import ModelSelector
import hashlib


class ConversationContextManager:
    """
    Manages conversation context with token-based truncation and summarization.
    
    Features:
    - Token-aware context management
    - Automatic summarization of old messages
    - Configurable context limits
    """
    
    def __init__(self):
        """Initialize context manager with empty history"""
        self.messages = []  # List of {"role": str, "content": str} dicts
        self.summaries = []  # List of summary messages
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation context.
        
        Args:
            role: Message role ("user", "assistant", "system", "tool")
            content: Message content
        """
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """
        Get current conversation messages, potentially truncated/summarized.
        
        Returns:
            List of message dictionaries
        """
        # If summarization is disabled or we haven't hit limits, return all
        if not Config.ENABLE_CONTEXT_SUMMARIZATION:
            return self.messages.copy()
        
        # Check if we need to truncate/summarize
        total_tokens = self._estimate_total_tokens()
        effective_limit = Config.MAX_CONTEXT_TOKENS - Config.CONTEXT_RESERVE_TOKENS
        
        if total_tokens <= effective_limit:
            return self.messages.copy()
        
        # Need to truncate - start with summaries, then recent messages
        return self._build_truncated_context(effective_limit)
    
    def _estimate_total_tokens(self) -> int:
        """Estimate total tokens in current context"""
        total_chars = 0
        for msg in self.messages:
            total_chars += len(msg.get("content", ""))
        # Rough conversion: ~4 chars per token
        return total_chars // 4
    
    def _build_truncated_context(self, max_tokens: int) -> List[Dict[str, str]]:
        """
        Build truncated context that fits within token limit.
        
        Strategy:
        1. Include all summaries (they're condensed)
        2. Add recent messages until we hit the limit
        3. If still over limit, summarize oldest messages
        
        Args:
            max_tokens: Maximum tokens to use
            
        Returns:
            Truncated message list
        """
        context = []
        current_tokens = 0
        
        # Always include summaries first (they're already condensed)
        for summary in self.summaries:
            summary_tokens = len(summary["content"]) // 4
            if current_tokens + summary_tokens <= max_tokens:
                context.append(summary)
                current_tokens += summary_tokens
            else:
                break
        
        # Add recent messages from the end
        recent_messages = []
        for msg in reversed(self.messages):
            msg_tokens = len(msg["content"]) // 4
            if current_tokens + msg_tokens <= max_tokens:
                recent_messages.insert(0, msg)  # Insert at beginning to maintain order
                current_tokens += msg_tokens
            else:
                break
        
        context.extend(recent_messages)
        
        # If we still don't have enough space and have old messages to summarize
        if current_tokens > max_tokens and len(self.messages) > len(recent_messages):
            context = self._summarize_and_rebuild(context, max_tokens)
        
        return context
    
    def _summarize_and_rebuild(self, current_context: List[Dict], max_tokens: int) -> List[Dict[str, str]]:
        """
        Create a summary of old messages and rebuild context.
        
        Args:
            current_context: Current truncated context
            max_tokens: Maximum tokens allowed
            
        Returns:
            Context with summary prepended
        """
        # Find how many old messages we can summarize
        old_messages = []
        for msg in self.messages:
            if msg not in current_context:
                old_messages.append(msg)
        
        if not old_messages:
            return current_context
        
        # Create summary of old messages
        summary_content = self._create_conversation_summary(old_messages)
        summary_msg = {
            "role": "system",
            "content": f"Previous conversation summary: {summary_content}"
        }
        
        # Add summary to our summaries list for future use
        self.summaries.append(summary_msg)
        
        # Rebuild context with summary
        new_context = [summary_msg]
        current_tokens = len(summary_content) // 4
        
        # Add as many recent messages as possible
        for msg in reversed(self.messages):
            if msg in current_context:
                msg_tokens = len(msg["content"]) // 4
                if current_tokens + msg_tokens <= max_tokens:
                    new_context.append(msg)
                    current_tokens += msg_tokens
        
        return new_context
    
    def _create_conversation_summary(self, messages: List[Dict]) -> str:
        """
        Create a concise summary of conversation messages.
        
        Args:
            messages: Messages to summarize
            
        Returns:
            Summary string
        """
        # Simple summarization strategy - could be enhanced with LLM
        user_queries = []
        assistant_responses = []
        tool_calls = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"][:200]  # Truncate for summary
            
            if role == "user":
                user_queries.append(content)
            elif role == "assistant":
                if "tool_calls" in msg or "I called" in content.lower():
                    tool_calls.append(content)
                else:
                    assistant_responses.append(content)
            elif role == "tool":
                tool_calls.append(f"Tool result: {content[:100]}")
        
        summary_parts = []
        if user_queries:
            summary_parts.append(f"User asked about: {'; '.join(user_queries[:3])}")
        if assistant_responses:
            summary_parts.append(f"Assistant provided: {'; '.join(assistant_responses[:2])}")
        if tool_calls:
            summary_parts.append(f"Tools used: {len(tool_calls)} operations")
        
        return ". ".join(summary_parts) if summary_parts else "Previous conversation context"
    
    def reset(self) -> None:
        """Reset conversation context"""
        self.messages = []
        self.summaries = []
    
    def get_stats(self) -> Dict[str, int]:
        """Get context statistics"""
        return {
            "total_messages": len(self.messages),
            "total_summaries": len(self.summaries),
            "estimated_tokens": self._estimate_total_tokens()
        }


class UnifiedAgent:
    """
    General-purpose agent with:
    - Dynamic model selection based on task type
    - Tool calling loop (ReAct pattern)
    - Prompt layering for behavior control
    """
    
    def __init__(self, model_preference: str = "auto"):
        """Initialize agent with config and prompt manager"""
        Config.validate()
        
        # Check if running in web mode (stdout used for JSON events)
        self.web_mode = os.getenv('DAAGENT_WEB_MODE') == '1'
        
        # NEW: Initialize model selector with preference
        self.model_selector = ModelSelector(preference=model_preference)
        
        # NEW: Use provider manager instead of single provider
        self.provider_manager = ProviderManager()
        self.provider_manager.load_state()  # Load previous rate limits
        
        # NEW: Initialize optimization components
        self.query_classifier = QueryClassifier()
        self.response_cache = ResponseCache(ttl_hours=Config.CACHE_TTL_HOURS)
        
        # Initialize conversation context manager
        self.context_manager = ConversationContextManager()
        
        # Initialize hybrid memory system
        from agent.memory.hybrid_memory import HybridMemory
        self.memory = HybridMemory()
        self.session_id = self._generate_session_id()
        
        # Initialize tool registry for auto-discovery (lazy loading)
        self.tool_registry = ToolRegistry()
        self.available_tools = []
        self._tools_loaded = False  # Flag to track if tools are loaded
        
        # Only load tools if not using lazy loading
        if not Config.ENABLE_LAZY_TOOLS:
            self._ensure_tools_loaded()
        
        if not self.web_mode:
            sys.stderr.write("🤖 Unified Agent initialized\n")
            sys.stderr.write(f"   Mode: {'DEV' if Config.DEV_MODE else 'PROD'}\n")
            sys.stderr.write(f"   Tools: {'Not loaded yet (lazy)' if Config.ENABLE_LAZY_TOOLS else f'{len(self.available_tools)} available'}\n")
            sys.stderr.write(f"   Providers: {len(self.provider_manager.providers)} loaded\n")
            sys.stderr.write(f"   Optimizations: {'ENABLED' if Config.ENABLE_QUERY_CLASSIFICATION else 'DISABLED'}\n")
            sys.stderr.write(f"   Context Management: {'ENABLED' if Config.ENABLE_CONTEXT_SUMMARIZATION else 'DISABLED'} ({Config.MAX_CONTEXT_TOKENS} tokens)\n")
            sys.stderr.write(f"   Memory System: {'ENABLED' if Config.MEMORY_EXTRACTION_ENABLED else 'DISABLED'}\n")
            sys.stderr.flush()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID for memory tracking."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _requires_tools(self, user_input: str) -> bool:
        """
        Detect if user query needs tool calling.
        
        Args:
            user_input: User's message
            
        Returns:
            True if tools are likely needed
        """
        tool_keywords = [
            "use tool", "mcp", "filesystem", "file", "search", 
            "web", "execute", "run code", "database", "api",
            "read", "write", "create", "delete", "list",
            "find", "search", "grep", "run", "execute"
        ]
        return any(kw in user_input.lower() for kw in tool_keywords)
    
    def _get_model_capabilities(self, model_id: str) -> Dict[str, Any]:
        """
        Get model capabilities from the model library.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model capability information
        """
        # Check free tool models
        if model_id in Config.FREE_TOOL_MODELS:
            return Config.FREE_TOOL_MODELS[model_id]
        
        # Check free reasoning models
        if model_id in Config.FREE_REASONING_MODELS:
            return Config.FREE_REASONING_MODELS[model_id]
        
        # Check paid models
        if model_id in Config.PAID_MODELS:
            return Config.PAID_MODELS[model_id]
        
        # Default fallback (assume tool support for unknown models)
        return {
            "display_name": model_id,
            "supports_tools": True,
            "supports_streaming": True,
            "context_window": 65536,
            "best_for": "General purpose",
            "cost_per_1m": 0.0,
            "tier": "unknown"
        }
    
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
            if not self.web_mode:
                sys.stderr.write(f"   ✓ Registered tool: {tool_name}\n")
                sys.stderr.flush()
        
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
            if not self.web_mode:
                sys.stderr.write(f"🔍 Query classified as: {query_type.value} ({QueryClassifier.get_execution_mode(query_type)})\n")
                sys.stderr.flush()
        else:
            query_type = QueryType.COMPLEX  # Default to full ReAct when disabled
        
        # Step 2: Check cache for instant responses
        if Config.ENABLE_RESPONSE_CACHE and QueryClassifier.should_check_cache(query_type):
            cached_response = self.response_cache.get(user_message)
            if cached_response:
                if not self.web_mode:
                    sys.stderr.write("⚡ Cache hit! Returning instant response\n")
                    sys.stderr.flush()
                return cached_response
        
        # Step 3: Detect or use provided task type
        if task_type is None:
            task_type = self._detect_task_type(user_message)
        
        # Step 3.5: Memory Integration - Store user message and retrieve relevant context
        # Store user message in working memory
        self.memory.store_working(
            content=user_message,
            metadata={"role": "user", "session_id": self.session_id}
        )
        
        # Retrieve relevant memories for context injection
        relevant_memories = self.memory.retrieve_relevant(
            query=user_message,
            task_type=self._classify_task_for_memory(user_message),
            top_k=5,
            session_id=self.session_id
        )
        
        # Step 4: Assess task complexity for provider selection
        complexity = self._assess_complexity(user_message, task_type)
        
        # Step 5: Get optimal provider with fallback logic
        provider = self.provider_manager.get_next_provider(complexity, task_type.value)
        client = provider.get_client()
        model = provider.get_model_name(task_type.value)
        
        # Step 5.5: Validate model capabilities for tool requirements
        requires_tools = self._requires_tools(user_message)
        model_capabilities = self._get_model_capabilities(model)
        
        if requires_tools and not model_capabilities.get('supports_tools', True):
            error_msg = (
                f"Task requires tool calling, but {model_capabilities.get('display_name', model)} "
                f"doesn't support tools. Switch to a tool-capable model: "
                f"Qwen3 Next 80B, Trinity Large, DeepSeek V3, Devstral 2, Nemotron 3 Nano, or Mimo V2 Flash"
            )
            if self.web_mode:
                # Emit error event for web UI
                error_event = {
                    "type": "error",
                    "message": error_msg,
                    "code": "MODEL_TOOL_MISMATCH"
                }
                print(json.dumps(error_event), flush=True)
            raise ValueError(error_msg)
        
        # Emit actual selected model info to web UI
        model_info = self.model_selector.get_model_info_by_id(model)
        model_event = {
            "type": "model_info",
            "model_name": model_info.get("display_name", model),
            "cost_tier": model_info.get("cost_tier", "unknown"),
            "supports_tools": model_capabilities.get("supports_tools", True)
        }
        print(json.dumps(model_event), flush=True)
        
        if not self.web_mode:
            sys.stderr.write(f"\n{'='*60}\n")
            sys.stderr.write(f"🎯 Task Type: {task_type.value} (complexity: {complexity})\n")
            sys.stderr.write(f"🏢 Provider: {provider.provider_name}\n")
            sys.stderr.write(f"🧠 Model: {model}\n")
            sys.stderr.write(f"🧠 Memories Retrieved: {len(relevant_memories)}\n")
            sys.stderr.write(f"{'='*60}\n\n")
            sys.stderr.flush()
        
        # Step 6: Execute based on query type
        # Format memory context for injection
        memory_context = self.memory.format_for_injection(relevant_memories) if relevant_memories else None
        
        if query_type == QueryType.INFORMATIONAL and Config.ENABLE_LAZY_TOOLS:
            # Lite mode: Single LLM call, no tools (skip tool loading)
            response = self._execute_lite_mode(user_message, client, model, task_type, provider, memory_context)
        else:
            # Full ReAct mode: Ensure tools are loaded, then use tool calling loop
            self._ensure_tools_loaded()
            response = self._execute_react_mode(user_message, client, model, task_type, provider, query_type, memory_context)
        
        # Step 7: Cache response if applicable
        if Config.ENABLE_RESPONSE_CACHE and query_type == QueryType.CACHED:
            self.response_cache.put(user_message, response)
        
        # Step 8: Store assistant response in memory
        self.memory.store_working(
            content=response,
            metadata={"role": "assistant", "session_id": self.session_id}
        )
        
        return response
    
    def _build_messages(self, user_message: str, memory_context: str = None) -> List[Dict[str, str]]:
        """Build message list with system prompt and conversation history"""
        
        # Get composed system prompt from prompt manager
        system_prompt = build_system_prompt()
        
        # Inject memory context if available
        if memory_context:
            system_prompt += "\n\n" + memory_context
        
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
    
    def _classify_task_for_memory(self, query: str) -> str:
        """
        Classify query type for adaptive memory retrieval.
        
        Returns: "recall", "knowledge", or "general"
        """
        recall_keywords = ["remember", "you said", "earlier", "last time", "previously"]
        knowledge_keywords = ["what is", "how does", "explain", "define", "tell me about"]
        
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in recall_keywords):
            return "recall"
        elif any(kw in query_lower for kw in knowledge_keywords):
            return "knowledge"
        else:
            return "general"
    
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
    
    def _execute_lite_mode(self, user_message: str, client, model: str, task_type: TaskType, provider, memory_context: str = None) -> str:
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
        if not self.web_mode:
            sys.stderr.write("🚀 Lite mode: Single LLM call (no tools)\n")
            sys.stderr.flush()
        
        messages = self._build_messages_optimized(user_message, include_tools=False, memory_context=memory_context)
        
        try:
            if Config.ENABLE_STREAMING:
                if not self.web_mode:
                    sys.stderr.write("\n🤖 Assistant:\n")
                    sys.stderr.flush()
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
            self.context_manager.add_message("user", user_message)
            self.context_manager.add_message("assistant", final_response)
            
            print("\n✅ Lite mode completed\n")
            if not self.web_mode:
                sys.stderr.write(self.provider_manager.get_status_report())
                sys.stderr.flush()
            self.provider_manager.save_state()
            
            return final_response
            
            return final_response
            
        except Exception as e:
            if self._is_rate_limit_error(e):
                provider = self.provider_manager.handle_rate_limit(provider.provider_name.lower(), e, task_type.value)
                return self._execute_lite_mode(user_message, provider.get_client(), 
                                             provider.get_model_name(task_type.value), task_type, provider)
            
            print(f"❌ Lite mode error: {e}")
            if not self.web_mode:
                sys.stderr.write(self.provider_manager.get_status_report())
                sys.stderr.flush()
            self.provider_manager.save_state()
            
            return f"I encountered an error: {e}"
            
            return f"I encountered an error: {e}"
    
    def _execute_react_mode(self, user_message: str, client, model: str, task_type: TaskType, 
                           provider, query_type: QueryType, memory_context: str = None) -> str:
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
        if not self.web_mode:
            sys.stderr.write("🔄 Full ReAct mode: Tool calling loop\n")
            sys.stderr.flush()
        
        messages = self._build_messages_optimized(user_message, 
                                                 include_tools=self._should_include_tools(query_type),
                                                 memory_context=memory_context)
        
        iteration = 0
        max_iterations = Config.MAX_ITERATIONS
        
        # Initialize checkpoint for partial success tracking
        task_id = hashlib.md5(user_message.encode()).hexdigest()[:12]
        checkpoint = TaskCheckpoint(task_id)
        if not self.web_mode:
            sys.stderr.write(f"📍 Checkpoint ID: {task_id}\n")
            sys.stderr.flush()
        
        while iteration < max_iterations:
            iteration += 1
            if not self.web_mode:
                sys.stderr.write(f"[Iteration {iteration}/{max_iterations}]\n")
                sys.stderr.flush()
            
            try:
                should_use_tools = self._should_include_tools(query_type)
                tools = self._get_tools_for_request(query_type) if should_use_tools else None
                
                if Config.ENABLE_STREAMING:
                    if not self.web_mode:
                        sys.stderr.write(f"\n🤖 Assistant (iteration {iteration}):\n")
                        sys.stderr.flush()
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
                    if not self.web_mode:
                        sys.stderr.write(f"🔧 Agent calling {len(message.tool_calls)} tool(s)...\n")
                        sys.stderr.flush()
                    
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
                        
                        if not self.web_mode:
                            sys.stderr.write(f"   → {tool_name}({tool_args})\n")
                            sys.stderr.flush()
                        
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
                                    if not self.web_mode:
                                        sys.stderr.write(self.provider_manager.get_status_report())
                                        sys.stderr.flush()
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
                                if not self.web_mode:
                                    sys.stderr.write(self.provider_manager.get_status_report())
                                    sys.stderr.flush()
                                self.provider_manager.save_state()

                                return partial_response

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
                self.context_manager.add_message("user", user_message)
                self.context_manager.add_message("assistant", final_response)
                
                print(f"\n✅ Task completed in {iteration} iteration(s)\n")
                
                # Save checkpoint for successful completion
                checkpoint.save_to_file()
                
                # Show cost report
                if not self.web_mode:
                    sys.stderr.write(self.provider_manager.get_status_report())
                    sys.stderr.flush()
                
                # Save state for persistence
                self.provider_manager.save_state()
                
                return final_response
            
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for rate limit errors
                if self._is_rate_limit_error(e):
                    # Handle rate limit with fallback
                    provider = self.provider_manager.handle_rate_limit(
                        provider.provider_name.lower(), e, task_type.value
                    )
                    client = provider.get_client()
                    model = provider.get_model_name(task_type.value)
                    
                    if not self.web_mode:
                        sys.stderr.write(f"🔄 Retrying with {provider.provider_name}...\n")
                        sys.stderr.flush()
                    continue
                
                # Other errors - fail gracefully
                if not self.web_mode:
                    sys.stderr.write(f"❌ Error in iteration {iteration}: {e}\n")
                    sys.stderr.write(self.provider_manager.get_status_report())
                    sys.stderr.flush()
                self.provider_manager.save_state()
                
                return f"I encountered an error: {e}"
        
        # Max iterations reached
        if not self.web_mode:
            sys.stderr.write(self.provider_manager.get_status_report())
            sys.stderr.flush()
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
    
    def _build_messages_optimized(self, user_message: str, include_tools: bool = True, memory_context: str = None) -> List[Dict[str, str]]:
        """
        Build message list optimized for the execution mode.
        
        Args:
            user_message: User's message
            include_tools: Whether tools are being used (affects prompt)
            memory_context: Memory context to inject
            
        Returns:
            List of messages
        """
        # Get composed system prompt from prompt manager
        system_prompt = build_system_prompt()
        
        # Inject memory context if available
        if memory_context:
            system_prompt += "\n\n" + memory_context
        
        # For lite mode, could add a note about no tools available
        if not include_tools:
            system_prompt += "\n\nNOTE: You are in lite mode. No tools are available for this query. Focus on providing direct, informative responses based on your knowledge."
        
        messages = [
            {"role": "system", "content": system_prompt},
            *self.context_manager.get_messages(),
            {"role": "user", "content": user_message}
        ]
        
        return messages
    
    def reset_conversation(self) -> None:
        """
        Reset conversation history.
        """
        self.context_manager.reset()
        if not self.web_mode:
            sys.stderr.write("Conversation history cleared\n")
            sys.stderr.flush()
    
    def close_session(self) -> None:
        """
        Close the current session and extract memories.
        Called when conversation ends (CLI exit, API session close).
        """
        try:
            # Get full conversation history from working memory
            conversation_history = self.memory.working_memory.copy()
            
            # Extract and consolidate memories
            self.memory.extract_and_consolidate(
                session_id=self.session_id,
                conversation_history=conversation_history
            )
            
            if not self.web_mode:
                print("✅ Memory extraction complete")
                
        except Exception as e:
            if not self.web_mode:
                print(f"⚠️ Memory extraction failed: {e}")