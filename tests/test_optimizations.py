"""
Tests for latency optimization system.
"""

import pytest
from agent.query_classifier import QueryClassifier, QueryType
from agent.response_cache import ResponseCache


def test_query_classifier_cached():
    """Test cached query classification"""
    qc = QueryClassifier()

    # Test cached queries
    assert qc.classify("How many tools do you have?") == QueryType.CACHED
    assert qc.classify("What can you do?") == QueryType.CACHED
    assert qc.classify("List your capabilities") == QueryType.CACHED

    # Test that cached queries should check cache
    assert qc.should_check_cache(QueryType.CACHED) == True
    assert qc.should_check_cache(QueryType.INFORMATIONAL) == False


def test_query_classifier_informational():
    """Test informational query classification"""
    qc = QueryClassifier()

    # Test informational queries
    assert qc.classify("What is Python?") == QueryType.INFORMATIONAL
    assert qc.classify("Explain machine learning") == QueryType.INFORMATIONAL
    assert qc.classify("Tell me about AI") == QueryType.INFORMATIONAL

    # Test that informational queries don't use tools
    assert qc.should_use_tools(QueryType.INFORMATIONAL) == False
    assert qc.should_use_react_loop(QueryType.INFORMATIONAL) == False


def test_query_classifier_action():
    """Test action query classification"""
    qc = QueryClassifier()

    # Test action queries
    assert qc.classify("Search for AI news") == QueryType.ACTION
    assert qc.classify("Execute python code") == QueryType.ACTION
    assert qc.classify("Read file test.txt") == QueryType.ACTION

    # Test that action queries use tools and ReAct
    assert qc.should_use_tools(QueryType.ACTION) == True
    assert qc.should_use_react_loop(QueryType.ACTION) == True


def test_query_classifier_complex():
    """Test complex query classification (default)"""
    qc = QueryClassifier()

    # Test complex queries (default fallback)
    assert qc.classify("Build a web application") == QueryType.COMPLEX
    assert qc.classify("Analyze this dataset and create a report") == QueryType.COMPLEX

    # Test that complex queries use tools and ReAct
    assert qc.should_use_tools(QueryType.COMPLEX) == True
    assert qc.should_use_react_loop(QueryType.COMPLEX) == True


def test_response_cache():
    """Test response cache functionality"""
    cache = ResponseCache(ttl_hours=1)  # Short TTL for testing

    # Test cache put and get
    cache.put("test query", "test response")
    assert cache.get("test query") == "test response"

    # Test cache miss
    assert cache.get("nonexistent query") is None

    # Test stats
    stats = cache.get_stats()
    assert stats['total_entries'] == 1
    assert stats['total_hits'] == 2  # One put, one get

    # Test clear
    cache.clear()
    assert cache.get("test query") is None
    assert cache.get_stats()['total_entries'] == 0


def test_response_cache_expiration():
    """Test cache entry expiration"""
    import time
    from datetime import timedelta

    # Create cache with very short TTL
    cache = ResponseCache(ttl_hours=0.0001)  # ~3.6 seconds

    cache.put("test", "response")
    assert cache.get("test") == "response"

    # Wait for expiration
    time.sleep(4)

    # Should be expired now
    assert cache.get("test") is None