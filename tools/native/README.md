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

## Code Execution Tools

Daagent includes built-in support for executing code in multiple languages:

### Python Execution (`execute_python`)

Execute Python code with optional pip package installation:

```python
# Example usage through agent
python main.py "Execute Python: print('Hello from Daagent!')"

# With package installation
python main.py "Execute Python code that uses pandas for data analysis"
```

**Features:**
- Inline Python execution with `python -c`
- Automatic pip package installation
- 30-second timeout (configurable)
- Isolated workspace in `./workspace/python/`
- Returns stdout, stderr, and return code

### JavaScript Execution (`execute_javascript`)

Execute Node.js code with optional npm package installation:

```python
# Example usage
python main.py "Execute JavaScript: console.log('Hello from Node!')"

# With packages
python main.py "Execute JavaScript code that fetches web data"
```

**Features:**
- Node.js execution via temp files
- Automatic npm package installation
- Node.js availability checking
- 30-second timeout (configurable)
- Isolated workspace in `./workspace/javascript/`

### Bash Execution (`execute_bash`)

Execute Bash commands with comprehensive safety checks:

```python
# Safe commands
python main.py "Execute Bash: echo 'Hello World'"

# Dangerous commands (blocked by default)
python main.py "Execute Bash: rm -rf /"  # Will be blocked
```

**Features:**
- Bash command execution
- **Safety checks block dangerous operations:**
  - Filesystem destruction (`rm -rf /`, `dd`, `mkfs`)
  - System shutdown/reboot
  - Fork bombs and resource exhaustion
  - Privilege escalation
  - Remote code execution
- `allow_dangerous=True` flag to bypass (use with caution)
- 30-second timeout (configurable)
- Isolated workspace in `./workspace/bash/`

### PowerShell Execution (`execute_powershell`)

Execute PowerShell commands with safety checks for Windows environments:

```python
# Safe commands
python main.py "Execute PowerShell: Get-ChildItem *.py"

# Dangerous commands (blocked by default)
python main.py "Execute PowerShell: Remove-Item C:\ -Recurse -Force"  # Will be blocked
```

**Features:**
- PowerShell Core (`pwsh`) preferred, falls back to Windows PowerShell
- **Safety checks block dangerous operations:**
  - Filesystem destruction (`Remove-Item -Recurse -Force C:\`)
  - System operations (`Stop-Computer`, `Restart-Computer`)
  - Remote code execution (`Invoke-WebRequest | Invoke-Expression`)
  - Privilege escalation (`Start-Process -Verb RunAs`)
  - Registry operations (`Remove-Item HKLM:\`)
- `allow_dangerous=True` flag to bypass (use with caution)
- 30-second timeout (configurable)
- Isolated workspace in `./workspace/powershell/`

### SQL Execution (`execute_sql`)

Execute SQL queries against multiple database types:

```python
# SQLite (default)
python main.py "Execute SQL: CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"

# PostgreSQL
python main.py "Execute SQL query on PostgreSQL database"

# MySQL
python main.py "Execute SQL query on MySQL database"
```

**Features:**
- **Database support:** SQLite (default), PostgreSQL, MySQL
- **SQLite:** Auto-creates databases in `./workspace/sql/`
- **Connection parameters:** host, port, database, username, password
- **Query types:** SELECT (returns rows), DML (returns affected rows)
- **Structured results:** rows array, row_count, affected_rows, execution_time_ms
- 30-second timeout (configurable)
- Proper connection cleanup

### Docker Execution (`execute_docker`)

Execute Docker container management commands:

```python
# List containers
python main.py "Execute Docker: list all running containers"

# Run a container
python main.py "Execute Docker: run nginx container"

# Build an image
python main.py "Execute Docker: build image from current directory"
```

**Features:**
- **Operations:** build, run, exec, ps, logs, stop, rm
- **Safety checks block dangerous operations:**
  - Privileged mode (`--privileged`)
  - Host network access (`--network=host`)
  - Dangerous mounts (`-v /:/host`)
- `allow_dangerous=True` flag to bypass (use with caution)
- 60-second timeout (configurable, longer for builds)
- Isolated workspace in `./workspace/docker/`
- Auto-pull missing images
- Auto-remove containers (`--rm` flag)

### Security Notes

- **Bash safety is conservative** - many legitimate admin commands may be blocked
- Use `allow_dangerous=True` only when absolutely necessary
- All execution happens in isolated workspace directories
- Timeouts prevent infinite loops and hanging processes
- Package installations are cached per workspace