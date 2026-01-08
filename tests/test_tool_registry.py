"""
Tests for tool registry auto-discovery functionality.
"""

import pytest
from agent.tool_registry import ToolRegistry


def test_tool_registry_discovery():
    """Test that tool registry discovers tools correctly"""
    registry = ToolRegistry()
    
    # Discover tools
    tools = registry.discover_tools()
    
    # Should find our native tools (53+ as of current implementation)
    assert len(tools) >= 50  # Allow for future tool additions
    assert "read_file" in tools
    assert "write_file" in tools
    assert "web_search" in tools
    assert 'web_search' in tools
    assert 'read_file' in tools
    assert 'write_file' in tools
    
    # Check schemas are present
    for tool_name, tool_info in tools.items():
        assert 'schema' in tool_info
        assert 'execute_func' in tool_info
        assert 'module' in tool_info
        assert tool_info['schema']['function']['name'] == tool_name


def test_tool_registry_execution():
    """Test that tool registry can execute tools"""
    registry = ToolRegistry()
    registry.discover_tools()
    
    # Test web search
    result = registry.execute_tool('web_search', query='test', max_results=1)
    assert '"status": "success"' in result
    assert '"query": "test"' in result
    
    # Test unknown tool
    result = registry.execute_tool('unknown_tool')
    assert '"status": "error"' in result
    assert 'Unknown tool' in result


def test_tool_registry_schemas():
    """Test that tool registry provides correct schemas"""
    registry = ToolRegistry()
    registry.discover_tools()
    
    schemas = registry.get_all_schemas()
    assert len(schemas) >= 50  # Allow for future tool additions
    
    # Check that schemas have required OpenAI format
    for schema in schemas:
        assert "type" in schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]


def test_tool_registry_list():
    """Test tool listing functionality"""
    registry = ToolRegistry()
    registry.discover_tools()
    
    tool_names = registry.list_tools()
    assert len(tool_names) >= 50  # Allow for future tool additions
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "web_search" in tool_names
    assert 'web_search' in tool_names
    assert 'read_file' in tool_names
    assert 'write_file' in tool_names