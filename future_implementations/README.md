## Workflow

### 1. Add Idea (Quick)

Edit `ideas.json`, add new entry:

```

{
"id": "NNN",
"name": "feature_name",
"title": "Human Readable Title",
"type": "feature",
"description": "Brief description",
"status": "pending",
"priority": "medium",
"effort": "medium",
"relevance": 50,
"dependencies": [],
"related_ideas": [],
"link": null,
"created_date": "YYYY-MM-DD",
"updated_date": "YYYY-MM-DD",
"notes": "Why this matters"
}

```

### 2. Approve Idea (When Ready)

1. Update status: `"status": "approved"`
2. Create detailed spec: `approved/NNN_feature_name.md`
3. Update link: `"link": "approved/NNN_feature_name.md"`

### 3. Implement Feature

1. Update status: `"status": "in_progress"`
2. Build the feature
3. Document decisions in spec file

### 4. Complete Feature

1. Update status: `"status": "completed"`
2. Move spec to `completed/NNN_feature_name.md`
3. Update link: `"link": "completed/NNN_feature_name.md"`
4. Add completion date

---

## Status Values

- **pending**: New idea, not yet reviewed
- **approved**: Green-lit, ready to implement
- **in_progress**: Currently being built
- **completed**: Implemented and shipped
- **rejected**: Decided not to pursue

---

## Priority Levels

- **critical**: Blocking other work, do now
- **high**: Important, schedule soon
- **medium**: Nice to have, queue up
- **low**: Maybe someday

---

## Effort Estimates

- **small**: 1-2 days
- **medium**: 3-7 days
- **large**: 1-2 weeks

---

## Relevance Score (0-100)

Used by AI orchestrator for prioritization:
- **80-100**: Core functionality
- **60-79**: Valuable enhancement
- **40-59**: Nice to have
- **0-39**: Low value, maybe later

---

## Detailed Spec Template

When creating markdown file in `approved/`:

```


# [Feature Name]

**ID**: NNN
**Status**: approved → in_progress → completed
**Last Updated**: YYYY-MM-DD

## Problem It Solves

[User pain point this addresses]

## Proposed Solution

[High-level approach]

## Architecture

[How it integrates with existing code]

## Implementation Plan

1. Step 1
2. Step 2
3. Step 3

## Example Usage

```python
# Code example
```


## Open Questions

- [ ] Question 1
- [ ] Question 2


## Decision Log

- YYYY-MM-DD: Approved
- YYYY-MM-DD: Started implementation
- YYYY-MM-DD: Completed


## Testing Strategy

[How to verify it works]

```
```


***

## Initial ideas.json

```json
{
  "ideas": [
    {
      "id": "001",
      "name": "ephemeral_workers",
      "title": "Ephemeral Worker Spawning System",
      "type": "feature",
      "description": "Parallel task execution with specialized sub-agents that spawn on-demand and self-destruct after completing their assigned subtask",
      "status": "approved",
      "priority": "medium",
      "effort": "large",
      "relevance": 75,
      "dependencies": ["web_search", "file_ops", "cli_interface"],
      "related_ideas": [],
      "link": "approved/001_ephemeral_workers.md",
      "created_date": "2025-12-25",
      "updated_date": "2025-12-25",
      "notes": "Based on Dust.tt pattern. Enables parallel research/analysis tasks. Implement in Phase 4 after tools working."
    },
    {
      "id": "002",
      "name": "yaml_prompts",
      "title": "YAML-Based Prompt System",
      "type": "refactor",
      "description": "Convert prompt layering from Python (agent/prompts.py) to YAML files in prompts/ directory for non-technical editing",
      "status": "pending",
      "priority": "medium",
      "effort": "medium",
      "relevance": 80,
      "dependencies": ["core_agent"],
      "related_ideas": ["003"],
      "link": null,
      "created_date": "2025-12-25",
      "updated_date": "2025-12-25",
      "notes": "Enables domain-specific prompts without code changes. Non-blocking (current system works)."
    },
    {
      "id": "003",
      "name": "domain_prompts",
      "title": "Domain-Specific Prompt Templates",
      "type": "feature",
      "description": "Pre-built prompt layers for common use cases: research, job applications, code review, data analysis",
      "status": "pending",
      "priority": "low",
      "effort": "small",
      "relevance": 60,
      "dependencies": ["002"],
      "related_ideas": ["002"],
      "link": null,
      "created_date": "2025-12-25",
      "updated_date": "2025-12-25",
      "notes": "Requires YAML prompt system first (id: 002). User can customize behavior for specific workflows."
    }
  ]
}
```