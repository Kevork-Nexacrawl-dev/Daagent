"""
Planning Tools - Daagent Native Tools
Ported from autogen-shop with adaptations for OpenAI function calling.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# ============================================
# TOOL SCHEMAS (OpenAI Function Calling Format)
# ============================================

DECOMPOSE_TASK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "decompose_task",
        "description": "Break down a complex task into smaller, manageable subtasks",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The main goal or task to decompose"
                },
                "complexity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Estimated complexity level",
                    "default": "medium"
                },
                "max_subtasks": {
                    "type": "integer",
                    "description": "Maximum number of subtasks to generate",
                    "default": 5
                }
            },
            "required": ["goal"]
        }
    }
}

PRIORITIZE_STEPS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "prioritize_steps",
        "description": "Order tasks by dependencies and priority",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "urgency": {"type": "integer", "minimum": 1, "maximum": 10},
                            "dependencies": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "description": "List of tasks with dependencies"
                }
            },
            "required": ["tasks"]
        }
    }
}

ESTIMATE_COMPLEXITY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "estimate_complexity",
        "description": "Estimate time and effort for a task",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task description to estimate"
                },
                "task_type": {
                    "type": "string",
                    "enum": ["coding", "research", "analysis", "planning", "testing"],
                    "description": "Type of task"
                }
            },
            "required": ["task", "task_type"]
        }
    }
}

# ============================================
# TOOL IMPLEMENTATIONS
# ============================================

def execute_decompose_task(args: Dict[str, Any]) -> str:
    """
    Execute decompose_task tool.

    Args:
        args: Dict with goal and optional parameters

    Returns:
        JSON string with decomposed subtasks
    """
    try:
        goal = args.get("goal", "")
        complexity = args.get("complexity", "medium")
        max_subtasks = args.get("max_subtasks", 5)

        if not goal:
            return json.dumps({"status": "error", "error": "Goal is required"})

        # Generate subtasks based on goal and complexity
        subtasks = []

        if complexity == "low":
            subtasks = [
                {"name": "Research", "description": f"Research {goal}", "order": 1},
                {"name": "Execute", "description": f"Execute {goal}", "order": 2},
                {"name": "Review", "description": f"Review {goal} results", "order": 3}
            ]
        elif complexity == "medium":
            subtasks = [
                {"name": "Analysis", "description": f"Analyze requirements for {goal}", "order": 1},
                {"name": "Planning", "description": f"Create plan for {goal}", "order": 2},
                {"name": "Implementation", "description": f"Implement {goal}", "order": 3},
                {"name": "Testing", "description": f"Test {goal}", "order": 4},
                {"name": "Documentation", "description": f"Document {goal}", "order": 5}
            ]
        else:  # high
            subtasks = [
                {"name": "Requirements", "description": f"Gather requirements for {goal}", "order": 1},
                {"name": "Design", "description": f"Design solution for {goal}", "order": 2},
                {"name": "Architecture", "description": f"Define architecture for {goal}", "order": 3},
                {"name": "Development", "description": f"Develop {goal}", "order": 4},
                {"name": "Integration", "description": f"Integrate components for {goal}", "order": 5},
                {"name": "Testing", "description": f"Test {goal} thoroughly", "order": 6},
                {"name": "Deployment", "description": f"Deploy {goal}", "order": 7}
            ]

        # Limit to max_subtasks
        subtasks = subtasks[:max_subtasks]

        return json.dumps({
            "status": "success",
            "goal": goal,
            "complexity": complexity,
            "subtasks_count": len(subtasks),
            "subtasks": subtasks,
            "estimated_total_time": f"{len(subtasks) * 2} hours"
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_prioritize_steps(args: Dict[str, Any]) -> str:
    """
    Execute prioritize_steps tool.

    Args:
        args: Dict with tasks array

    Returns:
        JSON string with prioritized tasks
    """
    try:
        tasks = args.get("tasks", [])

        if not tasks:
            return json.dumps({"status": "error", "error": "Tasks array is required"})

        # Add default values and calculate priority scores
        for task in tasks:
            if "urgency" not in task:
                task["urgency"] = 5
            if "dependencies" not in task:
                task["dependencies"] = []

            # Calculate priority score (higher = more important)
            task["priority_score"] = task["urgency"]

        # Sort by priority score (descending)
        prioritized_tasks = sorted(tasks, key=lambda x: x["priority_score"], reverse=True)

        # Assign priority tiers
        for i, task in enumerate(prioritized_tasks):
            if i < len(prioritized_tasks) // 3:
                task["priority_tier"] = "High"
            elif i < 2 * len(prioritized_tasks) // 3:
                task["priority_tier"] = "Medium"
            else:
                task["priority_tier"] = "Low"

        return json.dumps({
            "status": "success",
            "tasks_count": len(tasks),
            "prioritized_tasks": prioritized_tasks,
            "high_priority_count": sum(1 for t in prioritized_tasks if t["priority_tier"] == "High"),
            "medium_priority_count": sum(1 for t in prioritized_tasks if t["priority_tier"] == "Medium"),
            "low_priority_count": sum(1 for t in prioritized_tasks if t["priority_tier"] == "Low")
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_estimate_complexity(args: Dict[str, Any]) -> str:
    """
    Execute estimate_complexity tool.

    Args:
        args: Dict with task and task_type

    Returns:
        JSON string with complexity estimate
    """
    try:
        task = args.get("task", "")
        task_type = args.get("task_type", "")

        if not task or not task_type:
            return json.dumps({"status": "error", "error": "Both task and task_type are required"})

        # Base estimates by task type
        estimates = {
            "coding": {"hours": 4, "complexity": "medium", "confidence": 0.8},
            "research": {"hours": 2, "complexity": "low", "confidence": 0.7},
            "analysis": {"hours": 3, "complexity": "medium", "confidence": 0.8},
            "planning": {"hours": 2, "complexity": "low", "confidence": 0.9},
            "testing": {"hours": 3, "complexity": "medium", "confidence": 0.8}
        }

        base_estimate = estimates.get(task_type, {"hours": 2, "complexity": "medium", "confidence": 0.5})

        # Adjust based on task length/complexity indicators
        task_length = len(task.split())
        if task_length > 20:
            base_estimate["hours"] *= 1.5
            base_estimate["complexity"] = "high"
        elif task_length < 10:
            base_estimate["hours"] *= 0.7
            base_estimate["complexity"] = "low"

        # Look for complexity indicators
        complexity_keywords = ["complex", "advanced", "multiple", "integration", "architecture"]
        if any(kw in task.lower() for kw in complexity_keywords):
            base_estimate["hours"] *= 1.3
            base_estimate["complexity"] = "high"

        return json.dumps({
            "status": "success",
            "task": task,
            "task_type": task_type,
            "estimated_hours": round(base_estimate["hours"], 1),
            "complexity_level": base_estimate["complexity"],
            "confidence": base_estimate["confidence"],
            "factors": ["task_length", "keywords"] if task_length > 20 else ["task_length"]
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ============================================
# REGISTRY (for agent/core.py to discover)
# ============================================

TOOL_SCHEMAS = [DECOMPOSE_TASK_SCHEMA, PRIORITIZE_STEPS_SCHEMA, ESTIMATE_COMPLEXITY_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute planning tool.

    Args:
        operation: Tool operation name
        **kwargs: Tool arguments

    Returns:
        JSON string result
    """
    if operation == "decompose_task":
        return execute_decompose_task(kwargs)
    elif operation == "prioritize_steps":
        return execute_prioritize_steps(kwargs)
    elif operation == "estimate_complexity":
        return execute_estimate_complexity(kwargs)
    else:
        return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})