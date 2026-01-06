---
applyTo: "tools/native/**/*.py"
description: Standards for native tool development
---

## Native Tools Guidelines

These files implement Daagent's **core capabilities**. Tools must be production-ready and follow strict patterns.

### Tool Architecture (MANDATORY)

Every native tool must follow this exact structure:

```python
# tools/native/{toolname}.py

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def execute(query: str, **kwargs) -> str:
    """Execute {toolname} with provided query.
    
    Args:
        query: Primary input parameter
        **kwargs: Additional tool-specific parameters
    
    Returns:
        JSON string: {"status": "success", "results": [...], "count": N}
    
    Raises:
        ToolExecutionError: Only for critical failures
    """
    try:
        # 1. Input validation
        if not query or not query.strip():
            return json.dumps({"status": "error", "message": "Empty query"})
        
        # 2. Tool execution
        results = _do_the_thing(query, **kwargs)
        
        # 3. Result formatting
        return json.dumps({
            "status": "success",
            "results": results,
            "count": len(results)
        })
    
    except NetworkError as e:
        logger.error(f"{toolname} network error: {e}")
        return json.dumps({"status": "error", "message": f"Network failure: {e}"})
    
    except Exception as e:
        logger.error(f"{toolname} unexpected error: {e}")
        return json.dumps({"status": "error", "message": f"Execution failed: {e}"})

def _do_the_thing(query: str, **kwargs):
    """Internal implementation (not exposed to agent)."""
    # Implementation details
    pass

# OpenAI function schema (for agent registration)
FUNCTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "toolname",
        "description": "Clear description of what tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Primary input parameter"
                }
            },
            "required": ["query"]
        }
    }
}
```


### Return Value Requirements

#### ✅ Always Return JSON Strings

```python
# GOOD - Returns JSON string
return json.dumps({
    "status": "success",
    "results": [{"title": "Example", "url": "http://example.com"}],
    "count": 1
})

# BAD - Returns Python dict (breaks LLM parsing)
return {
    "status": "success",
    "results": [...]
}
```


#### ✅ Status Field Required

Every response must include a `status` field:

- `"status": "success"` - Tool executed successfully
- `"status": "error"` - Tool failed (with `message` field explaining why)


### Error Handling Standards

#### Specific Exception Types

```python
# ✅ GOOD - Specific exceptions
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.Timeout:
    logger.error(f"Timeout fetching {url}")
    return json.dumps({"status": "error", "message": "Request timeout"})
except requests.HTTPError as e:
    logger.error(f"HTTP {e.response.status_code} for {url}")
    return json.dumps({"status": "error", "message": f"HTTP {e.response.status_code}"})

# ❌ BAD - Bare except
try:
    risky_operation()
except:
    return json.dumps({"status": "error", "message": "Something went wrong"})
```


#### Graceful Degradation

Tools should fail gracefully, not crash the agent:

```python
# ✅ GOOD - Agent continues with error response
except Exception as e:
    logger.error(f"Tool execution failed: {e}")
    return json.dumps({"status": "error", "message": str(e)})

# ❌ BAD - Unhandled exception crashes agent
# (No try/except block)
```


### Function Schema Requirements

#### OpenAI Function Calling Format

```python
FUNCTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "toolname",  # Must match tool registration key
        "description": "Clear, actionable description",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",  # Use JSON schema types
                    "description": "What this parameter does"
                }
            },
            "required": ["param_name"]  # List required parameters
        }
    }
}
```


### Testing Requirements

Every tool must have comprehensive tests:

```python
# tests/test_{toolname}.py

def test_{toolname}_success():
    """Happy path test."""
    result = execute("valid input")
    assert json.loads(result)["status"] == "success"

def test_{toolname}_error_handling():
    """Error case test."""
    result = execute("invalid input")
    assert json.loads(result)["status"] == "error"

def test_{toolname}_edge_case():
    """Edge case test."""
    result = execute("edge case input")
    assert result is not None
```


### Tool Registration

After creating tool, register in `agent/core.py`:

```python
# agent/core.py

from tools.native import {toolname}

self.tools['{toolname}'] = ({toolname}.execute, {toolname}.FUNCTION_SCHEMA)
```


### Boundaries

#### ✅ Always Do

- Follow the architecture pattern exactly
- Return JSON strings (never dicts)
- Include comprehensive error handling
- Create FUNCTION_SCHEMA for OpenAI
- Use type hints and docstrings
- Register tool in agent/core.py


#### ⚠️ Ask First

- Adding new dependencies to requirements.txt
- Changing tool return format
- Creating tool that requires paid API


#### 🚫 Never Do

- Return Python objects (must be JSON strings)
- Skip input validation
- Hardcode API keys (use environment variables)
- Write tests yourself (hand off to QA Tester)
