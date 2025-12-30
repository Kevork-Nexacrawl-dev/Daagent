"""
Web search tool using DuckDuckGo (free, no API key required).
"""

from typing import Dict, Any
import logging
import json
from ddgs import DDGS

logger = logging.getLogger(__name__)


def execute_search(query: str, max_results: int = 5) -> str:
    """
    Search web using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        JSON string with search results

    Raises:
        SearchError: If search fails
    """
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        formatted = [{
            "title": r["title"],
            "url": r["href"],
            "snippet": r["body"]
        } for r in results]
        return json.dumps({
            "status": "success",
            "query": query,
            "results": formatted,
            "count": len(formatted)
        })
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        return json.dumps({
            "status": "error",
            "message": f"Search failed: {str(e)}"
        })


# OpenAI function calling schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

# Alias for auto-discovery compatibility
execute_tool = execute_search