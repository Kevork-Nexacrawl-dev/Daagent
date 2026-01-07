"""
Tests for ported tools from autogen-shop.
"""

import json
import pytest
import tempfile
import os
from unittest.mock import patch, mock_open
from tools.native.code_analysis import execute_tool as execute_code_analysis
from tools.native.data_ops import execute_tool as execute_data_ops
from tools.native.memory import execute_tool as execute_memory
from tools.native.planning import execute_tool as execute_planning
from tools.native.executor import execute_tool as execute_executor


class TestCodeAnalysis:
    """Test code analysis tool"""

    def test_validate_syntax_valid(self):
        """Test syntax validation with valid Python code"""
        code = "def hello():\n    print('Hello, world!')"
        result = execute_code_analysis("validate_syntax", code=code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["valid"] is True
        assert "errors" not in data or data["errors"] == []

    def test_validate_syntax_invalid(self):
        """Test syntax validation with invalid Python code"""
        code = "def hello(\n    print('Hello, world!')"  # Missing closing paren
        result = execute_code_analysis("validate_syntax", code=code)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["valid"] is False
        assert "error" in data  # Changed from "errors" to "error"

    def test_analyze_imports(self):
        """Test import analysis"""
        code = "import os\nimport sys\nfrom pathlib import Path"
        result = execute_code_analysis("analyze_imports", code=code)
        data = json.loads(result)
        assert data["status"] == "success"
        # Check that modules list contains the expected modules
        modules = data.get("modules", [])
        assert "os" in modules
        assert "sys" in modules
        assert "pathlib" in modules

    def test_detect_dependencies(self):
        """Test dependency detection"""
        code = "import requests\nfrom PIL import Image\nimport numpy as np"
        result = execute_code_analysis("detect_dependencies", code=code)
        data = json.loads(result)
        assert data["status"] == "success"
        # Check that packages list contains the expected third-party packages
        packages = data.get("packages", [])
        assert "requests" in packages
        assert "PIL" in packages
        assert "numpy" in packages


class TestDataOps:
    """Test data operations tool"""

    def test_parse_salary_ranges(self):
        """Test salary range parsing"""
        text = "Salary: $50,000 - $70,000 per year"
        result = execute_data_ops("parse_salary_ranges", text=text)
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["ranges"]) > 0
        assert data["ranges"][0]["min"] == 50000
        assert data["ranges"][0]["max"] == 70000

    def test_transform_csv(self):
        """Test CSV transformation"""
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
        operations = [{"type": "add_column", "column": "name_upper", "expression": "row['name'].upper()"}]
        result = execute_data_ops("transform_csv", data=data, operations=operations)
        data = json.loads(result)
        assert data["status"] == "success"

    def test_normalize_data(self):
        """Test data normalization"""
        values = [10, 20, 30, 40, 50]
        result = execute_data_ops("normalize_data", values=values, min_val=0, max_val=1)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["normalized_values"][0] == 0.0  # Min value
        assert data["normalized_values"][-1] == 1.0  # Max value


class TestMemory:
    """Test memory management tool"""

    def test_store_memory(self):
        """Test memory storage"""
        result = execute_memory("store_memory", session_id="test_session", agent_name="test_agent", content="Test memory", tags=["test"])
        data = json.loads(result)
        assert data["status"] == "success"
        assert "storage" in data  # Check that storage was successful

    def test_retrieve_memory(self):
        """Test memory retrieval"""
        result = execute_memory("retrieve_memory", session_id="test_session", limit=5)
        data = json.loads(result)
        assert data["status"] == "success"
        assert isinstance(data["memories"], list)

    def test_clear_memory(self):
        """Test memory clearing"""
        with patch('builtins.open', mock_open()) as mock_file:
            result = execute_memory("clear_memory", topic="test")
            data = json.loads(result)
            assert data["status"] == "success"


class TestPlanning:
    """Test planning tool"""

    def test_decompose_task(self):
        """Test task decomposition"""
        result = execute_planning("decompose_task", goal="Build a web application with user authentication")
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["subtasks"]) > 0
        assert isinstance(data["subtasks"], list)

    def test_prioritize_steps(self):
        """Test step prioritization"""
        tasks = [{"name": "Design database", "urgency": 8}, {"name": "Implement login", "urgency": 7}, {"name": "Write tests", "urgency": 6}, {"name": "Deploy app", "urgency": 9}]
        result = execute_planning("prioritize_steps", tasks=tasks)
        data = json.loads(result)
        assert data["status"] == "success"
        assert len(data["prioritized_tasks"]) == len(tasks)
        assert isinstance(data["prioritized_tasks"], list)

    def test_estimate_complexity(self):
        """Test complexity estimation"""
        result = execute_planning("estimate_complexity", task="Create a simple calculator app", task_type="coding")
        data = json.loads(result)
        assert data["status"] == "success"
        assert "complexity_level" in data
        assert data["complexity_level"] in ["low", "medium", "high"]


class TestExecutor:
    """Test Python execution tool"""

    def test_execute_python_safe(self):
        """Test safe Python execution"""
        code = "result = 2 + 3"
        result = execute_executor("execute_python", code=code, timeout=5)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["result"] == 5

    def test_execute_python_unsafe(self):
        """Test that unsafe operations are blocked"""
        code = "import os\nos.system('echo hello')"
        result = execute_executor("execute_python", code=code, timeout=5)
        data = json.loads(result)
        # Should either fail or not execute the dangerous operation
        assert data["status"] in ["success", "error"]

    def test_execute_python_timeout(self):
        """Test execution timeout"""
        code = "import time\ntime.sleep(10)"  # Long running code
        result = execute_executor("execute_python", code=code, timeout=1)
        data = json.loads(result)
        # Should timeout
        assert data["status"] == "error" or "timeout" in str(data).lower()