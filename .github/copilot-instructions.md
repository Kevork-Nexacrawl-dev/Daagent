# Daagent Development Guidelines

## Project Overview
Daagent is a general-purpose AI agent system with dynamic model selection, prompt layering, and extensible tools. Currently in **Phase 3 (Tools + CLI Complete)**, moving to **Phase 4 (Scalability)**.

**Philosophy:** "Be a DOER, not an ASKER." Agents should proactively solve problems with minimal hand-holding.

## Current Architecture

### Core Components
- `agent/core.py` - ReAct loop with tool calling (max 10 iterations)
- `agent/config.py` - Dynamic model selection, API clients
- `agent/prompts.py` - Layered prompt system (**needs YAML refactor**)

### Tools
- `tools/native/websearch.py` - DuckDuckGo search with JSON results
- `tools/native/fileops.py` - Read/write files with security checks
- `tools/mcp/` - **NOT IMPLEMENTED** (Phase 4 priority)
- `tools/autogen/` - **NOT IMPLEMENTED** (47 tools to port)

### Tech Stack
- **Python:** 3.11+
- **LLMs:** OpenRouter (DeepSeek V3 free, Grok 4 Fast), Anthropic Claude
- **Libraries:** openai (client), duckduckgo-search, rich (CLI), pydantic (validation)
- **Testing:** pytest, pytest-asyncio
- **Environment:** Windows PowerShell, VS Code, venv at `daagent/venv`

## Current Phase Status

### ✅ Phase 3 Complete
- CLI interface (`main.py`) with interactive/single-query modes
- Native tools (web search, file ops)
- Tool registry system
- Tests passing (`tests/test_basic.py`, `tests/test_websearch.py`, `tests/test_fileops.py`)

### 🔄 Phase 4 In Progress (Critical Path)
1. **PRIORITY 1:** Refactor `agent/prompts.py` to YAML-based system
   - Move prompts from Python strings to `prompts/core/*.yaml`
   - Implement `PromptManager` with priority-based loading
   - Target: Non-technical users can edit behavior via YAML
2. **PRIORITY 2:** MCP bridge (`tools/mcp/`)
   - Connect to C:\c-module-manager MCP warehouse
   - Auto-discover available MCP tools
   - Translate MCP schemas → OpenAI function calling format
3. **PRIORITY 3:** Ephemeral workers (`agent/worker.py`)
   - Main agent spawns sub-agents for parallel tasks
   - Workers are specialized, ephemeral, self-destructing
   - See `future_implementations/approved/001_ephemeral_workers.md`

## Coding Standards

### Type Hints & Docstrings (MANDATORY)
```python
def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Execute a tool by name with provided arguments.
    
    Args:
        name: Tool identifier (e.g., 'websearch')
        args: Tool-specific parameters
    
    Returns:
        Tool execution result as JSON string
    
    Raises:
        ToolExecutionError: If tool execution fails
    """
    try:
        # Implementation
        pass
    except KeyError as e:
        logger.error(f"Tool {name} not found: {e}")
        raise ToolNotFoundError(f"Unknown tool: {name}")
```

### Error Handling

- ✅ **Always:** Specific exceptions, not bare `except:`
- ✅ **Always:** Logging for debugging (`logger.info/error/debug`)
- ✅ **Always:** Graceful degradation (tool fails → inform user, continue)

### Testing Requirements

Every tool MUST have:

1. **Happy path test (normal usage)
2. **Error case test (failure handling)
3. **Edge case test (boundary conditions)

Example:

```python
def test_websearch_success():
    result = execute_search("AI news")
    assert len(result) > 0
    assert "http" in result

def test_websearch_network_failure():
    with patch('duckduckgo_search.DDGS') as mock:
        mock.side_effect = NetworkError()
        result = execute_search("test")
        assert "error" in result.lower()
```

### Tool Return Values

- ✅ **Always return strings** (LLMs consume text, not objects)
- ✅ **Use JSON for structured data:**

```python
return json.dumps({
"status": "success",
"results": [...],
"count": 5
})
```

- ❌ **NEVER return dicts directly** (breaks LLM parsing)

## Architecture Principles

### 1. Scalability Over Quick Hacks

Ask: "Will this work with 100 tools? 1000 users?"

- ✅ **Good:** YAML-based prompts (non-technical edits)
- ❌ **Bad:** Hardcoded prompts in Python (requires dev)

### 2. Prompt Engineering as First-Class Feature

User behavior control happens through **prompt layers, NOT code changes**.

- Benefits: Non-devs customize, rapid experimentation, version control

### 3. Graceful Degradation

Tools should fail gracefully. Agent adapts when tools unavailable.

- Web search fails → Use cached data or inform user
- File write fails → Store in memory and retry

### 4. Explicit Over Implicit

Code should be readable. Architecture obvious.

- ✅ **Good:** `Config.get_model_for_task(TaskType.CONVERSATIONAL)`
- ❌ **Bad:** `get_model("chat")`

## Decision Framework

When faced with architectural choices, evaluate:

1. **Scalability:** Will this work with 100 tools? 1000 users? Multiple agents?
2. **Maintainability:** Can future developer modify without breaking things?
3. **Performance:** Does this add latency? Token cost? API calls?
4. **User Experience:** Does this make agent more predictable/controllable?

**Tie-breaker:** Choose simpler solution. Complexity must justify itself.

## Project Constraints

### APIs/Services (DO NOT USE THESE)

- ❌ OpenRouter: DeepSeek Computer Use models (not stable)
- ❌ Anthropic: Claude Computer Use API (Phase 5 only, premature)
- ❌ MCP servers at C:\c-module-manager (Phase 4, not Phase 3)

### Cost Sensitivity

- Develop with **free models:** `nex-agi/deepseek-v3.1-nex-n1:free`
- Switch to paid only when necessary
- Monitor token usage
- User prefers free tier where possible

## Important Files

### Read These for Context

- `AGENTS.MD` - AI collaboration philosophy (read this first!)
- `DAAGENT.MD` - Project context for Perplexity (being deprecated)
- `future_implementations/approved/` - Green-lit features ready to build
- `memory-bank/latest.md` - Most recent session summary

### Never Commit

- `.env` - API keys
- `daagent/venv/` - Virtual environment
- `__pycache__/` - Python cache files

## Anti-Patterns (NEVER DO THIS)

### Generic Advice

- ❌ "You should add error handling" → Tell HOW for THIS project
- ❌ Incomplete code with `# TODO: implement this` → Finish it or don't start
- ❌ Assumed knowledge "Just use the standard pattern" → Show the code

### Engineering Mistakes

- ❌ Over-engineering: Don't add abstraction until 3+ use cases exist
- ❌ Silent failures: Every error must be logged or raised
- ❌ Magic numbers: Use named constants (`MAX_RETRIES = 3` not `range(3)`)
- ❌ Hardcoded paths: Use config/env vars for file paths, API endpoints

## Version History

- **1.0** (2025-12-25): Initial version from AGENTS.MD
- **1.1** (2026-01-02): Updated for GitHub Copilot custom agents

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
