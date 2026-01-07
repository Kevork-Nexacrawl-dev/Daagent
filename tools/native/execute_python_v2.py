"""
Unified Python execution interface for Daagent.
Smart routing between subprocess and persistent execution.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def execute_python_v2(
    code: str,
    persistent: bool = False,
    session_id: str = "default",
    requirements: Optional[List[str]] = None,
    timeout: int = 30
) -> str:
    """
    Smart Python executor with automatic mode selection.

    Args:
        code: Python code to execute
        persistent: Use Jupyter kernel (True) or subprocess (False)
        session_id: Session identifier for isolation
        requirements: Packages to install before execution
        timeout: Execution timeout in seconds

    Returns:
        JSON string with execution results
    """
    if persistent:
        try:
            from .execute_python_persistent import execute_python_persistent
            return execute_python_persistent(code, session_id, requirements, timeout)
        except Exception as e:
            logger.warning(f"Persistent execution failed, falling back to subprocess: {e}")
            # Fall back to subprocess execution
            persistent = False

    if not persistent:
        from .execute_python import execute_python
        return execute_python(code, requirements, timeout)


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_python_v2",
        "description": "Execute Python code with optional persistent session. Choose persistent=true for data analysis workflows, false for one-off scripts.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "persistent": {
                    "type": "boolean",
                    "default": False,
                    "description": "Use persistent kernel (default: false)"
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                    "description": "Session ID for isolation"
                },
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Packages to install before execution"
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 30,
                    "description": "Execution timeout in seconds"
                }
            },
            "required": ["code"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_python_v2