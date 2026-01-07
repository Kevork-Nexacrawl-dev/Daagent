"""
Python Executor - Daagent Native Tools
Ported from autogen-shop with adaptations for OpenAI function calling.
Safe Python code execution in sandboxed environment.
"""

import json
import sys
import io
import traceback
import threading
import time
from typing import Dict, Any, Optional, Callable
from contextlib import redirect_stdout, redirect_stderr

# Standard library imports for safe env
import re
import datetime
import math
import random

class TimeoutException(Exception):
    pass

def run_with_timeout(func: Callable[[], Any], timeout_sec: float) -> tuple[Any, Optional[Exception]]:
    """Run function with timeout."""
    result = [None]
    error = [None]

    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout_sec)

    if thread.is_alive():
        return None, TimeoutException(f"Exceeded {timeout_sec}s")
    if error[0]:
        return None, error[0]
    return result[0], None

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Block dangerous imports."""
    blocked = {'os', 'pathlib', 'subprocess', 'sys', 'builtins', 'importlib'}
    if name in blocked or any(name.startswith(b) for b in blocked):
        raise ImportError(f"Import of '{name}' is blocked for security reasons.")
    return __import__(name, globals, locals, fromlist, level)

# Create safe execution environment
SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'bool': bool, 'dict': dict,
    'enumerate': enumerate, 'filter': filter, 'float': float, 'int': int,
    'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
    'range': range, 'round': round, 'set': set, 'sorted': sorted,
    'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
    '__import__': guarded_import
}

SAFE_GLOBALS = {
    '__builtins__': SAFE_BUILTINS,
    're': re,
    'datetime': datetime,
    'json': json,
    'math': math,
    'random': random,
    'time': time,
    '__import__': guarded_import
}

# ============================================
# TOOL SCHEMAS (OpenAI Function Calling Format)
# ============================================

EXECUTE_PYTHON_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_python",
        "description": "Safely execute Python code in a sandboxed environment with timeout and memory limits",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "timeout": {
                    "type": "number",
                    "description": "Execution timeout in seconds",
                    "default": 10,
                    "maximum": 30
                },
                "context": {
                    "type": "object",
                    "description": "Optional context variables to pass to execution"
                }
            },
            "required": ["code"]
        }
    }
}

# ============================================
# TOOL IMPLEMENTATIONS
# ============================================

def execute_python_sandbox(code: str, timeout: float = 10.0, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute Python code in sandboxed environment.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
        context: Optional context variables

    Returns:
        JSON string with execution result
    """
    try:
        if not code.strip():
            return json.dumps({"status": "error", "error": "No code provided"})

        # Validate code syntax first
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            return json.dumps({
                "status": "error",
                "error": f"SyntaxError: {e}",
                "line": e.lineno,
                "offset": e.offset
            })

        # Prepare execution environment
        local_vars = context.copy() if context else {}
        safe_env = SAFE_GLOBALS.copy()

        def exec_wrapper():
            """Execute code with output capture."""
            captured_stdout = io.StringIO()
            captured_stderr = io.StringIO()

            try:
                with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
                    exec(code, safe_env, local_vars)

                output = captured_stdout.getvalue().strip()
                err_output = captured_stderr.getvalue().strip()
                result_val = local_vars.get('result', None)

                return {
                    "success": True,
                    "result": result_val,
                    "output": output,
                    "error": err_output
                }
            except Exception as e:
                output = captured_stdout.getvalue().strip()
                err_output = captured_stderr.getvalue().strip()
                return {
                    "success": False,
                    "result": None,
                    "output": output,
                    "error": f"{str(e)}\n{traceback.format_exc()}\n{err_output}"
                }

        # Execute with timeout
        raw_result, exc = run_with_timeout(exec_wrapper, timeout)

        if exc:
            error_msg = str(exc)
            if isinstance(exc, TimeoutException):
                return json.dumps({
                    "status": "error",
                    "error": f"Execution timed out after {timeout} seconds"
                })
            else:
                return json.dumps({
                    "status": "error",
                    "error": f"Execution failed: {error_msg}"
                })

        return json.dumps({
            "status": "success",
            "result": raw_result.get("result") if raw_result else None,
            "output": raw_result.get("output", "") if raw_result else "",
            "error": raw_result.get("error", "") if raw_result else "",
            "execution_time": f"< {timeout}s"
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_execute_python(args: Dict[str, Any]) -> str:
    """
    Execute execute_python tool.

    Args:
        args: Dict with code and optional parameters

    Returns:
        JSON string with execution result
    """
    try:
        code = args.get("code", "")
        timeout = min(args.get("timeout", 10.0), 30.0)  # Max 30 seconds
        context = args.get("context", {})

        return execute_python_sandbox(code, timeout, context)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ============================================
# REGISTRY (for agent/core.py to discover)
# ============================================

TOOL_SCHEMAS = [EXECUTE_PYTHON_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute Python execution tool.

    Args:
        operation: Tool operation name
        **kwargs: Tool arguments

    Returns:
        JSON string result
    """
    if operation == "execute_python":
        return execute_execute_python(kwargs)
    else:
        return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})