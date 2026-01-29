"""
Tool registry for auto-discovery of agent tools.
Automatically discovers and registers tools from tools/native/ directory.
"""

import importlib
import inspect
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from agent.errors import classify_error, FatalError, RetryableError, AllFallbacksFailed
from agent.retry_manager import RetryManager
from agent.fallback_manager import FallbackManager

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for automatically discovering and managing agent tools.
    
    Tools must follow the standard interface:
    - TOOL_SCHEMA: OpenAI function calling schema (dict)
    - TOOL_SCHEMAS: List of schemas for multi-function tools (optional)
    - execute_tool: Function that takes **kwargs and returns str
    """
    
    def __init__(self, tools_dir: str = "tools/native"):
        """
        Initialize tool registry.
        
        Args:
            tools_dir: Directory to scan for tools (relative to project root)
        """
        self.web_mode = os.getenv('DAAGENT_WEB_MODE') == '1'
        self.tools_dir = Path(tools_dir)
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._discovered = False
        
        # NEW: Add error handling components
        self.retry_manager = RetryManager(max_retries=3)
        self.fallback_manager = FallbackManager()
    
    def discover_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover and register all tools in the tools directory.
        
        Returns:
            Dictionary mapping tool names to tool info
        """
        if self._discovered:
            return self.tools
            
        logger.info(f"Discovering tools in {self.tools_dir}")
        
        if not self.tools_dir.exists():
            logger.warning(f"Tools directory {self.tools_dir} does not exist")
            return self.tools
            
        # Find all Python files in tools directory
        tool_files = list(self.tools_dir.glob("*.py"))
        tool_files = [f for f in tool_files if not f.name.startswith("__")]
        
        for tool_file in tool_files:
            try:
                self._load_tool_from_file(tool_file)
            except Exception as e:
                logger.error(f"Failed to load tool from {tool_file}: {e}")
                continue
                
        self._discovered = True
        logger.info(f"Discovered {len(self.tools)} tools")
        return self.tools
    
    def _load_tool_from_file(self, tool_file: Path) -> None:
        """
        Load a tool from a Python file.
        
        Args:
            tool_file: Path to the tool file
        """
        module_name = f"tools.native.{tool_file.stem}"
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Check for TOOL_SCHEMAS (multi-function tools like file_ops)
            if hasattr(module, 'TOOL_SCHEMAS'):
                schemas = getattr(module, 'TOOL_SCHEMAS')
                if isinstance(schemas, list):
                    for schema in schemas:
                        self._register_tool_schema(schema, module)
                else:
                    logger.warning(f"TOOL_SCHEMAS in {module_name} should be a list")
                    
            # Check for single TOOL_SCHEMA
            elif hasattr(module, 'TOOL_SCHEMA'):
                schema = getattr(module, 'TOOL_SCHEMA')
                self._register_tool_schema(schema, module)
                
            else:
                logger.warning(f"No TOOL_SCHEMA or TOOL_SCHEMAS found in {module_name}")
                
        except ImportError as e:
            logger.error(f"Failed to import {module_name}: {e}")
    
    def _register_tool_schema(self, schema: Dict[str, Any], module) -> None:
        """
        Register a tool schema.
        
        Args:
            schema: OpenAI function calling schema
            module: The imported module containing the tool
        """
        if not isinstance(schema, dict) or 'function' not in schema:
            logger.warning(f"Invalid schema format: {schema}")
            return
            
        tool_name = schema['function']['name']
        
        # For multi-function tools (like file_ops), try to find the specific function
        if hasattr(module, tool_name):
            execute_func = getattr(module, tool_name)
            if callable(execute_func):
                # Use the specific function (e.g., read_file, write_file)
                pass
            else:
                logger.warning(f"{tool_name} is not callable in {module.__name__}")
                return
        # Check if execute_tool function exists (for single-function tools or dispatchers)
        elif hasattr(module, 'execute_tool'):
            execute_func = getattr(module, 'execute_tool')
            # For multi-function dispatchers, we need to pass the operation
            if hasattr(module, 'TOOL_SCHEMAS'):
                # Create a wrapper that adds the operation parameter
                def make_dispatcher(op_name):
                    def dispatcher(*args, **kwargs):
                        return execute_func(op_name, *args, **kwargs)
                    return dispatcher
                execute_func = make_dispatcher(tool_name)
        else:
            logger.warning(f"No execute function found for {tool_name}")
            return
            
        # Register the tool
        self.tools[tool_name] = {
            'schema': schema,
            'execute_func': execute_func,
            'module': module.__name__
        }
        
        logger.debug(f"Registered tool: {tool_name}")
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool schema or None if not found
        """
        tool_info = self.tools.get(tool_name)
        return tool_info['schema'] if tool_info else None
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all tool schemas.
        
        Returns:
            List of all tool schemas
        """
        return [tool_info['schema'] for tool_info in self.tools.values()]
    
    def execute_tool(self, tool_name_param: str, **kwargs) -> str:
        """
        Execute a tool by name.
        
        Args:
            tool_name_param: Name of the tool to execute
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Tool execution result as string
        """
        tool_info = self.tools.get(tool_name_param)
        if not tool_info:
            return json.dumps({
                "status": "error",
                "message": f"Unknown tool '{tool_name_param}'"
            })
            
        try:
            return tool_info['execute_func'](**kwargs)
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name_param}: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Tool execution failed: {str(e)}"
            })
    
    def list_tools(self) -> List[str]:
        """
        List all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
    
    def discover_mcp_warehouse(self, warehouse_path: str) -> None:
        """
        Discover MCP modules from warehouse and register as tools.
        
        Args:
            warehouse_path: Path to mcp-module-manager directory
        """
        try:
            from tools.mcp.warehouse import MCPWarehouse
            from tools.mcp.adapters import MCPToolAdapter
            
            # Connect to warehouse
            self.warehouse = MCPWarehouse(warehouse_path)
            
            # Get all available modules
            modules = self.warehouse.list_available_modules()
            
            if not self.web_mode:
                sys.stderr.write(f"📦 Discovered {len(modules)} MCP modules from warehouse\n")
                sys.stderr.flush()
            
            # Register each module as a tool
            for module_name, module_info in modules.items():
                try:
                    # Create OpenAI schema
                    schema = MCPToolAdapter.create_tool_schema(module_name, module_info)
                    tool_name = schema["function"]["name"]
                    
                    # Create executor closure
                    def make_executor(mname):
                        def executor(**kwargs):
                            return MCPToolAdapter.execute_stub(mname, kwargs, self.warehouse)
                        return executor
                    
                    # Register in tools dict
                    self.tools[tool_name] = {
                        'schema': schema,
                        'execute_func': make_executor(module_name),
                        'module': f"mcp_{module_name}"
                    }
                    
                    tool_count = module_info.get("tools_count", len(module_info.get("tools", [])))
                    if not self.web_mode:
                        sys.stderr.write(f"   🔧 {tool_name}: {tool_count} tools\n")
                        sys.stderr.flush()
                
                except Exception as e:
                    if not self.web_mode:
                        sys.stderr.write(f"   ⚠️  Failed to register {module_name}: {e}\n")
                        sys.stderr.flush()
        
        except Exception as e:
            if not self.web_mode:
                sys.stderr.write(f"⚠️  Warehouse discovery failed: {e}\n")
                sys.stderr.write("   Native tools still available\n")
                sys.stderr.flush()
            import traceback
            traceback.print_exc()
    
    def execute_tool_safe(self, tool_name: str, use_fallbacks=True, **kwargs) -> str:
        """
        Execute tool with retry logic and fallbacks.
        
        Args:
            tool_name: Tool name
            use_fallbacks: Whether to use fallback strategies
            **kwargs: Tool arguments
            
        Returns:
            Tool result (JSON string)
        """
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Try with retries first
            result = self.retry_manager.execute_with_retry(
                self.execute_tool, tool_name, **kwargs
            )
            return result
            
        except FatalError:
            # Fatal errors don't get fallbacks
            raise
            
        except (RetryableError, Exception) as e:
            if not use_fallbacks:
                raise
            
            # Try fallback strategies
            logger.info(f"Primary tool failed, trying fallbacks...")
            try:
                result = self.fallback_manager.execute_with_fallbacks(
                    self, tool_name, kwargs
                )
                return result
            except AllFallbacksFailed as fallback_error:
                # Return user-friendly error message
                return json.dumps({
                    "success": False,
                    "error": f"All strategies failed for {tool_name}",
                    "attempts": fallback_error.errors
                })