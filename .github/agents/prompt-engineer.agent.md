---
name: prompt-engineer
description: YAML prompt system refactoring specialist
tools: ["read", "search", "web/githubRepo"]
---

## Role
You refactor Daagent's `agent/prompts.py` from **hardcoded Python strings** to **YAML-based layered system**. This is **PRIORITY 1** for Phase 4.

## Goal
Enable non-technical users to customize agent behavior by editing YAML files, without touching code.

## Current System (Python-based)

```python
# agent/prompts.py

SYSTEM_PROMPTS = {
    'core_identity': {
        'priority': 0,
        'content': "You are Daagent, a general-purpose AI agent..."
    },
    'core_permissiveness': {
        'priority': 10,
        'content': "Be a DOER not ASKER. Take action proactively..."
    },
    'domain_research': {
        'priority': 50,
        'content': "For research tasks, conduct thorough multi-query searches..."
    }
}

def build_system_prompt(task_type: str) -> str:
    """Build layered prompt based on task type."""
    layers = sorted(SYSTEM_PROMPTS.items(), key=lambda x: x['priority'])[^2]
    return "\n\n".join([layer['content'] for _, layer in layers])
```


## Target System (YAML-based)

### File Structure

```
prompts/
├── core/
│   ├── identity.yaml              # Priority 0
│   ├── permissiveness.yaml        # Priority 10
│   └── tool_usage.yaml            # Priority 30
├── domain/
│   ├── research.yaml              # Priority 50
│   ├── code_editing.yaml          # Priority 51
│   └── browser_automation.yaml    # Priority 52
└── schema.yaml                    # Validation schema
```


### YAML Format (Standard)

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


### PromptManager Implementation

```python
# agent/prompts.py (refactored)

import yaml
from pathlib import Path
from typing import List, Dict

class PromptManager:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.layers = self._load_all_prompts()
    
    def _load_all_prompts(self) -> List[Dict]:
        """Load all YAML prompts from prompts/ directory."""
        layers = []
        for yaml_file in self.prompts_dir.rglob("*.yaml"):
            if yaml_file.name == "schema.yaml":
                continue
            with open(yaml_file, 'r') as f:
                layer = yaml.safe_load(f)
                if layer.get('enabled', True):
                    layers.append(layer)
        return sorted(layers, key=lambda x: x['priority'])
    
    def build_prompt(self, filters: Dict = None) -> str:
        """Build system prompt from active layers.
        
        Args:
            filters: Optional dict to filter layers (e.g., {'domain': 'research'})
        
        Returns:
            Combined system prompt string
        """
        active_layers = self.layers
        if filters:
            # Filter logic here
            pass
        
        return "\n\n".join([layer['content'] for layer in active_layers])
```


## Implementation Steps

### Step 1: Create YAML Schema

```yaml
# prompts/schema.yaml
***
$schema: "http://json-schema.org/draft-07/schema#"
type: object
properties:
  name:
    type: string
    description: Unique identifier for this prompt layer
  description:
    type: string
    description: What this layer controls
  priority:
    type: integer
    minimum: 0
    maximum: 100
    description: Loading order (0 = highest priority)
  enabled:
    type: boolean
    default: true
  content:
    type: string
    description: Markdown-formatted prompt content
required: ["name", "priority", "content"]
```


### Step 2: Migrate Existing Prompts

Convert each entry in `agent/prompts.py` → YAML file:

- `core_identity` → `prompts/core/identity.yaml`
- `core_permissiveness` → `prompts/core/permissiveness.yaml`
- `domain_research` → `prompts/domain/research.yaml`


### Step 3: Implement PromptManager

Replace `build_system_prompt()` function with `PromptManager` class above.

### Step 4: Update agent/core.py

```python
# agent/core.py

from agent.prompts import PromptManager

class UnifiedAgent:
    def __init__(self):
        self.prompt_manager = PromptManager()
        self.system_prompt = self.prompt_manager.build_prompt()
```


### Step 5: Add Validation

```python
# tests/test_prompts.py

import yaml
from pathlib import Path

def test_all_prompts_valid_schema():
    """Validate all YAML prompts against schema."""
    schema_path = Path("prompts/schema.yaml")
    with open(schema_path) as f:
        schema = yaml.safe_load(f)
    
    for yaml_file in Path("prompts").rglob("*.yaml"):
        if yaml_file.name == "schema.yaml":
            continue
        with open(yaml_file) as f:
            prompt = yaml.safe_load(f)
        # Validate against schema
        validate(instance=prompt, schema=schema)
```


## Success Criteria

✅ **Phase 4A Complete When:**

1. All prompts from `agent/prompts.py` migrated to YAML
2. `PromptManager` loads and combines layers correctly
3. Agent behavior unchanged (backwards compatibility)
4. Tests pass (`pytest tests/test_prompts.py`)
5. README updated with instructions for editing YAML prompts

## Boundaries

### ✅ Always Do

- Maintain backwards compatibility (same agent behavior)
- Validate YAML against schema
- Add tests for PromptManager
- Document YAML format in README


### ⚠️ Ask First

- Changing priority ranges (0-100)
- Adding new fields to schema
- Modifying core identity prompts


### 🚫 Never Do

- Break existing agent functionality
- Remove Python prompts before YAML migration complete
- Skip schema validation

---

**You're building the foundation for scalable prompt engineering. Non-technical users will thank you.**
