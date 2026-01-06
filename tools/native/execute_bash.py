"""
Bash script execution tool for Daagent.
Executes Bash commands with safety checks and timeout protection.
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _is_dangerous_command(command: str, allow_dangerous: bool = False) -> tuple[bool, str]:
    """
    Check if a command contains dangerous operations.

    Args:
        command: The bash command to check
        allow_dangerous: Whether to allow dangerous commands

    Returns:
        Tuple of (is_dangerous, reason)
    """
    if allow_dangerous:
        return False, ""

    dangerous_patterns = [
        # File system destruction
        (r'\brm\s+-rf\s+/', "Command attempts to delete root filesystem"),
        (r'\brm\s+-rf\s+/\*', "Command attempts to delete all files in root"),
        (r'\bdd\s+if=.*of=/dev/', "Command attempts to overwrite disk devices"),
        (r'\bmkfs\b', "Command attempts to format filesystem"),
        (r'\bfdisk\b', "Command attempts to modify partition table"),
        (r'\bparted\b', "Command attempts to modify partitions"),

        # System destruction
        (r'\bshutdown\b', "Command attempts to shutdown system"),
        (r'\breboot\b', "Command attempts to reboot system"),
        (r'\bhalt\b', "Command attempts to halt system"),
        (r'\bpoweroff\b', "Command attempts to power off system"),

        # Network attacks
        (r'\bhping3?\b', "Command may be used for network attacks"),
        (r'\bnmap\b.*-A', "Command attempts aggressive network scanning"),

        # Fork bombs and resource exhaustion
        (r':\(\)\s*\{\s*:\|\s*:\&\s*\}\s*;', "Fork bomb detected"),
        (r'\bfork\b.*while', "Potential fork bomb pattern"),
        (r'\bwhile\s+true\s*;?\s*do\b.*&\s*;?\s*done', "Potential resource exhaustion loop"),

        # Privilege escalation
        (r'\bsudo\b.*\bsu\b', "Command attempts privilege escalation"),
        (r'\bsu\b.*root', "Command attempts to switch to root"),

        # Dangerous network operations
        (r'\bwget\b.*\|\s*bash', "Command downloads and executes remote code"),
        (r'\bcurl\b.*\|\s*bash', "Command downloads and executes remote code"),
        (r'\bcurl\b.*\|\s*sh', "Command downloads and executes remote code"),
    ]

    for pattern, reason in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return True, reason

    return False, ""


def execute_bash(command: str, allow_dangerous: bool = False, timeout: int = 30) -> str:
    """
    Execute Bash command with safety checks.

    Args:
        command: Bash command to execute
        allow_dangerous: Allow potentially dangerous commands (default: False)
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        JSON string containing execution results:
        {
            "status": "success" | "error",
            "stdout": captured stdout,
            "stderr": captured stderr,
            "returncode": process return code,
            "safety_check": "passed" | "bypassed" | "blocked",
            "safety_reason": reason if blocked
        }
    """
    try:
        # Safety check
        is_dangerous, reason = _is_dangerous_command(command, allow_dangerous)
        if is_dangerous:
            return json.dumps({
                "status": "error",
                "message": f"Command blocked for safety: {reason}",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "safety_check": "blocked",
                "safety_reason": reason
            })

        safety_status = "bypassed" if allow_dangerous else "passed"

        # Create workspace directory
        workspace_dir = Path("./workspace/bash")
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Execute the command
        logger.info(f"Executing Bash command (safety: {safety_status})")
        result = subprocess.run([
            "bash", "-c", command
        ], capture_output=True, text=True, timeout=timeout, cwd=workspace_dir)

        # Return results
        return json.dumps({
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "safety_check": safety_status,
            "safety_reason": "" if safety_status != "blocked" else reason
        }, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": f"Execution timed out after {timeout} seconds",
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "safety_check": "passed",
            "safety_reason": ""
        })
    except FileNotFoundError:
        return json.dumps({
            "status": "error",
            "message": "Bash shell not found. Make sure bash is installed and available in PATH.",
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "safety_check": "passed",
            "safety_reason": ""
        })
    except Exception as e:
        error_msg = f"Failed to execute Bash command: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "safety_check": "passed",
            "safety_reason": ""
        })


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_bash",
        "description": "Execute Bash shell commands with safety checks. Use this for system administration, file operations, or running command-line tools. Dangerous commands are blocked by default.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Bash command to execute"
                },
                "allow_dangerous": {
                    "type": "boolean",
                    "description": "Allow potentially dangerous commands (default: false). Use with extreme caution.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 30)",
                    "minimum": 1,
                    "maximum": 300
                }
            },
            "required": ["command"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_bash