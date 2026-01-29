"""
MCP Tool Adapters for Daagent.

This module contains adapters that convert MCP modules to OpenAI function calling format.
"""

import json
from typing import Dict, Any

from ..warehouse import MCPWarehouse


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
    def execute_stub(module_name: str, kwargs: Dict[str, Any], warehouse: MCPWarehouse) -> str:
        """
        Execute stub for MCP tool (Phase 1 - just shows info).

        Args:
            module_name: Module name
            kwargs: Tool arguments (contains 'tool_name' and 'arguments')
            warehouse: Warehouse instance

        Returns:
            JSON response
        """
        # Extract the actual tool name and arguments from the function call
        requested_tool = kwargs.get("tool_name", "unknown")
        tool_args = kwargs.get("arguments", {})

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
