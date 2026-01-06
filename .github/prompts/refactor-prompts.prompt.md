---
agent: "prompt-engineer"
tools: ["read", "search", "web/githubRepo"]
description: Migrate Python prompts to YAML system (Phase 4A)
---

# YAML Prompt Refactoring

**Source File:** {input:sourceFile|Which Python file contains prompts? (e.g., 'agent/prompts.py')}  
**Target Directory:** {input:targetDir|Where to create YAML files? (default: 'prompts/')}  
**Maintain Compatibility:** {input:compatibility|Keep existing agent behavior? (yes/no)}

## Migration Checklist

### Phase 1: Analysis
- [ ] Read current `agent/prompts.py` implementation
- [ ] Identify all prompt layers and their priorities
- [ ] Map Python logic to YAML structure
- [ ] Plan backwards compatibility strategy

### Phase 2: Schema Creation
- [ ] Create `prompts/schema.yaml` with validation rules
- [ ] Define required fields (name, priority, content, etc.)
- [ ] Test schema validation with sample data

### Phase 3: YAML Migration
For each prompt in `agent/prompts.py`:

- [ ] Create `prompts/core/{layer_name}.yaml`
- [ ] Convert Python string to YAML content block
- [ ] Set appropriate priority (0-199 range)
- [ ] Add description and enabled flag

### Phase 4: PromptManager Implementation
- [ ] Create `PromptManager` class in `agent/prompts.py`
- [ ] Implement YAML loading with priority sorting
- [ ] Add schema validation
- [ ] Replace `build_system_prompt()` function

### Phase 5: Integration
- [ ] Update `agent/core.py` to use `PromptManager`
- [ ] Test agent behavior unchanged (backwards compatibility)
- [ ] Run existing test suite to ensure no regressions

### Phase 6: Cleanup
- [ ] Deprecate old Python prompt system
- [ ] Update documentation with YAML editing instructions
- [ ] Add tests for `PromptManager`

## Success Criteria

- [ ] All prompts migrated from Python to YAML
- [ ] `PromptManager` loads and combines layers correctly
- [ ] Agent behavior identical to before migration
- [ ] Schema validation working
- [ ] Tests pass (`pytest tests/test_prompts.py`)
- [ ] README updated with YAML customization guide

## Validation Tests

```python
def test_prompt_manager_loading():
    manager = PromptManager()
    prompt = manager.build_prompt()
    # Verify all expected layers are present
    assert "You are Daagent" in prompt
    assert "Be a DOER" in prompt

def test_yaml_schema_validation():
    # Test all YAML files validate against schema
    pass

def test_backwards_compatibility():
    # Ensure agent behavior unchanged
    pass
```

## Common Migration Patterns

### Python Dict to YAML
```python
# Python
SYSTEM_PROMPTS = {
    'core_identity': {
        'priority': 0,
        'content': "You are Daagent..."
    }
}

# YAML
# prompts/core/identity.yaml
name: core_identity
description: Agent's base identity
priority: 0
enabled: true
content: |
  You are Daagent...
```

### Conditional Logic
```python
# Python
if task_type == 'research':
    prompt += research_layer

# YAML - Use separate domain files
# prompts/domain/research.yaml
name: domain_research
priority: 100
content: |
  For research tasks...
```

## Error Handling

- **Schema validation fails:** Fix YAML syntax or schema compliance
- **Missing layers:** Ensure all required layers are migrated
- **Priority conflicts:** Adjust priorities to avoid duplicates
- **Content too long:** Split into multiple focused layers

---

**This migration unlocks non-technical prompt customization. Do it carefully.**
