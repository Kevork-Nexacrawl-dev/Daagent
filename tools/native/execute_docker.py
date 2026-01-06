"""
Docker container management tool for Daagent.
Executes Docker commands with safety checks and timeout protection.
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _is_dangerous_docker_args(operation: str, args: List[str]) -> tuple[bool, str]:
    """
    Check if Docker command contains dangerous arguments.

    Args:
        operation: Docker operation (run, build, etc.)
        args: List of command arguments

    Returns:
        Tuple of (is_dangerous, reason)
    """
    dangerous_patterns = [
        # Privilege escalation
        ("--privileged", "Privileged mode grants full host access"),
        ("--network=host", "Host network mode can access host services"),
        ("--pid=host", "Host PID namespace access"),
        ("--ipc=host", "Host IPC namespace access"),
        ("--userns=host", "Host user namespace access"),

        # Dangerous mounts
        ("-v /:/", "Mounting host root filesystem"),
        ("--mount.*type=bind.*source=/", "Binding host root filesystem"),
        ("-v /etc:/", "Mounting host /etc directory"),
        ("-v /var:/", "Mounting host /var directory"),
    ]

    args_str = ' '.join(args)
    for pattern, reason in dangerous_patterns:
        if re.search(re.escape(pattern), args_str, re.IGNORECASE):
            return True, reason

    return False, ""


def _check_docker_available() -> bool:
    """
    Check if Docker is available and running.

    Returns:
        True if Docker is available, False otherwise
    """
    try:
        result = subprocess.run(["docker", "version"],
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def _build_docker_command(operation: str, **kwargs) -> List[str]:
    """
    Build Docker command from operation and parameters.

    Args:
        operation: Docker operation
        **kwargs: Operation-specific parameters

    Returns:
        List of command arguments
    """
    cmd = ["docker", operation]

    if operation == "run":
        if kwargs.get("detached", False):
            cmd.append("-d")
        if kwargs.get("name"):
            cmd.extend(["--name", kwargs["name"]])
        if kwargs.get("privileged", False):
            cmd.append("--privileged")
        if kwargs.get("network"):
            cmd.extend(["--network", kwargs["network"]])
        if kwargs.get("mounts"):
            for mount in kwargs["mounts"]:
                if mount.get("type") == "bind":
                    cmd.extend(["-v", f"{mount['source']}:{mount['target']}"])
                elif mount.get("type") == "volume":
                    cmd.extend(["-v", f"{mount['source']}:{mount['target']}"])
        if kwargs.get("image"):
            cmd.append(kwargs["image"])
        if kwargs.get("command"):
            cmd.extend(kwargs["command"] if isinstance(kwargs["command"], list) else [kwargs["command"]])

    elif operation == "build":
        if kwargs.get("tag"):
            cmd.extend(["-t", kwargs["tag"]])
        if kwargs.get("dockerfile"):
            cmd.extend(["-f", kwargs["dockerfile"]])
        if kwargs.get("context", "."):
            cmd.append(kwargs["context"])

    elif operation == "exec":
        if kwargs.get("container"):
            cmd.append(kwargs["container"])
        if kwargs.get("command"):
            cmd.extend(kwargs["command"] if isinstance(kwargs["command"], list) else [kwargs["command"]])

    elif operation == "ps":
        if kwargs.get("all", False):
            cmd.append("-a")
        if kwargs.get("quiet", False):
            cmd.append("-q")

    elif operation == "logs":
        if kwargs.get("container"):
            cmd.append(kwargs["container"])
        if kwargs.get("follow", False):
            cmd.append("-f")

    elif operation == "stop":
        if kwargs.get("containers"):
            cmd.extend(kwargs["containers"] if isinstance(kwargs["containers"], list) else [kwargs["containers"]])
        if kwargs.get("time"):
            cmd.extend(["-t", str(kwargs["time"])])

    elif operation == "rm":
        if kwargs.get("containers"):
            cmd.extend(kwargs["containers"] if isinstance(kwargs["containers"], list) else [kwargs["containers"]])
        if kwargs.get("force", False):
            cmd.append("-f")

    return cmd


def execute_docker(operation: str, allow_dangerous: bool = False, timeout: int = 60, **kwargs) -> str:
    """
    Execute Docker command with safety checks.

    Args:
        operation: Docker operation ('run', 'build', 'exec', 'ps', 'logs', 'stop', 'rm')
        allow_dangerous: Allow potentially dangerous operations (default: False)
        timeout: Execution timeout in seconds (default: 60)
        **kwargs: Operation-specific parameters

    Returns:
        JSON string containing execution results:
        {
            "status": "success" | "error",
            "operation": executed operation,
            "container_id": container ID if applicable,
            "stdout": captured stdout,
            "stderr": captured stderr,
            "returncode": process return code,
            "safety_check": "passed" | "bypassed" | "blocked",
            "safety_reason": reason if blocked
        }
    """
    try:
        # Check Docker availability
        if not _check_docker_available():
            return json.dumps({
                "status": "error",
                "message": "Docker not found or not running. Make sure Docker is installed and the daemon is running.",
                "operation": operation,
                "container_id": "",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "safety_check": "passed",
                "safety_reason": ""
            })

        # Build command
        cmd = _build_docker_command(operation, **kwargs)

        # Safety check
        is_dangerous, reason = _is_dangerous_docker_args(operation, cmd[2:])  # Skip 'docker operation'
        if is_dangerous and not allow_dangerous:
            return json.dumps({
                "status": "error",
                "message": f"Docker command blocked for safety: {reason}",
                "operation": operation,
                "container_id": "",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "safety_check": "blocked",
                "safety_reason": reason
            })

        safety_status = "bypassed" if allow_dangerous else "passed"

        # Create workspace directory
        workspace_dir = Path("./workspace/docker")
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Execute the command
        logger.info(f"Executing Docker {operation} command (safety: {safety_status})")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=workspace_dir)

        # Extract container ID if applicable
        container_id = ""
        if operation in ["run", "exec"] and result.returncode == 0:
            # For run command, container ID is in stdout
            if operation == "run" and result.stdout.strip():
                container_id = result.stdout.strip().split('\n')[-1]
            # For exec, we don't get container ID back

        return json.dumps({
            "status": "success" if result.returncode == 0 else "error",
            "operation": operation,
            "container_id": container_id,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "safety_check": safety_status,
            "safety_reason": "" if safety_status != "blocked" else reason
        }, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": f"Docker command timed out after {timeout} seconds",
            "operation": operation,
            "container_id": "",
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "safety_check": "passed",
            "safety_reason": ""
        })
    except Exception as e:
        error_msg = f"Failed to execute Docker command: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg,
            "operation": operation,
            "container_id": "",
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
        "name": "execute_docker",
        "description": "Execute Docker container management commands. Supports building, running, and managing containers. Dangerous operations like privileged mode are blocked by default.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["run", "build", "exec", "ps", "logs", "stop", "rm"],
                    "description": "Docker operation to perform"
                },
                "allow_dangerous": {
                    "type": "boolean",
                    "description": "Allow potentially dangerous operations (default: false). Use with extreme caution.",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 60)",
                    "minimum": 1,
                    "maximum": 600,
                    "default": 60
                },
                # Run operation parameters
                "image": {
                    "type": "string",
                    "description": "Docker image to run (for run operation)"
                },
                "name": {
                    "type": "string",
                    "description": "Container name (for run operation)"
                },
                "detached": {
                    "type": "boolean",
                    "description": "Run container in detached mode (for run operation)",
                    "default": False
                },
                "command": {
                    "type": "string",
                    "description": "Command to run inside container (for run/exec operations)"
                },
                # Build operation parameters
                "tag": {
                    "type": "string",
                    "description": "Image tag for build (for build operation)"
                },
                "dockerfile": {
                    "type": "string",
                    "description": "Path to Dockerfile (for build operation)"
                },
                "context": {
                    "type": "string",
                    "description": "Build context path (for build operation)",
                    "default": "."
                },
                # Container operations parameters
                "container": {
                    "type": "string",
                    "description": "Container name or ID (for exec/logs operations)"
                },
                "containers": {
                    "type": "string",
                    "description": "Container names or IDs (for stop/rm operations)"
                },
                # List operation parameters
                "all": {
                    "type": "boolean",
                    "description": "Show all containers including stopped (for ps operation)",
                    "default": False
                },
                "quiet": {
                    "type": "boolean",
                    "description": "Only show container IDs (for ps operation)",
                    "default": False
                },
                # Logs operation parameters
                "follow": {
                    "type": "boolean",
                    "description": "Follow log output (for logs operation)",
                    "default": False
                },
                # Stop operation parameters
                "time": {
                    "type": "integer",
                    "description": "Seconds to wait before killing container (for stop operation)",
                    "default": 10
                },
                # Remove operation parameters
                "force": {
                    "type": "boolean",
                    "description": "Force removal of running containers (for rm operation)",
                    "default": False
                }
            },
            "required": ["operation"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_docker