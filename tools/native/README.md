# Tool Development Guide

This guide explains how to create new tools for Daagent that will be automatically discovered and registered.

## Tool Interface Standard

All tools must follow this standard interface to be auto-discovered:

### Required Components

1. **TOOL_SCHEMA** or **TOOL_SCHEMAS**: OpenAI function calling schema(s)
2. **execute_tool** function: Main entry point for tool execution

### Single-Function Tools

For tools with one function (like `web_search`):

```python
# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "your_tool_name",
        "description": "What your tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",
                    "description": "Parameter description"
                }
            },
            "required": ["param_name"]
        }
    }
}

def execute_tool(**kwargs) -> str:
    """
    Execute the tool with given arguments.
    
    Args:
        **kwargs: Tool parameters
        
    Returns:
        JSON string result
    """
    # Your implementation here
    return json.dumps({"status": "success", "result": "..."})
```

### Multi-Function Tools

For tools with multiple functions (like `file_ops` with read/write):

```python
# Individual schemas for each function
READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read file contents",
        "parameters": {...}
    }
}

WRITE_FILE_SCHEMA = {
    "type": "function", 
    "function": {
        "name": "write_file",
        "description": "Write to file",
        "parameters": {...}
    }
}

# List of all schemas for auto-discovery
TOOL_SCHEMAS = [READ_FILE_SCHEMA, WRITE_FILE_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute tool operation.
    
    Args:
        operation: Which operation to perform
        **kwargs: Operation parameters
        
    Returns:
        JSON string result
    """
    if operation == "read_file":
        return read_file(**kwargs)
    elif operation == "write_file":
        return write_file(**kwargs)
    else:
        return json.dumps({"status": "error", "message": f"Unknown operation: {operation}"})
```

## Tool Return Values

**All tools must return strings** (JSON-formatted for complex data):

```python
# Good - returns JSON string
return json.dumps({
    "status": "success",
    "data": result_data,
    "count": len(results)
})

# Bad - returns dict/object
return {"status": "success", "data": result_data}
```

## File Location

Place tool files in `tools/native/your_tool_name.py`

## Auto-Discovery

Tools are automatically discovered when the agent starts. No manual registration needed!

## Example: Adding a Calculator Tool

```python
# tools/native/calculator.py

import json
from typing import Dict, Any

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')"
                }
            },
            "required": ["expression"]
        }
    }
}

def execute_tool(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: Math expression as string
        
    Returns:
        JSON result with calculation
    """
    try:
        # Use eval safely (in production, use a proper math parser)
        result = eval(expression, {"__builtins__": {}})
        
        return json.dumps({
            "status": "success",
            "expression": expression,
            "result": result
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Calculation failed: {str(e)}",
            "expression": expression
        })
```

That's it! The tool will be automatically discovered and available to the agent.