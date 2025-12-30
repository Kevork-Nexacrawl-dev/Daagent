"""
Tests for web_search tool.
"""

import json
import pytest
from unittest.mock import patch
from tools.native.web_search import execute_search


def test_search_success():
    """Test successful web search"""
    # Mock the search to return fake results
    fake_results = [
        {"title": "Python Programming", "href": "https://python.org", "body": "Learn Python"},
        {"title": "Python Tutorial", "href": "https://tutorial.python.org", "body": "Python basics"}
    ]
    with patch('tools.native.web_search.DDGS') as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.text.return_value = fake_results
        result = execute_search("Python programming", max_results=3)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["query"] == "Python programming"
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 2
        assert data["results"][0]["title"] == "Python Programming"
        assert data["results"][0]["url"] == "https://python.org"
        assert data["results"][0]["snippet"] == "Learn Python"


def test_search_error_handling():
    """Test error handling when search fails"""
    with patch('tools.native.web_search.DDGS') as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.text.side_effect = Exception("Network error")
        result = execute_search("test query")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Network error" in data["message"]


def test_search_no_results():
    """Test search with no results"""
    with patch('tools.native.web_search.DDGS') as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.text.return_value = []
        result = execute_search("nonexistent query")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["count"] == 0
        assert data["results"] == []