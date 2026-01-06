"""
Python code execution tool for Daagent.
Executes Python code with optional pip package installation.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def execute_python(code: str, requirements: Optional[List[str]] = None, timeout: int = 30) -> str:
    """
    Execute Python code with optional package installation.

    Args:
        code: Python code to execute
        requirements: List of pip packages to install before execution
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        JSON string containing execution results:
        {
            "status": "success" | "error",
            "stdout": captured stdout,
            "stderr": captured stderr,
            "returncode": process return code,
            "installed_packages": list of installed packages (if any)
        }
    """
    try:
        # Create workspace directory
        workspace_dir = Path("./workspace/python")
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Install requirements if provided
        installed_packages = []
        if requirements:
            logger.info(f"Installing requirements: {requirements}")
            for package in requirements:
                try:
                    # Use pip to install package
                    result = subprocess.run([
                        sys.executable, "-m", "pip", "install", package
                    ], capture_output=True, text=True, timeout=60)  # Longer timeout for installs

                    if result.returncode != 0:
                        return json.dumps({
                            "status": "error",
                            "message": f"Failed to install package '{package}': {result.stderr}",
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "returncode": result.returncode,
                            "installed_packages": installed_packages
                        })

                    installed_packages.append(package)
                    logger.info(f"Successfully installed: {package}")

                except subprocess.TimeoutExpired:
                    return json.dumps({
                        "status": "error",
                        "message": f"Timeout installing package '{package}'",
                        "stdout": "",
                        "stderr": "",
                        "returncode": -1,
                        "installed_packages": installed_packages
                    })
                except Exception as e:
                    return json.dumps({
                        "status": "error",
                        "message": f"Error installing package '{package}': {str(e)}",
                        "stdout": "",
                        "stderr": "",
                        "returncode": -1,
                        "installed_packages": installed_packages
                    })

        # Execute the Python code
        logger.info("Executing Python code")
        result = subprocess.run([
            sys.executable, "-c", code
        ], capture_output=True, text=True, timeout=timeout, cwd=workspace_dir)

        # Return results
        return json.dumps({
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "installed_packages": installed_packages
        }, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": f"Execution timed out after {timeout} seconds",
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "installed_packages": installed_packages if 'installed_packages' in locals() else []
        })
    except Exception as e:
        error_msg = f"Failed to execute Python code: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "installed_packages": []
        })


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_python",
        "description": "Execute Python code with optional pip package installation. Use this to run Python scripts, perform calculations, data analysis, or any Python programming task.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of pip packages to install before execution (optional)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 30)",
                    "minimum": 1,
                    "maximum": 300
                }
            },
            "required": ["code"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_python