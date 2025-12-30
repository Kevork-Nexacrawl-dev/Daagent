"""
Integration with existing MCP Module Manager warehouse.
Uses mcpmanager.py API for module discovery and management.
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


class MCPWarehouse:
    """Interface to existing MCP Module Manager"""

    def __init__(self, warehouse_path: str):
        """
        Initialize warehouse connection.

        Args:
            warehouse_path: Path to mcp-module-manager directory
        """
        self.warehouse_path = Path(warehouse_path)

        if not self.warehouse_path.exists():
            raise ValueError(f"MCP warehouse not found: {warehouse_path}")

        # Add warehouse to Python path to import mcp_manager
        sys.path.insert(0, str(self.warehouse_path))

        try:
            # Import the existing manager
            import mcp_manager
            self.manager = mcp_manager.EnhancedMCPModuleManager()
            print(f"📦 Connected to MCP Warehouse: {self.warehouse_path}")
        except ImportError as e:
            print(f"⚠️  MCP Warehouse not available: {e}")
            print("   Continuing with native tools only")
            self.manager = None

    def list_available_modules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available modules from warehouse.

        Returns:
            Dict of module_name -> module_info
        """
        if self.manager is None:
            return {}
        return self.manager.list_available_modules()

    def get_active_modules(self) -> List[str]:
        """
        Get currently loaded modules.

        Returns:
            List of active module names
        """
        if self.manager is None:
            return []
        return self.manager.get_active_modules()

    def load_module(self, module_name: str) -> Dict[str, Any]:
        """
        Load a module (activates its MCP server).

        Args:
            module_name: Name of module to load

        Returns:
            Result dict with status and details
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.load_module(module_name)

    def unload_module(self, module_name: str) -> Dict[str, Any]:
        """
        Unload a module.

        Args:
            module_name: Name of module to unload

        Returns:
            Result dict
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.unload_module(module_name)

    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """
        Get detailed info about a specific module.

        Args:
            module_name: Module name

        Returns:
            Module metadata including tools list
        """
        modules = self.list_available_modules()
        return modules.get(module_name, {})

    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """
        Use warehouse's AI to analyze task requirements.

        Args:
            task_description: User's task description

        Returns:
            Analysis with recommended modules
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.analyze_task_requirements(task_description)

    def adaptive_load(self, task_description: str) -> Dict[str, Any]:
        """
        Adaptively load modules based on task.

        Args:
            task_description: User's task

        Returns:
            Load result with modules activated
        """
        if self.manager is None:
            return {"status": "error", "message": "MCP warehouse not available"}
        return self.manager.adaptive_load_for_task(task_description)


class MCPToolAdapter:
    """
    Adapts MCP modules to OpenAI function calling format.
    Creates stub tools that show discovered MCP capabilities.
    """

    @staticmethod
    def create_tool_schema(module_name: str, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create OpenAI-format schema for MCP module.

        Args:
            module_name: Name of module
            module_info: Module metadata from warehouse

        Returns:
            OpenAI function schema
        """
        description = module_info.get("description", f"MCP module: {module_name}")
        tools = module_info.get("tools", [])
        tool_count = module_info.get("tools_count", len(tools))

        # Create schema that lists available tools
        return {
            "type": "function",
            "function": {
                "name": f"mcp_{module_name}",
                "description": f"{description} (Available tools: {', '.join(tools[:5])}{' ...' if len(tools) > 5 else ''}) [{tool_count} total tools]",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": f"Which tool to use. Available: {', '.join(tools)}",
                            "enum": tools if tools else ["info"]
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Arguments for the selected tool"
                        }
                    },
                    "required": ["tool_name"]
                }
            }
        }

    @staticmethod
    def execute_stub(module_name: str, args: Dict[str, Any], warehouse: MCPWarehouse) -> str:
        """
        Execute stub for MCP tool (Phase 1 - just shows info).

        Args:
            module_name: Module name
            args: Tool arguments (contains 'tool_name' and 'arguments')
            warehouse: Warehouse instance

        Returns:
            JSON response
        """
        # Extract the actual tool name and arguments from the function call
        requested_tool = args.get("tool_name", "unknown")
        tool_args = args.get("arguments", {})
        
        module_info = warehouse.get_module_info(module_name)
        active_modules = warehouse.get_active_modules()

        is_loaded = module_name in active_modules

        response = {
            "status": "stub",
            "module": module_name,
            "requested_tool": requested_tool,
            "tool_args": tool_args,
            "loaded": is_loaded,
            "message": f"MCP module '{module_name}' discovered from warehouse",
            "note": "Phase 1: Discovery complete. Phase 2 will enable real execution.",
            "available_tools": module_info.get("tools", []),
            "description": module_info.get("description", "")
        }

        if not is_loaded:
            response["hint"] = f"Module can be loaded with: warehouse.load_module('{module_name}')"

        return json.dumps(response, indent=2)