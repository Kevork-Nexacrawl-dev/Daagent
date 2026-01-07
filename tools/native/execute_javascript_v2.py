"""
Unified JavaScript execution interface for Daagent.
Smart routing between temp file and REPL execution.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def execute_javascript_v2(
    code: str,
    persistent: bool = False,
    session_id: str = "default",
    packages: Optional[List[str]] = None,
    timeout: int = 30
) -> str:
    """
    Smart JavaScript executor.

    Routes to:
    - execute_javascript_persistent() if persistent=True
    - execute_javascript() if persistent=False
    """
    if persistent:
        try:
            from .execute_javascript_persistent import execute_javascript_persistent
            return execute_javascript_persistent(code, session_id, packages, timeout)
        except Exception as e:
            logger.warning(f"Persistent JavaScript execution failed, falling back to temp file: {e}")
            # Fall back to temp file execution
            persistent = False

    if not persistent:
        from .execute_javascript import execute_javascript
        return execute_javascript(code, packages, timeout)


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_javascript_v2",
        "description": "Execute JavaScript code with optional persistent Node.js REPL. Choose persistent=true for API testing workflows, false for one-off scripts.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "JavaScript code to execute"
                },
                "persistent": {
                    "type": "boolean",
                    "default": False,
                    "description": "Use persistent REPL (default: false)"
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                    "description": "Session ID for isolation"
                },
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "npm packages to install before execution"
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
execute_tool = execute_javascript_v2