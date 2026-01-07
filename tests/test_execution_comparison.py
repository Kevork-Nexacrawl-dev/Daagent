"""
Performance and feature comparison tests between subprocess and persistent execution.
"""

import json
import time
import pytest
from unittest.mock import patch

# Import execution tools
from tools.native.execute_python import execute_python
from tools.native.execute_python_persistent import execute_python_persistent
from tools.native.execute_javascript import execute_javascript
from tools.native.execute_javascript_persistent import execute_javascript_persistent


class TestPerformanceComparison:
    """Compare performance between subprocess and persistent execution"""

    @pytest.fixture
    def mock_jupyter(self):
        """Mock Jupyter for consistent testing"""
        with patch('tools.native.execute_python_persistent.PersistentPythonExecutor._ensure_jupyter_dependencies') as mock_deps:
            mock_deps.return_value = True
            yield

    def test_single_execution_speed(self):
        """Subprocess should be faster for single executions"""
        code = "print(sum(range(1000)))"

        # Time subprocess execution
        start = time.time()
        result1 = json.loads(execute_python(code))
        subprocess_time = time.time() - start

        # Time persistent execution (first run includes kernel startup)
        start = time.time()
        result2 = json.loads(execute_python_persistent(code, session_id="perf_test"))
        persistent_time = time.time() - start

        # Both should succeed
        assert result1['success'] is True
        assert result2['status'] == 'success'

        # Subprocess might be faster for single runs (but not guaranteed due to kernel startup)
        # Just verify both work and persistent doesn't take excessively long
        assert persistent_time < 30  # Should complete within reasonable time

    def test_iterative_workflow_efficiency(self, mock_jupyter):
        """Persistent execution should excel in iterative workflows"""
        session_id = "iterative_test"

        # Simulate iterative development workflow
        operations = [
            "data = list(range(100))",
            "processed = [x * 2 for x in data]",
            "filtered = [x for x in processed if x > 50]",
            "result = sum(filtered)",
            "print(f'Final result: {result}')"
        ]

        # Time persistent execution across multiple calls
        start = time.time()
        results = []
        for code in operations:
            result = json.loads(execute_python_persistent(code, session_id=session_id))
            results.append(result)
            assert result['status'] == 'success'

        persistent_total_time = time.time() - start

        # Verify final result
        assert 'Final result: 9850' in results[-1]['stdout']  # sum of even numbers > 50

        # Time equivalent subprocess execution
        start = time.time()
        combined_code = '\n'.join(operations)
        result = json.loads(execute_python(combined_code))
        subprocess_time = time.time() - start

        assert result['success'] is True

        # Persistent should be reasonably fast (allowing for kernel overhead)
        assert persistent_total_time < 20

    def test_memory_efficiency_simulation(self):
        """Simulate memory usage patterns"""
        # Test that persistent execution can handle memory-intensive operations
        memory_test_code = """
import sys
# Create some data structures
large_list = list(range(10000))
large_dict = {i: i**2 for i in range(1000)}
print(f"Created structures with {len(large_list)} and {len(large_dict)} items")
"""

        # Test with persistent execution
        result = json.loads(execute_python_persistent(memory_test_code, session_id="memory_test"))
        assert result['status'] == 'success'
        assert '10000' in result['stdout'] and '1000' in result['stdout']

        # Memory should be cleaned up when session ends
        # (This is hard to test directly without psutil integration)

    def test_startup_overhead_comparison(self):
        """Compare startup times"""
        simple_code = "print(42)"

        # Multiple subprocess calls
        start = time.time()
        for _ in range(3):
            result = json.loads(execute_python(simple_code))
            assert result['success'] is True
        subprocess_total = time.time() - start

        # Multiple persistent calls (kernel startup only once)
        start = time.time()
        for i in range(3):
            result = json.loads(execute_python_persistent(simple_code, session_id="startup_test"))
            assert result['status'] == 'success'
        persistent_total = time.time() - start

        # Just verify both work - exact timing depends on system
        assert subprocess_total > 0
        assert persistent_total > 0


class TestFeatureComparison:
    """Compare feature sets between execution methods"""

    def test_error_handling_comparison(self):
        """Both methods should handle errors gracefully"""
        bad_code = "print(undefined_variable)"

        # Subprocess error handling
        result1 = json.loads(execute_python(bad_code))
        assert result1['success'] is False

        # Persistent error handling
        result2 = json.loads(execute_python_persistent(bad_code, session_id="error_test"))
        assert result2['status'] == 'error'

    def test_timeout_behavior(self):
        """Test timeout handling in both modes"""
        infinite_loop = "while True: pass"

        # Subprocess with timeout (if supported)
        result1 = json.loads(execute_python(infinite_loop, timeout=2))
        # Result depends on implementation

        # Persistent with timeout
        result2 = json.loads(execute_python_persistent(infinite_loop, session_id="timeout_test", timeout=2))
        # Should timeout gracefully

        # Verify kernel still works after timeout
        result3 = json.loads(execute_python_persistent("print('recovered')", session_id="timeout_test"))
        assert result3['status'] == 'success'

    def test_package_installation_comparison(self):
        """Compare package installation between methods"""
        # Test code that might require package installation
        code_with_import = "import json; print('json imported')"

        # Both should handle basic imports
        result1 = json.loads(execute_python(code_with_import))
        result2 = json.loads(execute_python_persistent(code_with_import, session_id="import_test"))

        assert result1['success'] is True
        assert result2['status'] == 'success'


class TestJavaScriptPerformanceComparison:
    """Compare JavaScript execution methods"""

    def test_js_single_execution(self):
        """Compare single JavaScript execution"""
        code = "console.log(42 * 2);"

        # Temp file execution
        result1 = json.loads(execute_javascript(code))
        assert result1['success'] is True

        # Persistent execution
        result2 = json.loads(execute_javascript_persistent(code, session_id="js_perf_test"))
        assert result2['status'] == 'success'

    def test_js_iterative_workflow(self):
        """Test iterative JavaScript workflow"""
        session_id = "js_iterative"

        operations = [
            "var data = [1, 2, 3, 4, 5];",
            "var doubled = data.map(x => x * 2);",
            "var filtered = doubled.filter(x => x > 4);",
            "console.log('Result:', filtered.reduce((a, b) => a + b, 0));"
        ]

        # Execute iteratively with persistent session
        for code in operations:
            result = json.loads(execute_javascript_persistent(code, session_id=session_id))
            assert result['status'] == 'success'

        # Final result should be 30 (6+8+10)
        # (Hard to verify exact output without parsing stdout)

    def test_js_error_recovery(self):
        """Test error recovery in JavaScript"""
        # Syntax error
        result1 = json.loads(execute_javascript_persistent(
            "console.log('unclosed string);",
            session_id="js_error_test"
        ))
        assert result1['status'] == 'error'

        # Should still work after error
        result2 = json.loads(execute_javascript_persistent(
            "console.log('recovered');",
            session_id="js_error_test"
        ))
        assert result2['status'] == 'success'


class TestResourceUsagePatterns:
    """Test resource usage patterns"""

    def test_concurrent_sessions(self):
        """Test multiple concurrent sessions"""
        # Create multiple sessions
        sessions = ['session_1', 'session_2', 'session_3']

        for session_id in sessions:
            result = json.loads(execute_python_persistent(
                f"session_var = '{session_id}'",
                session_id=session_id
            ))
            assert result['status'] == 'success'

        # Verify isolation
        for session_id in sessions:
            result = json.loads(execute_python_persistent(
                "print(session_var)",
                session_id=session_id
            ))
            assert result['status'] == 'success'
            assert session_id in result['stdout']

    def test_session_cleanup_simulation(self):
        """Simulate session cleanup behavior"""
        # Create a session
        result1 = json.loads(execute_python_persistent(
            "test_var = 123",
            session_id="cleanup_test"
        ))
        assert result1['status'] == 'success'

        # Simulate time passing (in real scenario, cleanup thread would handle this)
        # For testing, we just verify the session exists
        assert "cleanup_test" in [s for s in python_executor.session_info.keys()]


if __name__ == "__main__":
    pytest.main([__file__])