---
applyTo: "agent/**/*.py"
description: Standards for core agent logic (ReAct loop, config, prompts)
---

## Agent Core Guidelines

These files implement Daagent's **core reasoning engine**. Changes here affect the entire system.

### Architecture Context
- `agent/core.py` - ReAct loop with tool calling (max 10 iterations)
- `agent/config.py` - Dynamic model selection, API clients
- `agent/prompts.py` - Layered prompt system (being refactored to YAML)

### Critical Principles

#### 1. Tool Calling Must Be Isolated
```python
# ✅ GOOD - Tool execution isolated with error handling
try:
    result = self.tools[tool_name](params)
except ToolNotFoundError:
    result = json.dumps({"status": "error", "message": f"Tool {tool_name} not found"})
except Exception as e:
    logger.error(f"Tool execution failed: {e}")
    result = json.dumps({"status": "error", "message": str(e)})

# ❌ BAD - No error handling, crashes agent
result = self.tools[tool_name](params)
```


#### 2. Iteration Limits Prevent Infinite Loops

```python
# ✅ GOOD - Explicit max iterations
iterations = 0
while not done and iterations < Config.MAX_ITERATIONS:
    iterations += 1
    response = self.llm.chat(messages, tools=self.tools)
    # ...

# ❌ BAD - No limit, can loop forever
while not done:
    response = self.llm.chat(messages, tools=self.tools)
```


#### 3. Model Selection Must Be Deterministic

```python
# ✅ GOOD - Clear task type → model mapping
def get_model_for_task(task_type: TaskType) -> str:
    if Config.OVERRIDE_MODEL:
        return Config.OVERRIDE_MODEL
    
    if Config.DEV_MODE:
        return Config.DEV_MODELS.get(task_type, Config.DEFAULT_DEV_MODEL)
    else:
        return Config.PROD_MODELS.get(task_type, Config.DEFAULT_PROD_MODEL)

# ❌ BAD - Ambiguous logic
def get_model(mode):
    return "grok-4-fast" if mode == "fast" else "deepseek"
```


### Testing Requirements

Every change to `agent/core.py` requires:

1. **Unit test:** Isolated function behavior
2. **Integration test:** Full ReAct loop with mocked tools
3. **Regression test:** Existing tests still pass

### Performance Constraints

- **Iteration limit:** 10 (default), configurable via `--max-iterations`
- **Token budget:** ~4K tokens per turn (context window management)
- **Tool execution:** <5s timeout per tool call


### Boundaries

#### ✅ Always Do

- Log all tool calls (`logger.info(f"Executing tool: {tool_name}")`)
- Handle tool failures gracefully (don't crash agent)
- Validate tool arguments before execution
- Track iteration count


#### ⚠️ Ask First

- Changing iteration limit default (affects all users)
- Modifying ReAct loop structure (core architecture)
- Adding new task types to `TaskType` enum


#### 🚫 Never Do

- Remove iteration limit (infinite loop risk)
- Skip tool argument validation
- Hardcode model names (use Config)
- Break backwards compatibility with existing tools
