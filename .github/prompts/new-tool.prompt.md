---
agent: "tool-architect"
tools: ["read", "search", "web/githubRepo"]
description: Scaffold a new native tool with tests and registration
---

# New Tool Scaffolding

**Tool name:** {input:toolName|What tool are you building? (e.g., 'perplexity', 'codeexecution')}  
**Description:** {input:description|What does this tool do?}  
**Dependencies:** {input:dependencies|Any new packages needed? (comma-separated)}

## Requirements

### Step 1: Create Tool File
Create `tools/native/{toolName}.py` with:
- `execute()` function following architecture pattern
- OpenAI function schema in `FUNCTION_SCHEMA`
- Type hints and docstrings
- Error handling for common failures
- JSON string return format

### Step 2: Add Dependencies
If new packages needed:
- Add to `requirements.txt`
- Run `pip install -r requirements.txt` in venv

### Step 3: Register Tool
Add to `agent/core.py` tool registry:
```python
from tools.native import {toolName}

self.tools['{toolName}'] = ({toolName}.execute, {toolName}.FUNCTION_SCHEMA)
```


### Step 4: Hand Off to QA Tester

Create handoff: "Test {toolName} tool with happy/error/edge cases"

## Success Criteria

- [ ] Tool file created with proper structure
- [ ] Dependencies added to requirements.txt
- [ ] Tool registered in agent/core.py
- [ ] FUNCTION_SCHEMA valid OpenAI format
- [ ] Returns JSON string (not dict)
- [ ] Error handling for network/file/API failures
- [ ] Ready for QA Tester to write tests
