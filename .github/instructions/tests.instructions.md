---
applyTo: "tests/**/*.py"
description: Testing standards and patterns for Daagent
---

## Test File Standards

### Naming Conventions
- ✅ `test_{module}.py` (matches module being tested)
- ✅ `test_{module}_{scenario}` (descriptive test names)
- ❌ `test1.py`, `mytest.py` (meaningless names)

### Required Test Categories

Every module must have:

1. **Happy Path Tests**
```python
def test_{module}_success():
    """Test normal usage with valid inputs."""
    result = execute("valid input")
    assert result is not None
    assert "expected" in result
```

2. **Error Case Tests**
```python
def test_{module}_invalid_input():
    """Test with invalid input."""
    result = execute(None)
    assert "error" in result.lower()

def test_{module}_network_failure():
    """Test graceful degradation."""
    with patch('requests.get') as mock:
        mock.side_effect = requests.Timeout()
        result = execute("query")
        assert "timeout" in result.lower()
```

3. **Edge Case Tests**
```python
def test_{module}_large_input():
    """Test with unusually large input."""
    large_input = "x" * 10000
    result = execute(large_input)
    assert result is not None

def test_{module}_special_characters():
    """Test with special characters."""
    result = execute("query with @#$%")
    assert "status" in result
```


### Mocking External Dependencies

```python
from unittest.mock import patch, Mock

# ✅ GOOD - Mock external API
def test_websearch_with_mock():
    with patch('duckduckgo_search.DDGS') as mock_ddgs:
        mock_ddgs.return_value.text.return_value = [
            {'title': 'Test', 'href': 'http://test.com'}
        ]
        result = websearch.execute("test")
        assert "Test" in result

# ❌ BAD - Hits real API (slow, flaky, costs money)
def test_websearch_real():
    result = websearch.execute("test")
    assert result is not None
```


### Fixtures for Setup/Teardown

```python
import pytest

@pytest.fixture
def temp_config(tmp_path):
    """Create temporary config file."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}')
    yield config_file
    # Cleanup automatic

def test_config_loading(temp_config):
    config = load_config(temp_config)
    assert config['key'] == 'value'
```


### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_tool():
    result = await async_execute("query")
    assert result is not None
```


### Integration Tests (Mark as Optional)

```python
@pytest.mark.integration
@pytest.mark.skip(reason="Requires real API key")
def test_real_api_call():
    """Test against real API (CI only)."""
    result = execute("real query")
    assert len(result) > 0
```


### Coverage Goals

- **Minimum:** 80% line coverage
- **Target:** 90%+ for core modules
- **Command:** `pytest --cov=agent --cov-report=html`


### Boundaries

#### ✅ Always Do

- Test all three categories (happy/error/edge)
- Use mocks for external APIs
- Add docstrings to test functions
- Keep tests fast (<1s per test)


#### ⚠️ Ask First

- Skipping tests for edge cases
- Adding integration tests that require paid APIs
- Changing test structure/patterns


#### 🚫 Never Do

- Hit real APIs in unit tests
- Leave failing tests commented out
- Use `assert True` (meaningless assertion)
- Skip error case tests
