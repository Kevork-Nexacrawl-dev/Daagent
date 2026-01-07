"""
Query classification for latency optimization.
Provides lightweight pattern-based classification without LLM calls.
"""

import re
from enum import Enum
from typing import Optional


class QueryType(Enum):
    """Query classification types for optimization"""
    CACHED = "cached"          # FAQ-style queries (instant response)
    INFORMATIONAL = "informational"  # Explanatory queries (lite mode, no tools)
    ACTION = "action"          # Tool-requiring queries (full ReAct)
    COMPLEX = "complex"        # Complex reasoning (full ReAct, default)


class QueryClassifier:
    """
    Lightweight query classifier using regex patterns.
    Routes queries to optimal execution paths for speed optimization.
    """

    # Cached query patterns (FAQs, capabilities, etc.)
    CACHED_PATTERNS = [
        r"how many tools",
        r"what (can|do) you (have|do)",
        r"list (your )?capabilities",
        r"what are your (tools|abilities)",
        r"show me your tools",
        r"what (is|are) daagent",
        r"tell me about yourself",
        r"who are you",
        r"what can you help with",
        r"help me understand",
        r"explain (yourself|daagent)",
    ]

    # Informational patterns (explanations, definitions, no tools needed)
    INFORMATIONAL_PATTERNS = [
        r"what is",
        r"explain",
        r"tell me about",
        r"define",
        r"describe",
        r"how does",
        r"why (does|do)",
        r"when (is|are|do)",
        r"where (is|are)",
        r"who (is|are)",
    ]

    # Action patterns (require tools)
    ACTION_PATTERNS = [
        r"search",
        r"find",
        r"execute",
        r"run",
        r"read file",
        r"write file",
        r"edit file",
        r"analyze",
        r"check",
        r"test",
        r"install",
        r"download",
        r"upload",
        r"create",
        r"delete",
        r"move",
        r"copy",
        r"list",
        r"show me",
        r"get",
        r"fetch",
        r"query",
        r"calculate",
        r"compute",
        r"browse",
        r"navigate",
        r"click",
        r"apply",
        r"fill",
    ]

    @classmethod
    def classify(cls, query: str) -> QueryType:
        """
        Classify a query using pattern matching.

        Args:
            query: The user query to classify

        Returns:
            QueryType classification
        """
        query_lower = query.lower().strip()

        # Check cached patterns first (most specific)
        for pattern in cls.CACHED_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryType.CACHED

        # Check informational patterns
        for pattern in cls.INFORMATIONAL_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryType.INFORMATIONAL

        # Check action patterns
        for pattern in cls.ACTION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryType.ACTION

        # Default to complex for anything else
        return QueryType.COMPLEX

    @classmethod
    def should_use_tools(cls, query_type: QueryType) -> bool:
        """
        Determine if tools should be included based on query type.

        Args:
            query_type: The classified query type

        Returns:
            True if tools should be used
        """
        return query_type in [QueryType.ACTION, QueryType.COMPLEX]

    @classmethod
    def should_use_react_loop(cls, query_type: QueryType) -> bool:
        """
        Determine if full ReAct loop should be used.

        Args:
            query_type: The classified query type

        Returns:
            True if ReAct loop should be used
        """
        return query_type in [QueryType.ACTION, QueryType.COMPLEX]

    @classmethod
    def should_check_cache(cls, query_type: QueryType) -> bool:
        """
        Determine if cache should be checked.

        Args:
            query_type: The classified query type

        Returns:
            True if cache should be checked
        """
        return query_type == QueryType.CACHED

    @classmethod
    def get_execution_mode(cls, query_type: QueryType) -> str:
        """
        Get human-readable execution mode description.

        Args:
            query_type: The classified query type

        Returns:
            Description of execution mode
        """
        modes = {
            QueryType.CACHED: "cached (instant)",
            QueryType.INFORMATIONAL: "lite (single LLM call, no tools)",
            QueryType.ACTION: "full ReAct (with tools)",
            QueryType.COMPLEX: "full ReAct (with tools)",
        }
        return modes.get(query_type, "unknown")