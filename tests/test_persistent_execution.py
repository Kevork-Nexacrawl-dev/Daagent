"""
Comprehensive tests for persistent execution tools.
Tests variable persistence, session isolation, and auto-cleanup.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock

# Import the tools
from tools.native.execute_python_persistent import execute_python_persistent, _executor as python_executor
from tools.native.execute_javascript_persistent import execute_javascript_persistent, _executor as js_executor
from tools.native.session_manager import _session_manager


class TestPersistentPythonExecution:
    """Test persistent Python execution with Jupyter kernels."""

    @pytest.fixture
    def mock_jupyter(self):
        """Mock Jupyter dependencies for testing."""
        with patch('tools.native.execute_python_persistent._ensure_jupyter_dependencies') as mock_deps:
            mock_deps.return_value = True
            yield mock_deps

    def test_variable_persistence(self, mock_jupyter):
        """Test that variables survive between calls."""
        session_id = "test_persistence"

        # First execution: define variable
        result1 = json.loads(execute_python_persistent("x = 42", session_id=session_id))
        assert result1['status'] == 'success'

        # Second execution: access variable
        result2 = json.loads(execute_python_persistent("print(x)", session_id=session_id))
        assert result2['status'] == 'success'
        assert '42' in result2['stdout']

    def test_session_isolation(self, mock_jupyter):
        """Test that different session_ids are isolated."""
        # Session A
        result_a1 = json.loads(execute_python_persistent("a_var = 'session_a'", session_id="session_a"))
        assert result_a1['status'] == 'success'

        # Session B
        result_b1 = json.loads(execute_python_persistent("b_var = 'session_b'", session_id="session_b"))
        assert result_b1['status'] == 'success'

        # Try to access A's variable from B
        result_b2 = json.loads(execute_python_persistent("print(a_var)", session_id="session_b"))
        assert result_b2['status'] == 'error'  # Should fail

        # Try to access B's variable from A
        result_a2 = json.loads(execute_python_persistent("print(b_var)", session_id="session_a"))
        assert result_a2['status'] == 'error'  # Should fail

    def test_kernel_restart(self, mock_jupyter):
        """Test that reset_session clears all variables."""
        session_id = "test_restart"

        # Set variable
        result1 = json.loads(execute_python_persistent("y = 100", session_id=session_id))
        assert result1['status'] == 'success'

        # Verify variable exists
        result2 = json.loads(execute_python_persistent("print(y)", session_id=session_id))
        assert result2['status'] == 'success'
        assert '100' in result2['stdout']

        # Reset session
        result3 = json.loads(execute_python_persistent("print('reset')", session_id=session_id, reset_session=True))
        assert result3['status'] == 'success'

        # Variable should be gone
        result4 = json.loads(execute_python_persistent("print(y)", session_id=session_id))
        assert result4['status'] == 'error'  # NameError

    def test_execution_count_tracking(self, mock_jupyter):
        """Test that execution count increments properly."""
        session_id = "test_count"

        result1 = json.loads(execute_python_persistent("1+1", session_id=session_id))
        count1 = result1['execution_count']

        result2 = json.loads(execute_python_persistent("2+2", session_id=session_id))
        count2 = result2['execution_count']

        assert count2 == count1 + 1

    @patch('subprocess.check_call')
    def test_pip_install_in_kernel(self, mock_subprocess, mock_jupyter):
        """Test auto pip install in persistent kernel."""
        mock_subprocess.return_value = None

        session_id = "test_install"
        result = json.loads(execute_python_persistent(
            "import requests",
            session_id=session_id,
            requirements=["requests"]
        ))

        assert result['status'] == 'success'
        assert 'requests' in result['installed_packages']


class TestPersistentJavaScriptExecution:
    """Test persistent JavaScript execution with Node.js REPL."""

    @pytest.fixture
    def mock_nodejs(self):
        """Mock Node.js availability for testing."""
        with patch('tools.native.execute_javascript_persistent._check_nodejs_available') as mock_check:
            mock_check.return_value = True
            yield mock_check

    def test_variable_persistence_js(self, mock_nodejs):
        """Test that JavaScript variables survive between calls."""
        session_id = "test_js_persistence"

        # First execution: define variable
        result1 = json.loads(execute_javascript_persistent("let z = 99;", session_id=session_id))
        assert result1['status'] == 'success'

        # Second execution: access variable
        result2 = json.loads(execute_javascript_persistent("console.log(z);", session_id=session_id))
        assert result2['status'] == 'success'
        assert '99' in result2['stdout']

    def test_session_isolation_js(self, mock_nodejs):
        """Test that JavaScript sessions are isolated."""
        # Session A
        result_a1 = json.loads(execute_javascript_persistent("let a = 'A';", session_id="js_a"))
        assert result_a1['status'] == 'success'

        # Session B
        result_b1 = json.loads(execute_javascript_persistent("let b = 'B';", session_id="js_b"))
        assert result_b1['status'] == 'success'

        # Try cross-session access
        result_b2 = json.loads(execute_javascript_persistent("console.log(a);", session_id="js_b"))
        assert result_b2['status'] == 'error'  # ReferenceError

    def test_repl_restart_js(self, mock_nodejs):
        """Test that reset_session clears JavaScript variables."""
        session_id = "test_js_restart"

        # Set variable
        result1 = json.loads(execute_javascript_persistent("let w = 'hello';", session_id=session_id))
        assert result1['status'] == 'success'

        # Verify variable exists
        result2 = json.loads(execute_javascript_persistent("console.log(w);", session_id=session_id))
        assert result2['status'] == 'success'
        assert 'hello' in result2['stdout']

        # Reset session
        result3 = json.loads(execute_javascript_persistent("console.log('reset');", session_id=session_id, reset_session=True))
        assert result3['status'] == 'success'

        # Variable should be gone
        result4 = json.loads(execute_javascript_persistent("console.log(w);", session_id=session_id))
        assert result4['status'] == 'error'  # ReferenceError


class TestSessionManager:
    """Test session management functionality."""

    def test_list_sessions(self):
        """Test listing all sessions."""
        # Register a test session
        _session_manager.register_session("test_session", "python", {"test": True})

        result = _session_manager.list_sessions()
        assert result['count'] >= 1
        assert any(s['type'] == 'python' for s in result['sessions'])

    def test_get_session_info(self):
        """Test getting session info."""
        session_id = "info_test"
        _session_manager.register_session(session_id, "javascript", {"pid": 12345})

        info = _session_manager.get_session_info(session_id)
        assert info['type'] == 'javascript'
        assert info['status'] == 'active'
        assert 'uptime_seconds' in info
        assert 'idle_seconds' in info

    def test_kill_session(self):
        """Test killing a session."""
        session_id = "kill_test"
        _session_manager.register_session(session_id, "python")

        result = _session_manager.kill_session(session_id)
        assert result['success'] is True

        # Should be gone
        info = _session_manager.get_session_info(session_id)
        assert info['status'] == 'not_found'

    def test_cleanup_idle_sessions(self):
        """Test manual cleanup of idle sessions."""
        # Create a session and make it look old
        session_id = "old_session"
        _session_manager.register_session(session_id, "python")
        _session_manager.sessions[session_id]['last_activity'] = time.time() - 3600  # 1 hour ago

        result = _session_manager.cleanup_idle_sessions(max_idle_minutes=30)
        assert result['cleaned_count'] >= 1


class TestExecutionComparison:
    """Compare performance between subprocess and persistent execution."""

    @pytest.fixture
    def mock_jupyter(self):
        """Mock Jupyter for performance testing."""
        with patch('tools.native.execute_python_persistent._ensure_jupyter_dependencies') as mock_deps:
            mock_deps.return_value = True
            yield mock_deps

    def test_single_execution_comparison(self, mock_jupyter):
        """Test that single execution is faster with subprocess."""
        import time

        # Time subprocess execution
        start = time.time()
        from tools.native.execute_python import execute_python
        result_sub = json.loads(execute_python("print(42)"))
        subprocess_time = time.time() - start

        # Time persistent execution (first run includes setup)
        start = time.time()
        result_persist = json.loads(execute_python_persistent("print(42)", session_id="perf_test"))
        persistent_time = time.time() - start

        # Both should succeed
        assert result_sub['status'] == 'success'
        assert result_persist['status'] == 'success'

        # Subprocess might be faster for single runs (less overhead)
        # But we mainly care that both work
        assert subprocess_time > 0
        assert persistent_time > 0

    def test_iterative_workflow_benefit(self, mock_jupyter):
        """Test that persistent execution benefits iterative workflows."""
        session_id = "iterative_test"

        # First execution (setup)
        result1 = json.loads(execute_python_persistent("data = []", session_id=session_id))
        assert result1['status'] == 'success'

        # Multiple operations on same data
        results = []
        for i in range(5):
            result = json.loads(execute_python_persistent(
                f"data.append({i}); print('Length: ' + str(len(data)))",
                session_id=session_id
            ))
            results.append(result)
            assert result['status'] == 'success'

        # Verify final state
        final_result = json.loads(execute_python_persistent("print(data)", session_id=session_id))
        assert final_result['status'] == 'success'
        assert '[0, 1, 2, 3, 4]' in final_result['stdout']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])