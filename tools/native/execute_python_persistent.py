"""
Persistent Python execution tool for Daagent.
Uses Jupyter kernel for stateful execution with variable persistence.
"""

import json
import logging
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from queue import Queue, Empty
import atexit

logger = logging.getLogger(__name__)

# Global session storage
_kernel_managers: Dict[str, Dict[str, Any]] = {}
_session_lock = threading.Lock()


class PersistentPythonExecutor:
    """
    Manages persistent Jupyter kernels for stateful Python execution.
    """

    def __init__(self):
        self.kernel_managers = {}
        self.session_info = {}
        self.cleanup_thread = None
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background thread for cleaning up idle sessions."""
        def cleanup_worker():
            while True:
                try:
                    self._cleanup_idle_sessions()
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
                    time.sleep(60)  # Retry after 1 minute on error

        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_idle_sessions(self, max_idle_minutes: int = 30):
        """Clean up idle sessions."""
        current_time = time.time()
        max_idle_seconds = max_idle_minutes * 60
        cleaned_count = 0

        with _session_lock:
            sessions_to_remove = []
            for session_id, info in self.session_info.items():
                if current_time - info['last_activity'] > max_idle_seconds:
                    logger.info(f"Cleaning up idle session: {session_id}")
                    self._shutdown_kernel(session_id)
                    sessions_to_remove.append(session_id)
                    cleaned_count += 1

            for session_id in sessions_to_remove:
                del self.session_info[session_id]

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} idle sessions")

    def _ensure_jupyter_dependencies(self) -> bool:
        """Ensure Jupyter dependencies are installed."""
        required_packages = ['jupyter-client', 'ipykernel']

        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                logger.info(f"Installing missing dependency: {package}")
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pip", "install", "-q", package
                    ], capture_output=True, text=True, timeout=120)

                    if result.returncode != 0:
                        logger.error(f"Failed to install {package}: {result.stderr}")
                        return False

                    logger.info(f"Successfully installed: {package}")
                except Exception as e:
                    logger.error(f"Error installing {package}: {e}")
                    return False

        return True

    def _get_or_create_kernel(self, session_id: str) -> Tuple[Any, Any]:
        """Get existing kernel or create new one for session."""
        if not self._ensure_jupyter_dependencies():
            raise Exception("Failed to install Jupyter dependencies")

        try:
            from jupyter_client import KernelManager, BlockingKernelClient
            from jupyter_client.kernelspec import find_kernel_specs
        except ImportError as e:
            raise Exception(f"Jupyter dependencies not available: {e}")

        with _session_lock:
            if session_id not in self.kernel_managers:
                logger.info(f"Creating new kernel for session: {session_id}")

                # Create kernel manager
                km = KernelManager(kernel_name='python3')
                km.start_kernel()

                # Create and connect client
                kc = km.client()
                kc.start_channels()

                # Initialize session info
                self.kernel_managers[session_id] = {
                    'kernel_manager': km,
                    'kernel_client': kc,
                    'execution_count': 0,
                    'last_activity': time.time(),
                    'created_at': time.time()
                }

                self.session_info[session_id] = {
                    'type': 'python',
                    'status': 'active',
                    'created_at': time.time(),
                    'last_activity': time.time(),
                    'execution_count': 0
                }

                # Wait for kernel to be ready
                kc.wait_for_ready(timeout=30)

            kernel_info = self.kernel_managers[session_id]
            kernel_info['last_activity'] = time.time()
            self.session_info[session_id]['last_activity'] = time.time()

            return kernel_info['kernel_client'], kernel_info

    def _shutdown_kernel(self, session_id: str):
        """Shutdown kernel for session."""
        with _session_lock:
            if session_id in self.kernel_managers:
                try:
                    km = self.kernel_managers[session_id]['kernel_manager']
                    km.shutdown_kernel()
                    logger.info(f"Shutdown kernel for session: {session_id}")
                except Exception as e:
                    logger.error(f"Error shutting down kernel for {session_id}: {e}")
                finally:
                    del self.kernel_managers[session_id]

    def _install_package_in_kernel(self, session_id: str, package: str) -> bool:
        """Install package and make it available in the kernel."""
        try:
            # First install via pip
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Failed to install {package}: {result.stderr}")
                return False

            # Then import in kernel to make it available
            km, kernel_info = self._get_or_create_kernel(session_id)
            client = km.client

            # Execute import in kernel
            code = f"import {package.split('==')[0].split('>=')[0].split('>')[0].split('<')[0].split('!')[0].split(';')[0].strip()}"
            msg_id = client.execute(code)

            # Wait for execution to complete
            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    msg = client.get_iopub_msg(timeout=1)
                    if msg['parent_header']['msg_id'] == msg_id:
                        if msg['msg_type'] == 'execute_result':
                            return True
                        elif msg['msg_type'] == 'error':
                            logger.error(f"Import error in kernel: {msg['content']}")
                            return False
                except Empty:
                    continue

            return True

        except Exception as e:
            logger.error(f"Error installing package {package} in kernel: {e}")
            return False

    def execute_code(self, code: str, session_id: str = "default",
                    requirements: Optional[List[str]] = None,
                    timeout: int = 30, reset_session: bool = False) -> Dict[str, Any]:
        """
        Execute Python code in persistent Jupyter kernel.

        Args:
            code: Python code to execute
            session_id: Session identifier for isolation
            requirements: Packages to install before execution
            timeout: Execution timeout in seconds
            reset_session: Restart kernel and clear all variables

        Returns:
            Dict with execution results
        """
        try:
            # Reset session if requested
            if reset_session:
                logger.info(f"Resetting session: {session_id}")
                self._shutdown_kernel(session_id)

            # Install requirements if provided
            installed_packages = []
            if requirements:
                for package in requirements:
                    if self._install_package_in_kernel(session_id, package):
                        installed_packages.append(package)
                    else:
                        return {
                            'status': 'error',
                            'message': f'Failed to install package: {package}',
                            'stdout': '',
                            'stderr': '',
                            'execution_count': 0,
                            'kernel_status': 'error',
                            'installed_packages': installed_packages
                        }

            # Get or create kernel
            client, kernel_info = self._get_or_create_kernel(session_id)

            # Execute code
            logger.info(f"Executing code in session {session_id}")
            msg_id = client.execute(code, timeout=timeout)

            # Collect output
            stdout_parts = []
            stderr_parts = []
            execution_result = None
            error_info = None

            # Wait for execution to complete
            start_time = time.time()
            while time.time() - start_time < timeout + 5:  # Extra time for message processing
                try:
                    msg = client.get_iopub_msg(timeout=1)

                    if msg['parent_header']['msg_id'] == msg_id:
                        msg_type = msg['msg_type']
                        content = msg['content']

                        if msg_type == 'stream':
                            if content['name'] == 'stdout':
                                stdout_parts.append(content['text'])
                            elif content['name'] == 'stderr':
                                stderr_parts.append(content['text'])

                        elif msg_type == 'execute_result':
                            execution_result = content

                        elif msg_type == 'error':
                            error_info = content
                            break

                        elif msg_type == 'status' and content['execution_state'] == 'idle':
                            # Execution completed
                            break

                except Empty:
                    continue

            # Update session info
            kernel_info['execution_count'] += 1
            kernel_info['last_activity'] = time.time()
            self.session_info[session_id]['execution_count'] = kernel_info['execution_count']
            self.session_info[session_id]['last_activity'] = time.time()

            # Format result
            result = {
                'status': 'success' if error_info is None else 'error',
                'stdout': ''.join(stdout_parts),
                'stderr': ''.join(stderr_parts),
                'execution_count': kernel_info['execution_count'],
                'kernel_status': 'active',
                'installed_packages': installed_packages,
                'session_id': session_id
            }

            if execution_result:
                result['execution_result'] = execution_result

            if error_info:
                result['error'] = error_info
                result['message'] = f"Execution error: {error_info.get('ename', 'Unknown')}: {error_info.get('evalue', '')}"

            return result

        except Exception as e:
            logger.error(f"Error in persistent execution: {e}")
            return {
                'status': 'error',
                'message': f'Persistent execution failed: {str(e)}',
                'stdout': '',
                'stderr': '',
                'execution_count': 0,
                'kernel_status': 'error',
                'installed_packages': [],
                'session_id': session_id
            }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        with _session_lock:
            if session_id in self.session_info:
                info = self.session_info[session_id].copy()
                if session_id in self.kernel_managers:
                    km_info = self.kernel_managers[session_id]
                    info.update({
                        'uptime': time.time() - km_info['created_at'],
                        'last_execution_count': km_info['execution_count']
                    })
                return info
            else:
                return {'status': 'not_found', 'session_id': session_id}

    def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions."""
        with _session_lock:
            return {
                'sessions': list(self.session_info.values()),
                'count': len(self.session_info)
            }

    def kill_session(self, session_id: str) -> bool:
        """Kill a session."""
        with _session_lock:
            if session_id in self.session_info:
                self._shutdown_kernel(session_id)
                del self.session_info[session_id]
                return True
            return False


# Global executor instance
_executor = PersistentPythonExecutor()

# Register cleanup on exit
atexit.register(lambda: [_executor._shutdown_kernel(sid) for sid in list(_executor.kernel_managers.keys())])


def execute_python_persistent(
    code: str,
    session_id: str = "default",
    requirements: Optional[List[str]] = None,
    timeout: int = 30,
    reset_session: bool = False
) -> str:
    """
    Execute Python code in persistent Jupyter kernel.

    Args:
        code: Python code to execute
        session_id: Session identifier for isolation (default: "default")
        requirements: Packages to install before execution
        timeout: Execution timeout in seconds
        reset_session: Restart kernel and clear all variables

    Returns:
        JSON string with execution results
    """
    result = _executor.execute_code(code, session_id, requirements, timeout, reset_session)
    return json.dumps(result, indent=2)


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_python_persistent",
        "description": "Execute Python with persistent session. Variables survive between calls. Use for data analysis, iterative development, or when you need to build on previous results.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "session_id": {
                    "type": "string",
                    "default": "default",
                    "description": "Session ID for isolation (default: 'default')"
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
                },
                "reset_session": {
                    "type": "boolean",
                    "default": False,
                    "description": "Restart kernel and clear all variables"
                }
            },
            "required": ["code"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_python_persistent