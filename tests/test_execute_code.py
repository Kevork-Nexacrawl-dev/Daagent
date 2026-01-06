"""
Tests for code execution tools.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import tempfile
from pathlib import Path

from tools.native.execute_python import execute_python
from tools.native.execute_javascript import execute_javascript
from tools.native.execute_bash import execute_bash


class TestExecutePython:
    """Test Python execution tool"""

    def test_python_success(self):
        """Test successful Python execution"""
        code = "print('Hello World')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["stdout"].strip() == "Hello World"
        assert data["returncode"] == 0
        assert data["installed_packages"] == []

    def test_python_with_requirements(self):
        """Test Python execution with package installation"""
        code = "import requests; print('Package imported')"
        result = execute_python(code, requirements=["requests"])
        data = json.loads(result)
        # Note: This might fail if requests is not available, but tests the logic
        assert "installed_packages" in data
        assert isinstance(data["installed_packages"], list)

    def test_python_error(self):
        """Test Python execution with error"""
        code = "print('Hello'); raise ValueError('Test error')"
        result = execute_python(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] != 0
        assert "ValueError" in data["stderr"] or "ValueError" in data["stdout"]

    def test_python_timeout(self):
        """Test Python execution timeout"""
        code = "import time; time.sleep(60)"  # Sleep longer than timeout
        result = execute_python(code, timeout=1)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()


class TestExecuteJavaScript:
    """Test JavaScript execution tool"""

    def test_javascript_success(self):
        """Test successful JavaScript execution"""
        code = "console.log('Hello World');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["stdout"].strip() == "Hello World"
        assert data["returncode"] == 0
        assert data["installed_packages"] == []

    @patch('subprocess.run')
    def test_nodejs_not_found(self, mock_run):
        """Test when Node.js is not available"""
        mock_run.side_effect = FileNotFoundError("node not found")
        code = "console.log('test');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    def test_javascript_error(self):
        """Test JavaScript execution with error"""
        code = "console.log('Hello'); throw new Error('Test error');"
        result = execute_javascript(code)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] != 0

    def test_javascript_timeout(self):
        """Test JavaScript execution timeout"""
        code = "setTimeout(() => console.log('done'), 60000);"  # Wait 60 seconds
        result = execute_javascript(code, timeout=1)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()


class TestExecuteBash:
    """Test Bash execution tool"""

    def test_bash_success(self):
        """Test successful Bash execution"""
        command = "echo 'Hello World'"
        result = execute_bash(command)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["stdout"].strip() == "Hello World"
        assert data["returncode"] == 0
        assert data["safety_check"] == "passed"

    def test_bash_error(self):
        """Test Bash execution with error"""
        command = "echo 'Hello' && exit 1"
        result = execute_bash(command)
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] == 1
        assert "Hello" in data["stdout"]

    def test_bash_dangerous_blocked(self):
        """Test that dangerous commands are blocked"""
        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            ":(){ :|:& };:",  # Fork bomb
            "shutdown -h now"
        ]

        for cmd in dangerous_commands:
            result = execute_bash(cmd)
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["safety_check"] == "blocked"
            assert "blocked" in data["message"].lower()

    def test_bash_allow_dangerous(self):
        """Test bypassing safety checks"""
        # Use a command that would normally be blocked but is actually safe
        command = "echo 'rm -rf /' > /tmp/test.txt && cat /tmp/test.txt"
        result = execute_bash(command, allow_dangerous=True)
        data = json.loads(result)
        assert data["safety_check"] == "bypassed"
        # Note: This might still fail due to actual command safety, but tests the bypass

    def test_bash_timeout(self):
        """Test Bash execution timeout"""
        command = "sleep 60"  # Sleep longer than timeout
        result = execute_bash(command, timeout=1)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()

    @patch('subprocess.run')
    def test_bash_not_found(self, mock_run):
        """Test when bash is not available"""
        mock_run.side_effect = FileNotFoundError("bash not found")
        command = "echo test"
        result = execute_bash(command)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()