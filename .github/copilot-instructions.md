## 4. .github/copilot-instructions.md

```markdown
# Copilot Instructions for Daagent

Project-specific conventions and patterns for GitHub Copilot when working in this codebase.

---

## Project Overview

**Daagent** is a general-purpose AI agent with:
- Dynamic model selection (free dev → paid prod)
- Prompt layering for behavior control
- Extensible tool system (native + MCP + autogen)
- ReAct pattern (reasoning + action loops)

---

## File Structure

```

agent/          \# Core agent logic
core.py       \# Main ReAct loop, tool calling
config.py     \# Model selection, API clients
prompts.py    \# Layered prompt system

tools/          \# Agent capabilities
native/       \# Custom tools (web_search, file_ops)
mcp/          \# MCP ecosystem bridge (future)
autogen/      \# Ported autogen-shop tools (future)

tests/          \# Test suite
test_*.py     \# Unit tests for each module

```

---

## Coding Conventions

### Type Hints (Required)

```

def execute_tool(name: str, args: Dict[str, Any]) -> str:
pass

```

### Docstrings (Google Style)

```

def execute_tool(name: str, args: Dict[str, Any]) -> str:
"""
Execute a tool by name with provided arguments.

    Args:
        name: Tool identifier (e.g., "web_search")
        args: Tool-specific parameters
    
    Returns:
        Tool execution result as string
    
    Raises:
        ToolNotFoundError: If tool doesn't exist
    """
    ```

### Error Handling

```

try:
result = risky_operation()
except SpecificException as e:
logger.error(f"Operation failed: {e}")
raise CustomError(f"Context: {e}")

```

### Imports

Use absolute imports:
```

from agent.core import UnifiedAgent
from agent.config import Config, TaskType
from tools.native.web_search import execute_search

```

---

## Key Patterns

### Model Selection

Never hardcode model names. Use:
```

model = Config.get_model_for_task(TaskType.CONVERSATIONAL)

```

### Tool Return Values

Tools MUST return strings (not dicts):
```


# Good

return json.dumps({"status": "success", "data": [...]})

# Bad

return {"status": "success"}

```

### Tool Schema Format

Follow OpenAI function calling format:
```

TOOL_SCHEMA = {
"type": "function",
"function": {
"name": "tool_name",
"description": "Clear description",
"parameters": {
"type": "object",
"properties": {
"param": {"type": "string", "description": "What it does"}
},
"required": ["param"]
}
}
}

```

### Prompt Layers

Current (Python):
```

prompt_manager.add_layer("name", "content", priority=50)

```

Future (YAML) - Not yet implemented:
```

name: "layer_name"
priority: 50
content: |
Prompt content...

```

---

## Testing Standards

Every tool needs tests:
```


# tests/test_tool_name.py

def test_tool_success():
"""Test normal operation"""
result = execute_tool("input")
assert "expected" in result

def test_tool_error_handling():
"""Test error cases"""
with pytest.raises(ToolError):
execute_tool("invalid_input")

```

---

## Common Tasks

### Adding a New Tool

1. Create `tools/native/tool_name.py`
2. Implement `execute_tool_name(args) -> str`
3. Define `TOOL_SCHEMA` in OpenAI format
4. Register in `agent/core.py` `_execute_tool()`
5. Create `tests/test_tool_name.py`

### Changing Model

In `.env`:
```

DEV_MODE=false  \# Use prod models
OPENROUTER_MODEL=x-ai/grok-4-fast  \# Override specific model

```

### Running Tests

```

python tests/test_basic.py
python -m pytest tests/  \# When pytest available

```

---

## Anti-Patterns

❌ Hardcoded model names  
❌ Tools returning dicts (must be strings)  
❌ Missing type hints  
❌ Incomplete docstrings  
❌ Silent error swallowing  
❌ Magic numbers (use constants)  

---

## Dependencies

```

openai           \# For OpenRouter API
python-dotenv    \# For .env loading
duckduckgo-search \# For web_search tool
anthropic        \# For Computer Use (future)

```

---

## Environment

- **Python**: 3.11
- **OS**: Windows (PowerShell)
- **Venv**: `daagent/venv`
- **IDE**: VS Code

---

Read `AGENTS.MD` for full project philosophy and collaboration guidelines.