"""
Tests for academic search tools.
"""

import pytest
import httpx
import json
from unittest.mock import patch
from tools.native.academic_search import (
    search_papers,
    get_paper_details,
    get_paper_citations,
    execute_tool
)


class TestSearchPapers:
    """Test search_papers function."""

    def test_search_papers_success(self, httpx_mock):
        """Test successful paper search."""
        mock_response = {
            "data": [
                {
                    "paperId": "123",
                    "title": "Test Paper",
                    "authors": [{"name": "Author One"}, {"name": "Author Two"}],
                    "year": 2023,
                    "abstract": "Test abstract",
                    "citationCount": 10,
                    "url": "https://example.com",
                    "venue": "Test Venue"
                }
            ]
        }
        httpx_mock.add_response(
            url="https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=10&fields=title%2Cauthors%2Cyear%2Cabstract%2CcitationCount%2Curl%2CpaperId%2Cvenue",
            json=mock_response
        )

        result = search_papers("test", limit=10)

        assert result["success"] is True
        assert len(result["papers"]) == 1
        assert result["papers"][0]["title"] == "Test Paper"
        assert result["papers"][0]["citations"] == 10

    def test_search_papers_with_year_filter(self, httpx_mock):
        """Test search with year filter."""
        mock_response = {"data": []}
        httpx_mock.add_response(
            url="https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=10&year=2020-2024&fields=title%2Cauthors%2Cyear%2Cabstract%2CcitationCount%2Curl%2CpaperId%2Cvenue",
            json=mock_response
        )

        result = search_papers("test", year_filter="2020-2024")

        assert result["success"] is True
        assert result["papers"] == []

    def test_search_papers_invalid_year_filter(self):
        """Test invalid year filter format."""
        result = search_papers("test", year_filter="invalid")

        assert result["success"] is False
        assert "Invalid year_filter format" in result["error"]

    def test_search_papers_min_citations_filter(self, httpx_mock):
        """Test filtering by minimum citations."""
        mock_response = {
            "data": [
                {
                    "paperId": "123",
                    "title": "High Citations",
                    "authors": [{"name": "Author"}],
                    "year": 2023,
                    "abstract": "Abstract",
                    "citationCount": 100,
                    "url": "https://example.com",
                    "venue": "Venue"
                },
                {
                    "paperId": "456",
                    "title": "Low Citations",
                    "authors": [{"name": "Author"}],
                    "year": 2023,
                    "abstract": "Abstract",
                    "citationCount": 5,
                    "url": "https://example.com",
                    "venue": "Venue"
                }
            ]
        }
        httpx_mock.add_response(json=mock_response)

        result = search_papers("test", min_citations=50)

        assert result["success"] is True
        assert len(result["papers"]) == 1
        assert result["papers"][0]["title"] == "High Citations"

    def test_search_papers_rate_limit(self, httpx_mock):
        """Test rate limit handling."""
        httpx_mock.add_response(status_code=429)

        result = search_papers("test")

        assert result["success"] is False
        assert "Rate limit exceeded" in result["error"]

    def test_search_papers_network_error(self, httpx_mock):
        """Test network error handling."""
        httpx_mock.add_exception(httpx.RequestError("Network error"))

        result = search_papers("test")

        assert result["success"] is False
        assert "Network error" in result["error"]


class TestGetPaperDetails:
    """Test get_paper_details function."""

    def test_get_paper_details_success(self, httpx_mock):
        """Test successful paper details retrieval."""
        mock_response = {
            "paperId": "123",
            "title": "Test Paper",
            "authors": [
                {"name": "Author One", "affiliations": ["University A"]},
                {"name": "Author Two", "affiliations": ["University B"]}
            ],
            "year": 2023,
            "abstract": "Test abstract",
            "citationCount": 10,
            "referenceCount": 20,
            "venue": "Test Venue",
            "fieldsOfStudy": ["Computer Science"],
            "tldr": {"text": "TLDR summary"},
            "url": "https://example.com",
            "openAccessPdf": {"url": "https://pdf.example.com"}
        }
        httpx_mock.add_response(json=mock_response)

        result = get_paper_details("123")

        assert result["success"] is True
        assert result["paper"]["title"] == "Test Paper"
        assert result["paper"]["tldr"] == "TLDR summary"
        assert result["paper"]["openAccessPdf"] == "https://pdf.example.com"

    def test_get_paper_details_not_found(self, httpx_mock):
        """Test paper not found."""
        httpx_mock.add_response(status_code=404)

        result = get_paper_details("invalid")

        assert result["success"] is False
        assert result["error"] == "Paper not found"


class TestGetPaperCitations:
    """Test get_paper_citations function."""

    def test_get_paper_citations_success(self, httpx_mock):
        """Test successful citations retrieval."""
        mock_response = {
            "data": [
                {
                    "citingPaper": {
                        "title": "Citing Paper",
                        "year": 2024,
                        "citationCount": 5,
                        "url": "https://citing.com"
                    }
                }
            ]
        }
        httpx_mock.add_response(json=mock_response)

        result = get_paper_citations("123", limit=10)

        assert result["success"] is True
        assert len(result["citing_papers"]) == 1
        assert result["citing_papers"][0]["title"] == "Citing Paper"


class TestExecuteTool:
    """Test execute_tool function."""

    def test_execute_search_papers(self):
        """Test executing search_papers tool."""
        with patch('tools.native.academic_search.search_papers') as mock_search:
            mock_search.return_value = {"success": True, "papers": []}

            result = execute_tool("search_papers", {"query": "test"})
            parsed = json.loads(result)

            assert parsed["success"] is True

    def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        result = execute_tool("unknown", {})
        parsed = json.loads(result)

        assert parsed["success"] is False
        assert "Unknown tool" in parsed["error"]


@pytest.mark.integration
def test_real_api_search():
    """Integration test with real API (requires internet)."""
    result = search_papers("transformers in NLP", limit=5)

    # This will fail if API is down or rate limited, but tests real integration
    if result["success"]:
        assert len(result["papers"]) <= 5
        for paper in result["papers"]:
            assert "title" in paper
            assert "authors" in paper
    else:
        # If rate limited or error, just check it's a proper error response
        assert "error" in result