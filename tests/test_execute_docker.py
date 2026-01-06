"""
Tests for Docker execution tool.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import subprocess
from pathlib import Path

from tools.native.execute_docker import execute_docker


class TestExecuteDocker:
    """Test Docker execution tool"""

    @patch('tools.native.execute_docker._check_docker_available')
    def test_docker_not_available(self, mock_check):
        """Test when Docker is not available"""
        mock_check.return_value = False
        result = execute_docker("ps")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "not found or not running" in data["message"]
        assert data["operation"] == "ps"

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_ps_command(self, mock_run, mock_check):
        """Test docker ps command"""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES\nabc123         nginx     nginx     1min      Up        80/tcp    web\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = execute_docker("ps")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["operation"] == "ps"
        assert "nginx" in data["stdout"]
        assert data["safety_check"] == "passed"

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_run_command(self, mock_run, mock_check):
        """Test docker run command"""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123def456\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = execute_docker("run", image="nginx", detached=True)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["operation"] == "run"
        assert data["container_id"] == "abc123def456"

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_dangerous_blocked(self, mock_run, mock_check):
        """Test dangerous Docker command blocking"""
        mock_check.return_value = True

        dangerous_args = [
            {"operation": "run", "image": "ubuntu", "privileged": True},
            {"operation": "run", "image": "ubuntu", "network": "host"},
            {"operation": "run", "image": "ubuntu", "mounts": [{"source": "/", "target": "/host"}]}
        ]

        for kwargs in dangerous_args:
            result = execute_docker(**kwargs)
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["safety_check"] == "blocked"
            assert "blocked for safety" in data["message"]

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_dangerous_allowed(self, mock_run, mock_check):
        """Test dangerous command with allow_dangerous=True"""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = execute_docker("run", image="ubuntu", allow_dangerous=True, privileged=True)
        data = json.loads(result)
        assert data["safety_check"] == "bypassed"
        # Command execution depends on actual Docker setup

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_timeout(self, mock_run, mock_check):
        """Test timeout functionality"""
        mock_check.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)

        result = execute_docker("build", timeout=5)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timed out" in data["message"]

    def test_docker_workspace_creation(self):
        """Test that workspace directory is created"""
        # Even when Docker is not available, workspace should be created
        result = execute_docker("ps")
        data = json.loads(result)
        # Just check that the function runs without error

        # Check workspace directory exists
        workspace_dir = Path("./workspace/docker")
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_build_command(self, mock_run, mock_check):
        """Test docker build command"""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully built abc123\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = execute_docker("build", tag="myapp:latest")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["operation"] == "build"

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_exec_command(self, mock_run, mock_check):
        """Test docker exec command"""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "executed\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = execute_docker("exec", container="mycontainer", command="echo hello")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["operation"] == "exec"

    @patch('tools.native.execute_docker._check_docker_available')
    @patch('subprocess.run')
    def test_docker_error_handling(self, mock_run, mock_check):
        """Test error handling for failed commands"""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "docker: Error response from daemon: No such container: nonexistent\n"
        mock_run.return_value = mock_result

        result = execute_docker("logs", container="nonexistent")
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["returncode"] == 1
        assert "No such container" in data["stderr"]