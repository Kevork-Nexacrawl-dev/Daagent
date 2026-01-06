---
agent: "qa-tester"
tools: ["read", "search", "web/githubRepo"]
description: Generate comprehensive tests for a tool
---

# Tool Testing Template

**Tool Name:** {input:toolName|Which tool needs testing? (e.g., 'websearch', 'perplexity')}  
**Test File:** {input:testFile|Test file location (default: 'tests/test_{toolName}.py')}  
**Coverage Target:** {input:coverage|Target coverage % (default: 80)}

## Test Categories Required

### 1. Happy Path Tests
```python
def test_{toolName}_success():
    """Test normal usage with valid inputs."""
    result = execute("valid input")
    data = json.loads(result)
    assert data["status"] == "success"
    assert "results" in data
    assert data["count"] >= 0
```

### 2. Error Case Tests
```python
def test_{toolName}_empty_input():
    """Test with empty or invalid input."""
    result = execute("")
    data = json.loads(result)
    assert data["status"] == "error"
    assert "message" in data

def test_{toolName}_network_failure():
    """Test graceful degradation when network fails."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout()
        result = execute("test query")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "timeout" in data["message"].lower()
```

### 3. Edge Case Tests
```python
def test_{toolName}_large_input():
    """Test with unusually large input."""
    large_input = "x" * 10000
    result = execute(large_input)
    data = json.loads(result)
    # Should handle gracefully (truncate, reject, or process)
    assert data is not None

def test_{toolName}_special_characters():
    """Test with special characters and unicode."""
    special_input = "query with @#$%^&*() 特殊字符"
    result = execute(special_input)
    data = json.loads(result)
    assert "status" in data

def test_{toolName}_malformed_data():
    """Test with unexpected data formats."""
    # Test with None, dict, list inputs if applicable
    pass
```

## Mocking Strategy

### External API Calls
```python
from unittest.mock import patch, Mock

def test_{toolName}_with_mock():
    """Test using mocked external dependencies."""
    with patch('external_library.APIClient') as mock_client:
        mock_client.return_value.get.return_value = mock_response
        result = execute("test")
        assert "expected" in result
```

### File System Operations
```python
import pytest

@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file for testing."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    yield test_file

def test_{toolName}_file_operations(temp_file):
    result = execute(str(temp_file))
    assert "test content" in result
```

## Integration Tests
```python
@pytest.mark.integration
def test_{toolName}_real_api():
    """Test against real API (optional, CI only)."""
    result = execute("real world query")
    data = json.loads(result)
    assert data["status"] == "success"
    assert len(data.get("results", [])) > 0
```

## Coverage Goals

- **Unit Tests:** 80%+ coverage
- **Mock Usage:** All external dependencies mocked
- **Execution Time:** <1 second per test
- **Isolation:** Tests don't depend on each other

## Test File Structure

```python
# tests/test_{toolName}.py
import json
import pytest
from unittest.mock import patch, Mock
from tools.native.{toolName} import execute

# Happy path tests
def test_{toolName}_success():
    # Implementation

# Error case tests
def test_{toolName}_error_cases():
    # Implementation

# Edge case tests
def test_{toolName}_edge_cases():
    # Implementation

# Integration tests (optional)
@pytest.mark.integration
def test_{toolName}_integration():
    # Implementation
```

## Running Tests

```bash
# Run specific test file
pytest tests/test_{toolName}.py -v

# With coverage
pytest tests/test_{toolName}.py --cov=tools.native.{toolName} --cov-report=term-missing

# Run all tests
pytest tests/ --cov=agent --cov=tools --cov-report=html
```

## Success Criteria

- [ ] All 3 test categories implemented (happy/error/edge)
- [ ] Tests pass with `pytest tests/test_{toolName}.py`
- [ ] Coverage ≥ target % with mocked dependencies
- [ ] No real API calls in unit tests
- [ ] Tests run in <30 seconds total
- [ ] Test file follows naming conventions

---

**No tool ships without comprehensive tests. Quality is not optional.**
