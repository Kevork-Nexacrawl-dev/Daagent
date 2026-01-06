"""
PowerShell script execution tool for Daagent.
Executes PowerShell commands with safety checks and timeout protection.
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
        command: The PowerShell command to check
        allow_dangerous: Whether to allow dangerous commands

    Returns:
        Tuple of (is_dangerous, reason)
    """
    if allow_dangerous:
        return False, ""

    dangerous_patterns = [
        # File system destruction
        (r'Remove-Item.*C:.*Recurse.*Force', "Command attempts to delete root filesystem"),
        (r'Format-Volume', "Command attempts to format volumes"),
        (r'Remove-Item.*HKLM:', "Command attempts to delete registry keys"),

        # System operations
        (r'Stop-Computer', "Command attempts to shutdown system"),
        (r'Restart-Computer', "Command attempts to reboot system"),

        # Dangerous web operations
        (r'Invoke-WebRequest.*\|.*Invoke-Expression', "Command downloads and executes remote code"),
        (r'IEX.*New-Object', "Command downloads and executes remote code"),

        # Privilege escalation
        (r'Start-Process.*Verb.*RunAs', "Command attempts privilege escalation"),
    ]

    for pattern, reason in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE | re.DOTALL):
            return True, reason

    return False, ""


def _find_powershell() -> Optional[str]:
    """
    Find available PowerShell executable.

    Returns:
        Path to PowerShell executable or None if not found
    """
    candidates = ["pwsh", "powershell"]
    for candidate in candidates:
        try:
            result = subprocess.run([candidate, "-Command", "Write-Host 'test'"],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return candidate
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            continue
    return None


def execute_powershell(command: str, allow_dangerous: bool = False, timeout: int = 30) -> str:
    """
    Execute PowerShell command with safety checks.

    Args:
        command: PowerShell command to execute
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
        # Find PowerShell executable
        powershell_exe = _find_powershell()
        if not powershell_exe:
            return json.dumps({
                "status": "error",
                "message": "PowerShell not found. Make sure PowerShell Core (pwsh) or Windows PowerShell is installed and available in PATH.",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "safety_check": "passed",
                "safety_reason": ""
            })

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
        workspace_dir = Path("./workspace/powershell")
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Execute the command
        logger.info(f"Executing PowerShell command (safety: {safety_status})")
        result = subprocess.run([
            powershell_exe, "-Command", command
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
    except Exception as e:
        error_msg = f"Failed to execute PowerShell command: {str(e)}"
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
        "name": "execute_powershell",
        "description": "Execute PowerShell commands with safety checks. Use this for Windows system administration, PowerShell scripting, or Windows-specific operations. Dangerous commands are blocked by default.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "PowerShell command to execute"
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
execute_tool = execute_powershell