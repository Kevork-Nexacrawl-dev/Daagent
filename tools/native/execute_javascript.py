"""
JavaScript/Node.js code execution tool for Daagent.
Executes JavaScript code with optional npm package installation.
"""

import json
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def execute_javascript(code: str, packages: Optional[List[str]] = None, timeout: int = 30) -> str:
    """
    Execute JavaScript code with optional npm package installation.

    Args:
        code: JavaScript code to execute
        packages: List of npm packages to install before execution
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
        # Check if Node.js is available
        try:
            node_check = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if node_check.returncode != 0:
                return json.dumps({
                    "status": "error",
                    "message": "Node.js is not installed or not available in PATH",
                    "stdout": node_check.stdout,
                    "stderr": node_check.stderr,
                    "returncode": node_check.returncode,
                    "installed_packages": []
                })
        except FileNotFoundError:
            return json.dumps({
                "status": "error",
                "message": "Node.js executable 'node' not found in PATH",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "installed_packages": []
            })

        # Create workspace directory
        workspace_dir = Path("./workspace/javascript")
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Install packages if provided
        installed_packages = []
        if packages:
            logger.info(f"Installing npm packages: {packages}")

            # Initialize package.json if it doesn't exist
            package_json = workspace_dir / "package.json"
            if not package_json.exists():
                init_result = subprocess.run(
                    ["npm", "init", "-y"],
                    cwd=workspace_dir,
                    capture_output=True, text=True, timeout=30
                )
                if init_result.returncode != 0:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to initialize npm project: {init_result.stderr}",
                        "stdout": init_result.stdout,
                        "stderr": init_result.stderr,
                        "returncode": init_result.returncode,
                        "installed_packages": []
                    })

            # Install each package
            for package in packages:
                try:
                    result = subprocess.run([
                        "npm", "install", package
                    ], cwd=workspace_dir, capture_output=True, text=True, timeout=60)

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

        # Create temporary JavaScript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, dir=workspace_dir) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute the JavaScript code
            logger.info("Executing JavaScript code")
            result = subprocess.run([
                "node", temp_file
            ], capture_output=True, text=True, timeout=timeout, cwd=workspace_dir)

            # Return results
            return json.dumps({
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "installed_packages": installed_packages
            }, indent=2)

        finally:
            # Clean up temporary file
            try:
                Path(temp_file).unlink()
            except Exception:
                pass  # Ignore cleanup errors

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
        error_msg = f"Failed to execute JavaScript code: {str(e)}"
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
        "name": "execute_javascript",
        "description": "Execute JavaScript/Node.js code with optional npm package installation. Use this for web development tasks, API calls, data processing, or any JavaScript programming.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "JavaScript code to execute"
                },
                "packages": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of npm packages to install before execution (optional)"
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
execute_tool = execute_javascript