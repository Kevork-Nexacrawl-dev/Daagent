"""
Persistent JavaScript execution tool for Daagent.
Uses Node.js REPL for stateful execution with variable persistence.
"""

import json
import logging
import subprocess
import sys
import time
import threading
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from queue import Queue, Empty
import atexit

# Platform-specific imports
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import select
    HAS_SELECT = True
except ImportError:
    HAS_SELECT = False

logger = logging.getLogger(__name__)

# Global session storage
_repl_processes: Dict[str, Dict[str, Any]] = {}
_session_lock = threading.Lock()


class PersistentJavaScriptExecutor:
    """
    Manages persistent Node.js REPL processes for stateful JavaScript execution.
    """

    def __init__(self):
        self.repl_processes = {}
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
                    logger.info(f"Cleaning up idle JavaScript session: {session_id}")
                    self._shutdown_repl(session_id)
                    sessions_to_remove.append(session_id)
                    cleaned_count += 1

            for session_id in sessions_to_remove:
                del self.session_info[session_id]

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} idle JavaScript sessions")

    def _check_nodejs_available(self) -> bool:
        """Check if Node.js is available."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _get_or_create_repl(self, session_id: str) -> Tuple[subprocess.Popen, Dict[str, Any]]:
        """Get existing REPL or create new one for session."""
        if not self._check_nodejs_available():
            raise Exception("Node.js is not installed or not available in PATH")

        with _session_lock:
            if session_id not in self.repl_processes:
                logger.info(f"Creating new Node.js REPL for session: {session_id}")

                # Create REPL process
                try:
                    process = subprocess.Popen(
                        ["node", "-i"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        env=dict(os.environ, NODE_NO_WARNINGS="1")
                    )

                    # Initialize session info
                    self.repl_processes[session_id] = {
                        'process': process,
                        'execution_count': 0,
                        'last_activity': time.time(),
                        'created_at': time.time(),
                        'output_buffer': []
                    }

                    self.session_info[session_id] = {
                        'type': 'javascript',
                        'status': 'active',
                        'created_at': time.time(),
                        'last_activity': time.time(),
                        'execution_count': 0,
                        'pid': process.pid
                    }

                    # Register with session manager
                    try:
                        from .session_manager import _session_manager
                        _session_manager.register_session(session_id, 'javascript', {'pid': process.pid})
                    except ImportError:
                        pass  # Session manager not available

                    # Wait for REPL to be ready (look for > prompt)
                    self._wait_for_repl_ready(session_id)

                except Exception as e:
                    logger.error(f"Failed to create REPL for session {session_id}: {e}")
                    raise

            repl_info = self.repl_processes[session_id]
            repl_info['last_activity'] = time.time()
            self.session_info[session_id]['last_activity'] = time.time()

            return repl_info['process'], repl_info

    def _wait_for_repl_ready(self, session_id: str, timeout: int = 10):
        """Wait for REPL to show ready prompt."""
        process, repl_info = self.repl_processes[session_id]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Try to read prompt
                output = self._read_repl_output(process, timeout=1)
                if '>' in output or 'Welcome to Node.js' in output:
                    return True
            except:
                pass
            time.sleep(0.1)

        logger.warning(f"REPL for session {session_id} may not be ready")
        return False

    def _read_repl_output(self, process: subprocess.Popen, timeout: float = 1.0) -> str:
        """Read output from REPL process."""
        output = ""
        start_time = time.time()

        # Simple approach: read available output
        try:
            # Try to read immediately available output
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    break  # Process terminated

                # Read line if available (non-blocking)
                import io
                if isinstance(process.stdout, io.TextIOWrapper):
                    line = process.stdout.readline()
                    if line:
                        output += line
                    else:
                        # No more lines immediately available
                        break
                else:
                    break

        except Exception as e:
            logger.debug(f"Error reading REPL output: {e}")

        return output

    def _write_repl_input(self, process: subprocess.Popen, code: str):
        """Write input to REPL process."""
        if process.stdin:
            process.stdin.write(code + '\n')
            process.stdin.flush()

    def _shutdown_repl(self, session_id: str):
        """Shutdown REPL for session."""
        with _session_lock:
            if session_id in self.repl_processes:
                try:
                    process = self.repl_processes[session_id]['process']
                    if process.poll() is None:  # Still running
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    logger.info(f"Shutdown REPL for session: {session_id}")
                except Exception as e:
                    logger.error(f"Error shutting down REPL for {session_id}: {e}")
                finally:
                    del self.repl_processes[session_id]

    def _install_package_in_repl(self, session_id: str, package: str) -> bool:
        """Install npm package and make it available in REPL."""
        try:
            # Install via npm
            result = subprocess.run([
                "npm", "install", "-g", package
            ], capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Failed to install {package}: {result.stderr}")
                return False

            # Try to require in REPL
            process, repl_info = self._get_or_create_repl(session_id)

            # Send require statement
            require_code = f"const {package.split('@')[0].split('/').pop()} = require('{package}');"
            self._write_repl_input(process, require_code)

            # Wait a bit for it to load
            time.sleep(1)

            return True

        except Exception as e:
            logger.error(f"Error installing package {package} in REPL: {e}")
            return False

    def execute_code(self, code: str, session_id: str = "default",
                    packages: Optional[List[str]] = None,
                    timeout: int = 30, reset_session: bool = False) -> Dict[str, Any]:
        """
        Execute JavaScript code in persistent Node.js REPL.

        Args:
            code: JavaScript code to execute
            session_id: Session identifier for isolation
            packages: npm packages to install before execution
            timeout: Execution timeout in seconds
            reset_session: Restart REPL process

        Returns:
            Dict with execution results
        """
        try:
            # Reset session if requested
            if reset_session:
                logger.info(f"Resetting JavaScript session: {session_id}")
                self._shutdown_repl(session_id)

            # Install packages if provided
            installed_packages = []
            if packages:
                for package in packages:
                    if self._install_package_in_repl(session_id, package):
                        installed_packages.append(package)
                    else:
                        return {
                            'status': 'error',
                            'message': f'Failed to install package: {package}',
                            'stdout': '',
                            'stderr': '',
                            'execution_count': 0,
                            'repl_status': 'error',
                            'installed_packages': installed_packages
                        }

            # Get or create REPL
            process, repl_info = self._get_or_create_repl(session_id)

            # Check if process is still alive
            if process.poll() is not None:
                logger.warning(f"REPL process died for session {session_id}, restarting")
                self._shutdown_repl(session_id)
                process, repl_info = self._get_or_create_repl(session_id)

            # Execute code
            logger.info(f"Executing JavaScript code in session {session_id}")
            self._write_repl_input(process, code)

            # Read output
            output = self._read_repl_output(process, timeout=timeout)

            # Update session info
            repl_info['execution_count'] += 1
            repl_info['last_activity'] = time.time()
            self.session_info[session_id]['execution_count'] = repl_info['execution_count']
            self.session_info[session_id]['last_activity'] = time.time()

            # Update session manager
            try:
                from .session_manager import _session_manager
                _session_manager.update_session_activity(session_id)
            except ImportError:
                pass

            # Check for errors in output
            has_error = 'Error:' in output or 'SyntaxError:' in output or 'ReferenceError:' in output

            result = {
                'status': 'success' if not has_error else 'error',
                'stdout': output,
                'stderr': '',
                'execution_count': repl_info['execution_count'],
                'repl_status': 'active' if process.poll() is None else 'terminated',
                'installed_packages': installed_packages,
                'session_id': session_id
            }

            if has_error:
                result['message'] = 'JavaScript execution error detected in output'

            return result

        except Exception as e:
            logger.error(f"Error in persistent JavaScript execution: {e}")
            return {
                'status': 'error',
                'message': f'Persistent JavaScript execution failed: {str(e)}',
                'stdout': '',
                'stderr': '',
                'execution_count': 0,
                'repl_status': 'error',
                'installed_packages': [],
                'session_id': session_id
            }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        with _session_lock:
            if session_id in self.session_info:
                return self.session_info[session_id].copy()
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
                self._shutdown_repl(session_id)
                del self.session_info[session_id]
                return True
            return False


# Global executor instance
_executor = PersistentJavaScriptExecutor()

# Register cleanup on exit
atexit.register(lambda: [_executor._shutdown_repl(sid) for sid in list(_executor.repl_processes.keys())])


def execute_javascript_persistent(
    code: str,
    session_id: str = "default",
    packages: Optional[List[str]] = None,
    timeout: int = 30,
    reset_session: bool = False
) -> str:
    """
    Execute JavaScript in persistent Node.js REPL.

    Args:
        code: JavaScript code to execute
        session_id: Session identifier
        packages: npm packages to install
        timeout: Execution timeout
        reset_session: Restart REPL process

    Returns:
        JSON string with execution results
    """
    result = _executor.execute_code(code, session_id, packages, timeout, reset_session)
    return json.dumps(result, indent=2)


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_javascript_persistent",
        "description": "Execute JavaScript with persistent Node.js REPL. Variables survive between calls. Use for API testing, iterative development, or building on previous results.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "JavaScript code to execute"
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
                },
                "reset_session": {
                    "type": "boolean",
                    "default": False,
                    "description": "Restart REPL process"
                }
            },
            "required": ["code"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_javascript_persistent