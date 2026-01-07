"""
Session management system for Daagent.
Centralized lifecycle management for persistent execution sessions.
"""

import json
import logging
import time
import threading
import psutil
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages persistent execution sessions across all tools.

    Responsibilities:
    - Track active sessions (kernel PIDs, REPL processes)
    - Auto-cleanup idle sessions after timeout
    - Provide session status/info
    - Force kill sessions on demand
    """

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.cleanup_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while True:
                try:
                    self._cleanup_idle_sessions()
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
                    time.sleep(60)  # Retry after 1 minute

        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_idle_sessions(self, max_idle_minutes: int = 30) -> int:
        """Auto-cleanup idle sessions, return count cleaned."""
        current_time = time.time()
        max_idle_seconds = max_idle_minutes * 60
        cleaned_count = 0

        with self._lock:
            sessions_to_remove = []

            for session_id, session_info in self.sessions.items():
                last_activity = session_info.get('last_activity', 0)
                if current_time - last_activity > max_idle_seconds:
                    logger.info(f"Auto-cleaning idle session: {session_id} ({session_info.get('type', 'unknown')})")

                    # Kill the session
                    self._kill_session_processes(session_id, session_info)
                    sessions_to_remove.append(session_id)
                    cleaned_count += 1

            # Remove from tracking
            for session_id in sessions_to_remove:
                del self.sessions[session_id]

        if cleaned_count > 0:
            logger.info(f"Auto-cleaned {cleaned_count} idle sessions")

        return cleaned_count

    def _kill_session_processes(self, session_id: str, session_info: Dict[str, Any]):
        """Kill processes associated with a session."""
        session_type = session_info.get('type')

        if session_type == 'python':
            # Kill Jupyter kernel
            try:
                from .execute_python_persistent import _executor
                _executor.kill_session(session_id)
            except Exception as e:
                logger.error(f"Error killing Python session {session_id}: {e}")

        elif session_type == 'javascript':
            # Kill Node.js REPL
            try:
                from .execute_javascript_persistent import _executor
                _executor.kill_session(session_id)
            except Exception as e:
                logger.error(f"Error killing JavaScript session {session_id}: {e}")

        # Kill by PID if available
        pid = session_info.get('pid')
        if pid:
            try:
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Killed process {pid} for session {session_id}")
            except (psutil.NoSuchProcess, psutil.TimeoutExpired) as e:
                logger.warning(f"Could not kill process {pid}: {e}")
            except Exception as e:
                logger.error(f"Error killing process {pid}: {e}")

    def register_session(self, session_id: str, session_type: str, metadata: Dict[str, Any] = None):
        """Register a new session."""
        with self._lock:
            self.sessions[session_id] = {
                'type': session_type,
                'created_at': time.time(),
                'last_activity': time.time(),
                'status': 'active',
                **(metadata or {})
            }
            logger.info(f"Registered session: {session_id} ({session_type})")

    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a session."""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]['last_activity'] = time.time()

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get detailed info about a specific session."""
        with self._lock:
            if session_id not in self.sessions:
                return {'status': 'not_found', 'session_id': session_id}

            session_info = self.sessions[session_id].copy()

            # Add computed fields
            session_info['uptime_seconds'] = time.time() - session_info['created_at']
            session_info['idle_seconds'] = time.time() - session_info['last_activity']

            # Add process info if PID available
            pid = session_info.get('pid')
            if pid:
                try:
                    process = psutil.Process(pid)
                    session_info['process_info'] = {
                        'cpu_percent': process.cpu_percent(),
                        'memory_mb': process.memory_info().rss / 1024 / 1024,
                        'status': process.status()
                    }
                except psutil.NoSuchProcess:
                    session_info['process_info'] = {'status': 'terminated'}
                except Exception as e:
                    session_info['process_info'] = {'error': str(e)}

            return session_info

    def list_sessions(self, session_type: Optional[str] = None) -> Dict[str, Any]:
        """List all active sessions, optionally filtered by type."""
        with self._lock:
            sessions = []
            for session_id, session_info in self.sessions.items():
                if session_type is None or session_info.get('type') == session_type:
                    info = self.get_session_info(session_id)
                    sessions.append(info)

            return {
                'sessions': sessions,
                'count': len(sessions),
                'types': list(set(s['type'] for s in sessions if 'type' in s))
            }

    def kill_session(self, session_id: str) -> Dict[str, Any]:
        """Force kill a session."""
        with self._lock:
            if session_id not in self.sessions:
                return {
                    'success': False,
                    'message': f'Session not found: {session_id}'
                }

            session_info = self.sessions[session_id]
            logger.info(f"Killing session: {session_id} ({session_info.get('type', 'unknown')})")

            # Kill processes
            self._kill_session_processes(session_id, session_info)

            # Remove from tracking
            del self.sessions[session_id]

            return {
                'success': True,
                'message': f'Session killed: {session_id}',
                'session_type': session_info.get('type')
            }

    def cleanup_idle_sessions(self, max_idle_minutes: int = 30) -> Dict[str, Any]:
        """Manually trigger cleanup of idle sessions."""
        cleaned_count = self._cleanup_idle_sessions(max_idle_minutes)
        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'message': f'Cleaned {cleaned_count} idle sessions'
        }


# Global session manager instance
_session_manager = SessionManager()


def list_sessions(session_type: Optional[str] = None) -> str:
    """List all active persistent execution sessions."""
    result = _session_manager.list_sessions(session_type)
    return json.dumps(result, indent=2)


def get_session_info(session_id: str) -> str:
    """Get detailed info about a specific session."""
    result = _session_manager.get_session_info(session_id)
    return json.dumps(result, indent=2)


def kill_session(session_id: str, session_type: str) -> str:
    """Force kill a persistent session."""
    result = _session_manager.kill_session(session_id)
    return json.dumps(result, indent=2)


# Tool schemas for OpenAI function calling
LIST_SESSIONS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_sessions",
        "description": "List all active persistent execution sessions (Python kernels, JavaScript REPLs)",
        "parameters": {
            "type": "object",
            "properties": {
                "session_type": {
                    "type": "string",
                    "enum": ["python", "javascript", None],
                    "description": "Filter by session type (optional)"
                }
            }
        }
    }
}

GET_SESSION_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_session_info",
        "description": "Get detailed info about a specific session (status, uptime, last activity)",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to query"
                }
            },
            "required": ["session_id"]
        }
    }
}

KILL_SESSION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "kill_session",
        "description": "Force kill a persistent session (use when session is stuck or needs cleanup)",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to kill"
                }
            },
            "required": ["session_id"]
        }
    }
}

# Tool schemas list for auto-discovery
TOOL_SCHEMAS = [
    LIST_SESSIONS_SCHEMA,
    GET_SESSION_INFO_SCHEMA,
    KILL_SESSION_SCHEMA
]

# Alias for compatibility
execute_tool = list_sessions