---
applyTo: "prompts/**/*.yaml"
description: Standards for YAML prompt files (Phase 4)
---

## YAML Prompt Standards

These files define Daagent's **behavior layers**. Changes here affect how the agent thinks and acts.

### File Structure

```
prompts/
├── core/              # Priority 0-99 (foundational)
│   ├── identity.yaml
│   ├── permissiveness.yaml
│   └── tool_usage.yaml
├── domain/            # Priority 100-199 (task-specific)
│   ├── research.yaml
│   ├── coding.yaml
│   └── analysis.yaml
└── schema.yaml        # Validation schema
```

### YAML Format (MANDATORY)

```yaml
# prompts/core/identity.yaml
***
name: core_identity
description: Agent's base identity and capabilities
priority: 0
enabled: true
content: |
  You are Daagent, a general-purpose AI agent with the following capabilities:
  - Dynamic model selection (free dev models, optimized prod models)
  - Tool usage (web search, file operations, code execution)
  - Autonomous reasoning via ReAct pattern
  
  Your goal is to help users accomplish tasks efficiently and accurately.
```

### Required Fields

#### name (string)
- Unique identifier for this prompt layer
- Use snake_case: `core_identity`, `domain_research`
- Must be unique across all prompt files

#### description (string)
- Human-readable explanation of what this layer controls
- Keep under 100 characters
- Example: "Agent's base identity and capabilities"

#### priority (integer)
- Loading order (0 = highest priority, loaded first)
- **Core layers:** 0-99
- **Domain layers:** 100-199
- Lower number = higher priority

#### enabled (boolean)
- Whether this layer is active
- Default: `true`
- Set to `false` to disable without deleting

#### content (string)
- The actual prompt text
- Use `|` for multi-line strings
- Markdown formatting supported
- Keep concise (under 1000 characters per layer)

### Priority Ranges

| Range | Purpose | Examples |
|-------|---------|----------|
| 0-9 | Core Identity | What the agent IS |
| 10-29 | Behavioral Traits | How the agent ACTS |
| 30-49 | Tool Usage | What the agent CAN DO |
| 50-99 | Core Capabilities | Foundational skills |
| 100-199 | Domain Specializations | Task-specific behavior |

### Content Guidelines

#### Clear and Actionable

```yaml
# ✅ GOOD
content: |
  When researching topics:
  - Use multiple search queries for comprehensive coverage
  - Cross-reference information from different sources
  - Cite sources for all claims

# ❌ BAD
content: |
  Be good at research.
```

#### Specific Instructions

```yaml
# ✅ GOOD
content: |
  For coding tasks:
  - Use type hints on all function signatures
  - Write Google-style docstrings
  - Follow the project's existing patterns

# ❌ BAD
content: |
  Write good code.
```

#### Behavioral Constraints

```yaml
# ✅ GOOD
content: |
  Philosophy: "Be a DOER, not an ASKER"
  - Take initiative rather than asking for permission
  - Make reasonable assumptions when requirements are ambiguous
  - Proactively solve problems with minimal hand-holding

# ❌ BAD
content: |
  Don't be annoying.
```

### Validation

#### Schema Compliance

All YAML files must validate against `prompts/schema.yaml`:

```yaml
# prompts/schema.yaml
$schema: "http://json-schema.org/draft-07/schema#"
type: object
properties:
  name:
    type: string
    pattern: "^[a-z_]+$"
  description:
    type: string
    maxLength: 100
  priority:
    type: integer
    minimum: 0
    maximum: 199
  enabled:
    type: boolean
  content:
    type: string
    maxLength: 2000
required: ["name", "priority", "content"]
```

#### Testing

```python
# tests/test_prompts.py

def test_all_prompts_valid_schema():
    """Validate all YAML prompts against schema."""
    # Load schema and validate each prompt file
    pass

def test_prompt_manager_loading():
    """Test that PromptManager loads and orders prompts correctly."""
    manager = PromptManager()
    prompt = manager.build_prompt()
    assert "You are Daagent" in prompt
    assert "Be a DOER" in prompt
```

### Best Practices

#### Layer Separation

```yaml
# ✅ GOOD - Separate concerns
# prompts/core/identity.yaml
name: core_identity
content: |
  You are Daagent...

# prompts/core/permissiveness.yaml
name: core_permissiveness
content: |
  Be a DOER not ASKER...

# ❌ BAD - Mixed concerns in one layer
name: core_combined
content: |
  You are Daagent. Be a DOER not ASKER...
```

#### Version Control

- Each prompt layer should be independently modifiable
- Non-technical users can edit YAML without code changes
- Changes are tracked in git history

#### Performance

- Keep content concise (under 500 characters per layer)
- Limit total layers to <20 for reasonable prompt sizes
- Use `enabled: false` instead of deleting files

### Boundaries

#### ✅ Always Do

- Follow YAML schema exactly
- Use descriptive names and priorities
- Keep content focused and actionable
- Test changes with PromptManager

#### ⚠️ Ask First

- Changing priority ranges
- Adding new required fields to schema
- Modifying core identity prompts

#### 🚫 Never Do

- Break YAML syntax
- Use duplicate names
- Put code in content (use Markdown only)
- Skip schema validation
