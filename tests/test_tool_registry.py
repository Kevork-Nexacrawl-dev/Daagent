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
    
    # Should find our 3 tools
    assert len(tools) == 3
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
    assert len(schemas) == 3
    
    # Check web_search schema
    web_search_schema = registry.get_tool_schema('web_search')
    assert web_search_schema is not None
    assert web_search_schema['function']['name'] == 'web_search'
    assert 'query' in web_search_schema['function']['parameters']['properties']


def test_tool_registry_list():
    """Test tool listing functionality"""
    registry = ToolRegistry()
    registry.discover_tools()
    
    tool_names = registry.list_tools()
    assert len(tool_names) == 3
    assert 'web_search' in tool_names
    assert 'read_file' in tool_names
    assert 'write_file' in tool_names