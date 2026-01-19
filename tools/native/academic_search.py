"""
Academic research tools using Semantic Scholar API.

Provides functions to search academic papers, get paper details, and retrieve citations.
"""

import json
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Semantic Scholar API base URL
API_BASE = "https://api.semanticscholar.org/graph/v1"

# Rate limit: 100 requests per 5 minutes
# We'll handle this by logging and returning error if hit

def search_papers(query: str, limit: int = 10, year_filter: str = None,
                  min_citations: int = 0) -> Dict[str, Any]:
    """
    Search academic papers across all fields.

    Args:
        query: Search query (e.g., "transformers in NLP")
        limit: Max results (default 10, max 100)
        year_filter: Optional year range "2020-2024"
        min_citations: Minimum citation count filter

    Returns:
        {
            "success": bool,
            "papers": [
                {
                    "title": str,
                    "authors": [str],
                    "year": int,
                    "abstract": str,
                    "citations": int,
                    "url": str,
                    "paperId": str,
                    "venue": str
                }
            ],
            "count": int
        }
    """
    try:
        params = {
            "query": query,
            "limit": min(limit, 100),  # API max is 100
            "fields": "title,authors,year,abstract,citationCount,url,paperId,venue"
        }

        if year_filter:
            # Parse year range like "2020-2024"
            try:
                start_year, end_year = map(int, year_filter.split('-'))
                params["year"] = f"{start_year}-{end_year}"
            except ValueError:
                logger.warning(f"Invalid year_filter format: {year_filter}. Expected 'YYYY-YYYY'")
                return {"success": False, "error": "Invalid year_filter format. Use 'YYYY-YYYY'"}

        url = f"{API_BASE}/paper/search"

        logger.info(f"Searching papers: query='{query}', limit={limit}, year={year_filter}")

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            papers = []
            for paper in data.get("data", []):
                citations = paper.get("citationCount", 0)
                if citations >= min_citations:
                    papers.append({
                        "title": paper.get("title", ""),
                        "authors": [author.get("name", "") for author in paper.get("authors", [])],
                        "year": paper.get("year"),
                        "abstract": paper.get("abstract", ""),
                        "citations": citations,
                        "url": paper.get("url", ""),
                        "paperId": paper.get("paperId", ""),
                        "venue": paper.get("venue", "")
                    })

            return {
                "success": True,
                "papers": papers[:limit],  # Ensure we don't exceed requested limit
                "count": len(papers)
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.error("Rate limit exceeded for Semantic Scholar API")
            return {"success": False, "error": "Rate limit exceeded. Try again in 5 minutes."}
        logger.error(f"API error: {e.response.status_code} - {e.response.text}")
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        return {"success": False, "error": "Network error. Check connection."}
    except Exception as e:
        logger.error(f"Unexpected error in search_papers: {e}")
        return {"success": False, "error": str(e)}


def get_paper_details(paper_id: str) -> Dict[str, Any]:
    """
    Get full details for a specific paper.

    Args:
        paper_id: Semantic Scholar paper ID or DOI

    Returns:
        {
            "success": bool,
            "paper": {
                "title": str,
                "authors": [{"name": str, "affiliations": [str]}],
                "year": int,
                "abstract": str,
                "citations": int,
                "references": int,
                "venue": str,
                "fieldsOfStudy": [str],
                "tldr": str,  # AI-generated summary if available
                "url": str,
                "openAccessPdf": str  # URL to free PDF if available
            }
        }
    """
    try:
        url = f"{API_BASE}/paper/{paper_id}"
        params = {
            "fields": "title,authors,year,abstract,citationCount,referenceCount,venue,fieldsOfStudy,tldr,url,openAccessPdf"
        }

        logger.info(f"Getting paper details: {paper_id}")

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

            paper = response.json()

            return {
                "success": True,
                "paper": {
                    "title": paper.get("title", ""),
                    "authors": [
                        {
                            "name": author.get("name", ""),
                            "affiliations": author.get("affiliations", [])
                        }
                        for author in paper.get("authors", [])
                    ],
                    "year": paper.get("year"),
                    "abstract": paper.get("abstract", ""),
                    "citations": paper.get("citationCount", 0),
                    "references": paper.get("referenceCount", 0),
                    "venue": paper.get("venue", ""),
                    "fieldsOfStudy": paper.get("fieldsOfStudy", []),
                    "tldr": paper.get("tldr", {}).get("text", "") if paper.get("tldr") else "",
                    "url": paper.get("url", ""),
                    "openAccessPdf": paper.get("openAccessPdf", {}).get("url", "") if paper.get("openAccessPdf") else ""
                }
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "error": "Paper not found"}
        if e.response.status_code == 429:
            logger.error("Rate limit exceeded for Semantic Scholar API")
            return {"success": False, "error": "Rate limit exceeded. Try again in 5 minutes."}
        logger.error(f"API error: {e.response.status_code} - {e.response.text}")
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        return {"success": False, "error": "Network error. Check connection."}
    except Exception as e:
        logger.error(f"Unexpected error in get_paper_details: {e}")
        return {"success": False, "error": str(e)}


def get_paper_citations(paper_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get papers that cite this paper.

    Args:
        paper_id: Semantic Scholar paper ID
        limit: Max citations to return

    Returns:
        {
            "success": bool,
            "citing_papers": [
                {
                    "title": str,
                    "year": int,
                    "citations": int,
                    "url": str
                }
            ]
        }
    """
    try:
        url = f"{API_BASE}/paper/{paper_id}/citations"
        params = {
            "limit": min(limit, 100),  # API max is 1000, but we'll limit to 100
            "fields": "citingPaper.title,citingPaper.year,citingPaper.citationCount,citingPaper.url"
        }

        logger.info(f"Getting citations for paper: {paper_id}, limit={limit}")

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            citing_papers = []
            for citation in data.get("data", []):
                citing = citation.get("citingPaper", {})
                citing_papers.append({
                    "title": citing.get("title", ""),
                    "year": citing.get("year"),
                    "citations": citing.get("citationCount", 0),
                    "url": citing.get("url", "")
                })

            return {
                "success": True,
                "citing_papers": citing_papers[:limit]
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "error": "Paper not found"}
        if e.response.status_code == 429:
            logger.error("Rate limit exceeded for Semantic Scholar API")
            return {"success": False, "error": "Rate limit exceeded. Try again in 5 minutes."}
        logger.error(f"API error: {e.response.status_code} - {e.response.text}")
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Network error: {e}")
        return {"success": False, "error": "Network error. Check connection."}
    except Exception as e:
        logger.error(f"Unexpected error in get_paper_citations: {e}")
        return {"success": False, "error": str(e)}


# Tool schema for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_papers",
            "description": "Search academic papers across all fields using Semantic Scholar",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10, "maximum": 100},
                    "year_filter": {"type": "string", "description": "Year range like '2020-2024'"},
                    "min_citations": {"type": "integer", "default": 0}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper_details",
            "description": "Get full details for a specific academic paper",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Semantic Scholar paper ID or DOI"}
                },
                "required": ["paper_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper_citations",
            "description": "Get papers that cite a specific academic paper",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Semantic Scholar paper ID"},
                    "limit": {"type": "integer", "default": 10, "maximum": 100}
                },
                "required": ["paper_id"]
            }
        }
    }
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute academic search tool by name.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        JSON string result
    """
    try:
        if name == "search_papers":
            return json.dumps(search_papers(**arguments))
        elif name == "get_paper_details":
            return json.dumps(get_paper_details(**arguments))
        elif name == "get_paper_citations":
            return json.dumps(get_paper_citations(**arguments))
        else:
            return json.dumps({"success": False, "error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return json.dumps({"success": False, "error": str(e)})