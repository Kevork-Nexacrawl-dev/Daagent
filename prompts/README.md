---

# Prompt Layering System

## Overview

The Daagent prompt system uses **priority-based layering** to compose a final system prompt from modular YAML files. This allows:

- **Non-developers** to modify agent behavior without touching Python code
- **Easy composition** of complex prompts from reusable layers
- **Clear separation** of concerns (identity, behavior, tools, domains)
- **Version control** of prompt changes alongside code
- **Extensibility** to add new domains without refactoring

## Directory Structure

```
prompts/
├── core/                    # Core behavior layers
│   ├── identity.yaml       # Priority 0: Base agent identity
│   ├── behavior.yaml       # Priority 10: Behavioral traits
│   └── tool_usage.yaml     # Priority 30: Tool usage patterns
│
├── domain/                 # Domain-specific layers
│   ├── research.yaml       # Priority 50: Research behavior
│   ├── coding.yaml         # (Future) Programming tasks
│   └── analysis.yaml       # (Future) Data analysis
│
└── README.md              # This file
```

## Priority Ranges

Layers are composed in **priority order (0 → 99)**:

| Priority | Purpose | Examples |
|----------|---------|----------|
| **0-9** | Core Identity | Agent's fundamental identity, core capabilities |
| **10-29** | Behavioral Traits | Philosophies, decision-making, attitude |
| **30-49** | Tool Usage | How to use available tools effectively |
| **50-99** | Domain-Specific | Specialized behavior for specific domains |

Lower priority layers appear first in the final prompt. Higher priority can override or specialize lower priority guidance.

## YAML Schema

Each layer is a YAML file with this structure:

```yaml
name: "layer_name"              # Unique identifier (snake_case)
priority: 10                     # 0-99 (lower = earlier in prompt)
description: "What this does"    # Human-readable description
content: |                       # The actual prompt text
  Instructions or guidelines
  for this layer...
```

### Example: behavior.yaml

```yaml
name: "core_behavior"
priority: 10
description: "DOER philosophy and decision-making guidelines"
content: |
  BEHAVIORAL GUIDELINES:

  - Be a DOER, not an ASKER. Take action rather than asking for permission.
  - When uncertain, make reasonable assumptions and proceed.
  - If multiple approaches exist, choose the most efficient one.
  - Don't apologize excessively or hedge unnecessarily.
  - If a task seems impossible with available tools, get creative with combinations.
```

## How It Works

### 1. Loading Layers

The `load_prompts()` function scans the `prompts/` directory and loads all YAML files:

```python
from agent.prompt_loader import load_prompts
from pathlib import Path

layers = load_prompts(Path.cwd())
# Returns: List[PromptLayer] sorted by priority
```

**Features:**
- Recursively searches subdirectories
- Validates required fields (name, priority, content)
- Gracefully skips invalid files with warnings
- Returns layers sorted by priority (ascending)

### 2. Composing Prompts

The `compose_prompt()` function combines layers into a single prompt:

```python
from agent.prompt_loader import compose_prompt

final_prompt = compose_prompt(layers)
# Returns: str (all layer contents joined with double newlines)
```

### 3. Backward Compatibility

The `build_system_prompt()` in `agent/prompts.py` maintains the original interface:

```python
from agent.prompts import build_system_prompt

prompt = build_system_prompt()
# Same signature as before, but now uses layered system internally
```

## Hybrid Prompt Layering (v2.0)

### Modes

Each prompt layer has a **mode** that determines how it interacts with other prompts:

- **stackable**: All prompts in the same priority group are concatenated
- **hierarchical**: Only the highest priority prompt in the group is used

### Priority Groups

Prompts are organized into groups based on priority ranges:

| Group | Range | Default Mode | Purpose |
|-------|-------|--------------|---------|
| `behavior` | 0-10 | Stackable | Core personality, identity |
| `expertise` | 11-19 | Stackable | Domain knowledge |
| `tool_instructions` | 20-30 | Hierarchical | How to use tools |
| `error_handling` | 31-39 | Stackable | Retry logic, fallbacks |
| `response_format` | 40-50 | Stackable | Output structure |
| `memory_context` | 51-59 | Stackable | Conversation awareness |
| `execution_mode` | 60-70 | Hierarchical | Lite vs ReAct vs Planning |
| `safety_ethics` | 71-79 | Hierarchical | Content filtering |
| `user_overrides` | 80-90 | Hierarchical | CLI flags, user prefs |
| `debug_emergency` | 91-100 | Hierarchical | Debug mode |

### Example: Stackable

```yaml
# Both prompts stack together
name: identity
priority: 5
mode: stackable
priority_group: behavior
content: "You are helpful..."

name: expert_coder
priority: 8
mode: stackable
priority_group: behavior
content: "You excel at code..."

# Result: Both included in final prompt
```

### Example: Hierarchical

```yaml
# Only highest priority wins
name: safe_mode
priority: 25
mode: hierarchical
priority_group: tool_instructions
content: "Ask before file ops"

name: aggressive_mode
priority: 28
mode: hierarchical
priority_group: tool_instructions
content: "Execute immediately"

# Result: Only aggressive_mode included (28 > 25)
```

### Migration from v1.0

Existing YAML files without `mode` field default to `stackable` (backward compatible).

To convert to hybrid:
1. Add `mode: stackable` or `mode: hierarchical`
2. Add `priority_group: <group_name>` (optional, auto-detected from priority)

---

## Adding New Layers

### Step 1: Create YAML File

Create a new file in the appropriate subdirectory:

```bash
# New tool usage guideline
touch prompts/core/new_tool.yaml

# New domain-specific layer
touch prompts/domain/my_domain.yaml
```

### Step 2: Write YAML Content

```yaml
name: "my_new_layer"
priority: 45                    # Pick appropriate priority range
description: "What this layer does"
content: |
  Your prompt content here.
  Can be multiple lines.
  Just remember to indent properly.
```

### Step 3: Test

Verify loading works:

```python
from agent.prompt_loader import load_prompts
from agent.prompts import build_system_prompt

layers = load_prompts()
# Check your layer is loaded
assert any(l.name == "my_new_layer" for l in layers)

# Test final prompt
prompt = build_system_prompt()
assert "Your prompt content" in prompt
```

### Step 4: Run Tests

```bash
pytest tests/test_prompt_loader.py -v
```

## Creating New Domains

To add domain-specific behavior:

### 1. Create Domain Directory

```bash
mkdir -p prompts/domain/my_domain
```

### 2. Add Domain Layers

```bash
# prompts/domain/my_domain/main.yaml
name: "domain_my_domain"
priority: 50
description: "Behavior for my_domain tasks"
content: |
  [Domain-specific guidelines...]
```

### 3. Load in Code

```python
from agent.prompts import load_custom_layers

# Load domain-specific layers
domain_layers = load_custom_layers("my_domain")
```

## Common Patterns

### Override a Layer

To modify existing behavior, edit the corresponding YAML file:

```yaml
# prompts/core/behavior.yaml
# Edit this to change how the agent makes decisions

name: "core_behavior"
priority: 10
content: |
  [Updated behavioral guidelines]
```

### Add Conditional Behavior

Create multiple layers for different scenarios:

```
prompts/domain/research/
├── base.yaml          # Priority 50: Basic research guidelines
├── academic.yaml      # Priority 55: Academic research specifics
└── commercial.yaml    # Priority 56: Commercial research specifics
```

Load the appropriate layers based on context:

```python
if research_type == "academic":
    layers = load_prompts()  # Includes academic.yaml
elif research_type == "commercial":
    # Load different layers or modify composition
```

### Template Layer

Create a reusable template:

```yaml
# prompts/core/template_instructions.yaml
name: "template_instructions"
priority: 25
description: "Template for instruction following"
content: |
  INSTRUCTION FOLLOWING:
  - Read instructions carefully before responding
  - Follow numbered steps in order
  - If instruction conflicts with guidelines, seek clarification
  - Report completion status
```

## Validation

### Verify Layer Loading

```python
from agent.prompt_loader import load_prompts

layers = load_prompts()
for layer in layers:
    print(f"{layer.priority:02d}: {layer.name}")

# Output:
# 00: core_identity
# 10: core_behavior
# 30: tool_usage
# 50: domain_research
```

### Verify Composition

```python
from agent.prompts import build_system_prompt

prompt = build_system_prompt()
print(len(prompt))           # Check size
print(prompt[:200])          # Check beginning
```

### Run Tests

```bash
# All tests
pytest tests/test_prompt_loader.py -v

# Specific test
pytest tests/test_prompt_loader.py::TestPromptComposition::test_compose_prompt_order -v

# With coverage
pytest tests/test_prompt_loader.py --cov=agent.prompt_loader --cov-report=html
```

## Troubleshooting

### Prompt Not Loading

1. **Check file exists**
   ```bash
   ls -la prompts/core/
   ls -la prompts/domain/
   ```

2. **Validate YAML syntax**
   ```yaml
   # Must have these fields:
   name: "layer_name"
   priority: 10
   content: "Your content"
   ```

3. **Check for encoding issues**
   - Ensure file is UTF-8 encoded
   - No BOM (Byte Order Mark)

4. **Enable debug logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)

   from agent.prompt_loader import load_prompts
   layers = load_prompts()
   ```

### Unexpected Layer Order

Verify priorities are numeric and sorted:

```python
from agent.prompt_loader import load_prompts

layers = load_prompts()
for layer in layers:
    print(f"{layer.priority:3d}: {layer.name}")

# Should be ascending
```

### Content Not Appearing in Prompt

1. Check layer is loading: `load_prompts()` should include it
2. Check priority isn't conflicting
3. Verify YAML indentation (use spaces, not tabs for content)

```yaml
# Good
content: |
  This is
  multi-line content

# Bad
content: |
	Tab indentation won't parse correctly
```

## Best Practices

1. **Use clear names**: `core_identity`, not `prompt1` or `x`
2. **Document priorities**: Comment your choice
3. **Keep layers focused**: One concern per layer
4. **Use consistent formatting**: Match existing style
5. **Test changes**: Run `pytest` before committing
6. **Version control**: Commit YAML changes with code changes
7. **Document domains**: Add README to domain directories

## Future Extensions

- [ ] Layer templates with variables
- [ ] Conditional layer loading based on task type
- [ ] Layer composition profiles (research mode, coding mode, etc.)
- [ ] Layer dependency management
- [ ] Web UI for prompt editing
- [ ] A/B testing different layer combinations

## Files

- `agent/prompt_loader.py` - Core loading and composition logic
- `agent/prompts.py` - Integration with agent.core.py (backward compatible)
- `prompts/core/*.yaml` - Core behavior layers
- `prompts/domain/*.yaml` - Domain-specific layers
- `tests/test_prompt_loader.py` - Comprehensive test suite

## API Reference

### `load_prompts(base_path=None) → List[PromptLayer]`

Load all prompt layers from YAML files.

**Parameters:**
- `base_path` (Path): Root path. Defaults to `Path.cwd()`

**Returns:**
- List of `PromptLayer` objects sorted by priority

**Raises:**
- `FileNotFoundError`: If prompts directory doesn't exist

### `compose_prompt(layers) → str`

Compose final system prompt from layers.

**Parameters:**
- `layers` (List[PromptLayer]): Layers to compose

**Returns:**
- Final prompt string (layers joined with double newlines)

**Raises:**
- `ValueError`: If layer list is empty

### `load_and_compose(base_path=None) → str`

Convenience function: load and compose in one call.

**Parameters:**
- `base_path` (Path): Root path. Defaults to `Path.cwd()`

**Returns:**
- Final prompt string

### `build_system_prompt() → str`

Build system prompt via original interface (backward compatible).

**Parameters:**
- None

**Returns:**
- Final prompt string

**Note:** This is the primary function used by `agent.core.py`

---

*Generated for Daagent | Prompt System v1.0*
