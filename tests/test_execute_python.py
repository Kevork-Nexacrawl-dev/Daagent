"""
Tests for Python code execution tool.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import tempfile
from pathlib import Path

from tools.native.execute_python import execute_python


class TestExecutePython:
    """Test Python execution tool"""

    def test_python_simple_execution(self):
        """Test basic Python code execution"""
        code = "print('hello world')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "hello world" in data["stdout"]
        assert data["returncode"] == 0
        assert data["installed_packages"] == []

    def test_python_with_requirements(self):
        """Test pip package installation"""
        # Use a lightweight package for testing
        code = "import json; print('package test')"
        result = execute_python(code, requirements=["requests"])
        data = json.loads(result)
        # Note: This tests the installation logic, may fail if network unavailable
        assert "installed_packages" in data
        assert isinstance(data["installed_packages"], list)
        if data["status"] == "success":
            assert "requests" in data["installed_packages"]

    def test_python_timeout(self):
        """Test execution timeout"""
        code = "import time; time.sleep(60)"
        result = execute_python(code, timeout=1)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()
        assert data["returncode"] == -1

    def test_python_invalid_syntax(self):
        """Test syntax error handling"""
        code = "print('unclosed string"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] != 0
        assert "SyntaxError" in data["stderr"] or "SyntaxError" in data["stdout"]

    def test_python_runtime_error(self):
        """Test runtime error handling"""
        code = "raise ValueError('test error')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] != 0
        assert "ValueError" in data["stderr"] or "ValueError" in data["stdout"]

    def test_python_large_output(self):
        """Test handling of large output"""
        code = "print('x' * 10000)"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["stdout"]) >= 10000
        assert data["stdout"].count('x') == 10000

    def test_python_special_characters(self):
        """Test handling of special characters and unicode"""
        code = "print('héllo wörld 🌍\\n\\t\\r')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "héllo wörld 🌍" in data["stdout"]

    def test_python_package_install_failure(self):
        """Test package installation failure"""
        code = "print('test')"
        result = execute_python(code, requirements=["nonexistent-package-12345"])
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Failed to install" in data["message"]
        assert "nonexistent-package-12345" in data["message"]

    def test_python_multiple_packages(self):
        """Test installing multiple packages"""
        code = "import json; print('multiple packages')"
        requirements = ["requests", "beautifulsoup4"]
        result = execute_python(code, requirements=requirements)
        data = json.loads(result)
        assert "installed_packages" in data
        # May succeed or fail depending on network, but tests the logic

    def test_python_empty_code(self):
        """Test empty code execution"""
        code = ""
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["returncode"] == 0

    def test_python_code_with_imports(self):
        """Test code that uses standard library imports"""
        code = """
import sys
import os
print(f"Python version: {sys.version}")
print(f"Current dir: {os.getcwd()}")
"""
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "Python version:" in data["stdout"]
        assert "Current dir:" in data["stdout"]

    @patch('subprocess.run')
    def test_python_subprocess_error(self, mock_run):
        """Test handling of subprocess errors"""
        mock_run.side_effect = Exception("Subprocess failed")
        code = "print('test')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Failed to execute" in data["message"]

    def test_python_workspace_creation(self):
        """Test that workspace directory is created"""
        code = "print('workspace test')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"

        # Check workspace directory exists
        workspace_dir = Path("./workspace/python")
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()


class TestExecutePythonIntegration:
    """Integration tests for Python execution"""

    def test_agent_python_execution_mock(self):
        """Mock test for agent integration"""
        # This would test how the agent calls execute_python
        # For now, just test the tool can be imported and called
        from tools.native.execute_python import TOOL_SCHEMA
        assert TOOL_SCHEMA["function"]["name"] == "execute_python"
        assert "code" in TOOL_SCHEMA["function"]["parameters"]["required"]

    def test_python_execution_in_isolation(self):
        """Test that executions don't interfere with each other"""
        # Run multiple executions to ensure isolation
        results = []
        for i in range(3):
            code = f"print('execution {i}')"
            result = execute_python(code)
            results.append(json.loads(result))

        for i, data in enumerate(results):
            assert data["status"] == "success"
            expected = f"execution {i}"
            assert expected in data["stdout"]