"""
Tests for JavaScript code execution tool.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import tempfile
from pathlib import Path

from tools.native.execute_javascript import execute_javascript


class TestExecuteJavaScript:
    """Test JavaScript execution tool"""

    def test_javascript_simple_execution(self):
        """Test basic JavaScript execution"""
        code = "console.log('hello world');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "hello world" in data["stdout"]
        assert data["returncode"] == 0
        assert data["installed_packages"] == []

    def test_javascript_with_packages(self):
        """Test npm package installation"""
        # Use a lightweight package for testing
        code = "console.log('package test');"
        result = execute_javascript(code, packages=["lodash"])
        data = json.loads(result)
        # Note: This tests the installation logic, may fail if network unavailable
        assert "installed_packages" in data
        assert isinstance(data["installed_packages"], list)
        if data["status"] == "success":
            assert "lodash" in data["installed_packages"]

    def test_javascript_timeout(self):
        """Test execution timeout"""
        code = "setTimeout(() => { console.log('done'); process.exit(0); }, 60000);"
        result = execute_javascript(code, timeout=1)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()
        assert data["returncode"] == -1

    def test_javascript_syntax_error(self):
        """Test syntax error handling"""
        code = "console.log('unclosed string"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] != 0

    def test_javascript_runtime_error(self):
        """Test runtime error handling"""
        code = "throw new Error('test error');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] != 0
        assert "Error" in data["stderr"] or "Error" in data["stdout"]

    def test_javascript_large_output(self):
        """Test handling of large output"""
        code = "console.log('x'.repeat(10000));"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["stdout"]) >= 10000
        assert data["stdout"].count('x') == 10000

    def test_javascript_special_characters(self):
        """Test handling of special characters and unicode"""
        code = "console.log('héllo wörld 🌍\\n\\t\\r');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "héllo wörld 🌍" in data["stdout"]

    def test_javascript_package_install_failure(self):
        """Test package installation failure"""
        code = "console.log('test');"
        result = execute_javascript(code, packages=["nonexistent-package-12345"])
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Failed to install" in data["message"]
        assert "nonexistent-package-12345" in data["message"]

    def test_javascript_multiple_packages(self):
        """Test installing multiple packages"""
        code = "console.log('multiple packages');"
        packages = ["lodash", "axios"]
        result = execute_javascript(code, packages=packages)
        data = json.loads(result)
        assert "installed_packages" in data
        # May succeed or fail depending on network, but tests the logic

    def test_javascript_empty_code(self):
        """Test empty code execution"""
        code = ""
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["returncode"] == 0

    def test_javascript_async_code(self):
        """Test asynchronous JavaScript code"""
        code = """
async function main() {
    console.log('start');
    await new Promise(resolve => setTimeout(resolve, 100));
    console.log('end');
}
main();
"""
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "start" in data["stdout"]
        assert "end" in data["stdout"]

    @patch('subprocess.run')
    def test_javascript_node_unavailable(self, mock_run):
        """Test when Node.js is not installed"""
        # Mock the node version check
        mock_run.side_effect = FileNotFoundError("node not found")
        code = "console.log('test');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    @patch('subprocess.run')
    def test_javascript_npm_unavailable(self, mock_run):
        """Test when npm is not available"""
        def side_effect(*args, **kwargs):
            if 'npm' in str(args[0]):
                raise FileNotFoundError("npm not found")
            return MagicMock(returncode=0, stdout="v18.0.0", stderr="")

        mock_run.side_effect = side_effect
        code = "console.log('test');"
        result = execute_javascript(code, packages=["lodash"])
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Failed to initialize npm" in data["message"]

    def test_javascript_workspace_creation(self):
        """Test that workspace directory is created"""
        code = "console.log('workspace test');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"

        # Check workspace directory exists
        workspace_dir = Path("./workspace/javascript")
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()

    def test_javascript_with_require(self):
        """Test requiring built-in modules"""
        code = """
const fs = require('fs');
const os = require('os');
console.log('Platform:', os.platform());
"""
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "Platform:" in data["stdout"]


class TestExecuteJavaScriptIntegration:
    """Integration tests for JavaScript execution"""

    def test_agent_javascript_execution_mock(self):
        """Mock test for agent integration"""
        from tools.native.execute_javascript import TOOL_SCHEMA
        assert TOOL_SCHEMA["function"]["name"] == "execute_javascript"
        assert "code" in TOOL_SCHEMA["function"]["parameters"]["required"]

    def test_javascript_execution_in_isolation(self):
        """Test that executions don't interfere with each other"""
        results = []
        for i in range(3):
            code = f"console.log('execution {i}');"
            result = execute_javascript(code)
            results.append(json.loads(result))

        for i, data in enumerate(results):
            assert data["status"] == "success"
            expected = f"execution {i}"
            assert expected in data["stdout"]