---
agent: "apex-orch"
tools: ["read", "search"]
description: Plan implementation of a new development phase
---

# Phase Planning Template

**Phase Name:** {input:phaseName|What phase are we planning? (e.g., 'Phase 4A: YAML Prompts')}  
**Goal:** {input:goal|What does this phase accomplish?}  
**Complexity:** {input:complexity|High/Medium/Low complexity?}  
**Timeline:** {input:timeline|Estimated timeline?}

## Current State Analysis

### ✅ What's Working
- List current capabilities that support this phase

### ❌ Blockers
- What must be completed before starting this phase?
- Dependencies on other phases or external factors?

### 📋 Requirements Gathering
- Functional requirements (what the phase must do)
- Non-functional requirements (performance, security, etc.)
- Success criteria (how we know it's done)

## Implementation Plan

### Phase Breakdown
Break into logical sub-phases with clear deliverables:

1. **Sub-phase 1** (Priority: High)
   - Description: What this sub-phase accomplishes
   - Complexity: Estimated effort
   - Dependencies: What must be done first
   - Success Criteria: Measurable outcomes

2. **Sub-phase 2** (Priority: Medium)
   - ...

### DAG Dependencies
```
Task A → Task B → Task C
   ↓
Task D → Task E
```

### Agent Assignment
- **Apex Orchestrator:** Overall coordination and critical path management
- **Tool Architect:** Build new tools/components
- **Prompt Engineer:** YAML refactoring and prompt engineering
- **MCP Integrator:** External system integration
- **QA Tester:** Testing strategy and implementation
- **Red Team:** Failure mode analysis and security review

## Risk Assessment

### High Risk Items
1. **Risk:** Description
   - **Impact:** What breaks if this fails
   - **Likelihood:** How probable
   - **Mitigation:** How to prevent/reduce

### Contingency Plans
- What if timeline slips?
- What if key dependencies aren't met?
- What if external factors change?

## Success Metrics

### Quantitative
- Code coverage: ≥80%
- Performance benchmarks: Meet targets
- Test pass rate: 100%

### Qualitative
- User experience improvements
- Maintainability enhancements
- Scalability gains

## Communication Plan

### Internal Updates
- Daily standups for active phases
- Weekly progress reviews
- Immediate escalation for blockers

### User Communication
- Phase completion announcements
- Feature previews for major changes
- Migration guides for breaking changes

## Rollback Plan

If phase must be aborted:
- What can be safely reverted?
- What becomes unsupported?
- How to minimize user impact?

---

**Use this template to plan every major development phase. Structure brings clarity to complexity.**
