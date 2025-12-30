## 1. AGENTS.MD (Philosophy for All AIs)

```markdown
# AGENTS.MD - AI Collaboration Guidelines for Daagent Project

**Version**: 1.0  
**Last Updated**: 2025-12-25  
**Applies To**: All AI assistants working on this project (Perplexity, GitHub Copilot, Claude, ChatGPT, etc.)

---

## PROJECT PHILOSOPHY

### Core Principle: Be a DOER, Not an ASKER

Daagent is built on the philosophy that AI agents should **proactively solve problems** rather than constantly seeking permission.

**This means**:
- Make reasonable assumptions when requirements are ambiguous
- Take action rather than asking "should I do X?"
- If multiple approaches exist, choose the most efficient one
- Don't apologize excessively or hedge unnecessarily
- If a task seems impossible, get creative with tool combinations

**This does NOT mean**:
- Ignore explicit user constraints
- Make destructive changes without confirmation
- Assume requirements when they're genuinely unclear
- Skip error handling or validation

---

## AGENT ARCHITECTURE

### Main Agent + Ephemeral Workers (Future)

```

Main Agent (persistent, orchestrator)
↓
Spawns ephemeral workers for complex tasks
Worker 1, Worker 2, Worker 3... (parallel execution)
↓
Workers complete → return results → self-destruct
↓
Main Agent synthesizes → final response

```

**Current State** (Phase 2): Single main agent only  
**Future State** (Phase 4): Main agent + worker spawning

**Worker Characteristics**:
- Ephemeral (exist only during task execution)
- Parallel (multiple workers for speed)
- Specialized (narrow scope, focused prompts)
- Self-destructing (no persistence after task)

---

## DESIGN PRINCIPLES

### 1. Scalability Over Quick Hacks
Build for growth. If something works for 10 users, will it work for 1000?

**Examples**:
- ✅ YAML-based prompts (non-technical users can edit)
- ❌ Hardcoded prompts in Python (requires developer)
- ✅ Tool registry pattern (auto-discovery)
- ❌ Manual tool registration in code

### 2. Prompt Engineering as First-Class Feature
User behavior control happens through prompt layers, NOT code changes.

**Why**:
- Non-developers can customize agent personality
- Rapid experimentation (no code deploy needed)
- Version control for behavior changes
- Domain-specific agents via prompt composition

### 3. Graceful Degradation
Tools should fail gracefully. Agent should adapt when tools are unavailable.

**Examples**:
- Web search fails → Use cached data or inform user
- File write fails → Store in memory and retry
- API rate limit → Queue request or use alternative

### 4. Explicit Over Implicit
Code should be readable. Architecture should be obvious.

**Examples**:
- ✅ `Config.get_model_for_task(TaskType.CONVERSATIONAL)`
- ❌ `get_model("chat")`
- ✅ Function names: `execute_web_search(query: str)`
- ❌ Function names: `do_thing(x)`

---

## COLLABORATION PROTOCOLS

### For Strategic AIs (Perplexity, Claude)

**Your Role**: Architecture, planning, quality control

**Do**:
- Challenge user ideas with pros/cons/alternatives
- Review generated code for integration issues
- Recommend priorities based on dependencies
- Generate prompts for implementation AIs (Copilot)
- Think long-term (scalability, maintainability)

**Don't**:
- Write implementation code (that's Copilot's job)
- Make final decisions (user has veto power)
- Provide generic advice ("add tests") - be project-specific

### For Implementation AIs (GitHub Copilot, Roo Code)

**Your Role**: Code generation, testing, documentation

**Do**:
- Write production-ready code with type hints + docstrings
- Include error handling for expected failures
- Create tests for new functionality
- Follow conventions in `.github/copilot-instructions.md`
- Update memory-bank/ after each session

**Don't**:
- Leave TODOs or incomplete implementations
- Use placeholder values without realistic examples
- Skip error handling ("user will add later")
- Ignore existing patterns in codebase

### Interaction Protocol (All AIs)

When proposing significant changes:

1. **Brief verification first** - "Here's what I'll do... sound good?"
2. **Wait for approval** - Don't generate 4k responses immediately
3. **Adjust if needed** - Make changes and verify again
4. **Then execute** - Full implementation only after confirmation

This prevents wasted work on misaligned approaches.

---

## TECHNICAL STANDARDS

### Code Quality

**Required**:
- Type hints on all function signatures
- Google-style docstrings on public functions
- Error handling with specific exceptions
- Logging for debugging (use `logger.info/error/debug`)

**Example**:
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
        ToolExecutionError: If tool execution fails
    """
    try:
        # Implementation
        pass
    except KeyError as e:
        logger.error(f"Tool '{name}' not found: {e}")
        raise ToolNotFoundError(f"Unknown tool: {name}")
    ```

### Testing

**Every tool must have**:
- Happy path test (normal usage)
- Error case test (failure handling)
- Edge case test (boundary conditions)

**Example**:
```

def test_web_search_success():
result = execute_search("AI news")
assert len(result) > 0
assert "http" in result

def test_web_search_network_failure():
with patch('duckduckgo_search.DDGS') as mock:
mock.side_effect = NetworkError()
result = execute_search("test")
assert "error" in result.lower()

```

---

## TOOL DEVELOPMENT GUIDELINES

### OpenAI Function Calling Format

All tools must follow this schema:

```

{
"type": "function",
"function": {
"name": "tool_name",
"description": "Clear description of what tool does",
"parameters": {
"type": "object",
"properties": {
"param_name": {
"type": "string",
"description": "What this parameter does"
}
},
"required": ["param_name"]
}
}
}

```

### Tool Return Values

**Must return strings** (LLMs consume text, not objects)

**Good**:
```

return json.dumps({
"status": "success",
"results": [...],
"count": 5
})

```

**Bad**:
```

return {"status": "success", "results": [...]}  \# Dict not string

```

---

## PROMPT ENGINEERING STANDARDS

### Layer Structure

```

name: "layer_name"
description: "What this layer controls"
priority: 0-100  \# Lower = higher priority
content: |
Markdown-formatted prompt content.

Can include:

- Instructions
- Examples
- Constraints
- Behavioral guidelines

```

### Priority Ranges

- **0-9**: Core identity (what the agent IS)
- **10-29**: Behavioral traits (how it ACTS)
- **30-49**: Tool usage (what it CAN DO)
- **50-99**: Domain-specific (task specialization)

---

## DECISION-MAKING FRAMEWORK

When faced with architectural choices, evaluate:

### 1. Scalability
Will this work with 100 tools? 1000 users? Multiple agents?

### 2. Maintainability
Can future developer modify this without breaking things?

### 3. Performance
Does this add latency? Token cost? API calls?

### 4. User Experience
Does this make agent more predictable and controllable?

**Tie-breaker**: Choose simpler solution. Complexity must justify itself.

---

## COMMUNICATION STANDARDS

### With Users

**Do**:
- Be direct and technical (users are developers)
- Explain reasoning behind recommendations
- Provide concrete examples, not theory
- Challenge bad ideas with alternatives

**Don't**:
- Hand-hold or over-explain basics
- Use corporate jargon or fluff
- Assume user knowledge without verification
- Agree with everything (critical thinking required)

### With Other AIs

**Do**:
- Document decisions in memory-bank/
- Reference specific files/functions when discussing code
- Provide context for recommendations
- State assumptions explicitly

**Don't**:
- Assume other AI has full context
- Use vague references ("the thing we discussed")
- Skip error scenarios in specifications

---

## ANTI-PATTERNS (Never Do This)

❌ **Generic advice**: "You should add error handling" (tell HOW for THIS project)  
❌ **Incomplete code**: "// TODO: implement this part" (finish it or don't start)  
❌ **Assumed knowledge**: "Just use the standard pattern" (show the code)  
❌ **Over-engineering**: Don't add abstraction until 3+ use cases exist  
❌ **Silent failures**: Every error must be logged or raised  
❌ **Magic numbers**: Use named constants (`MAX_RETRIES = 3` not `range(3)`)  
❌ **Hardcoded paths**: Use config/env vars for file paths, API endpoints  

---

## PROJECT CONSTRAINTS

### APIs/Services
- OpenRouter (DeepSeek, Grok models)
- Anthropic (Claude Computer Use)
- MCP servers at `C:\Users\k\Documents\Projects\mcp-module-manager`

### Environment
- Python 3.11
- Windows (PowerShell)
- VS Code + GitHub Copilot
- Virtual environment at `daagent/venv`

### Cost Sensitivity
- Develop with free models (nex-agi/deepseek-v3.1-nex-n1:free)
- Switch to paid only when necessary
- Monitor token usage
- User prefers free tier where possible

---

## VERSION HISTORY

- **1.0** (2025-12-25): Initial version
  - Core philosophy established
  - Architecture patterns defined
  - Collaboration protocols created

---