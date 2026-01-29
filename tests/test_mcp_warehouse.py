"""
Tests for MCP warehouse integration.
"""

import pytest
import json
from unittest.mock import Mock, patch
from tools.mcp.warehouse import MCPWarehouse
from tools.mcp.adapters import MCPToolAdapter


def test_mcp_warehouse_unavailable():
    """Test warehouse handles missing mcpmanager gracefully"""
    # Mock the path existence check and import
    with patch('pathlib.Path.exists', return_value=True), \
         patch('builtins.__import__', side_effect=ImportError("No module named 'mcpmanager'")):
        warehouse = MCPWarehouse(r"C:\nonexistent\path")
        assert warehouse.manager is None
        assert warehouse.list_available_modules() == {}
        assert warehouse.get_active_modules() == []


def test_mcp_warehouse_available():
    """Test warehouse when mcpmanager is available"""
    mock_manager = Mock()
    mock_manager.list_available_modules.return_value = {
        "filesystem": {"description": "File operations", "tools": ["read_file", "write_file"], "tools_count": 2},
        "github": {"description": "GitHub operations", "tools": ["create_repo"], "tools_count": 1}
    }
    mock_manager.get_active_modules.return_value = ["filesystem"]

    with patch('tools.mcp.warehouse.MCPWarehouse.__init__', return_value=None):
        warehouse = MCPWarehouse.__new__(MCPWarehouse)
        warehouse.manager = mock_manager

        modules = warehouse.list_available_modules()
        assert len(modules) == 2
        assert "filesystem" in modules
        assert "github" in modules

        active = warehouse.get_active_modules()
        assert active == ["filesystem"]


def test_mcp_tool_adapter_create_schema():
    """Test creating OpenAI schema from MCP module info"""
    module_info = {
        "description": "File system operations",
        "tools": ["read_file", "write_file", "list_dir"],
        "tools_count": 3
    }

    schema = MCPToolAdapter.create_tool_schema("filesystem", module_info)

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "mcp_filesystem"
    assert "File system operations" in schema["function"]["description"]
    assert "read_file, write_file, list_dir" in schema["function"]["description"]
    assert "[3 total tools]" in schema["function"]["description"]

    # Check parameters
    params = schema["function"]["parameters"]
    assert params["type"] == "object"
    assert "tool_name" in params["properties"]
    assert params["required"] == ["tool_name"]


def test_mcp_tool_adapter_execute_stub():
    """Test stub execution for MCP tools"""
    mock_warehouse = Mock()
    mock_warehouse.get_module_info.return_value = {
        "description": "Test module",
        "tools": ["test_tool"]
    }
    mock_warehouse.get_active_modules.return_value = []

    result_json = MCPToolAdapter.execute_stub("test_module", {"tool_name": "test_tool"}, mock_warehouse)
    result = json.loads(result_json)  # Parse the JSON string

    assert result["status"] == "stub"
    assert result["module"] == "test_module"
    assert result["requested_tool"] == "test_tool"
    assert result["loaded"] == False
    assert "Phase 1: Discovery complete" in result["note"]
    assert "hint" in result