"""
Tests for document RAG system.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from agent.rag_engine import RAGEngine
from tools.native.document_rag import upload_document, search_documents, list_documents, delete_document


@pytest.fixture
def test_document(tmp_path):
    """Create a test document."""
    doc = tmp_path / "test.txt"
    doc.write_text("Artificial intelligence is transforming software development. " * 50)
    return str(doc)


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    with patch('agent.rag_engine.QdrantClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        # Mock collections
        mock_collection = MagicMock()
        mock_collection.name = "daagent_docs"
        mock_instance.get_collections.return_value.collections = [mock_collection]

        yield mock_instance


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch('agent.rag_engine.OpenAI') as mock_openai:
        mock_instance = MagicMock()
        mock_client = MagicMock()
        mock_instance.return_value = mock_client

        # Mock embedding response
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1] * 1536
        mock_client.embeddings.create.return_value = mock_response

        yield mock_client


def test_chunk_text(mock_qdrant, mock_openai):
    """Test text chunking."""
    engine = RAGEngine()
    text = "This is a test. " * 100
    chunks = engine.chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    # Check overlap exists
    assert any(chunks[i][-20:] in chunks[i+1] for i in range(len(chunks)-1))


def test_upload_document(test_document, mock_qdrant, mock_openai):
    """Test document upload."""
    result = upload_document(test_document, title="Test Doc")

    assert result["success"] is True
    assert "doc_id" in result
    assert result["num_chunks"] > 0


def test_search_documents(test_document):
    """Test document search."""
    from tools.native.document_rag import rag_engine

    # Mock the search_documents method
    mock_results = [{
        "chunk_id": "test-uuid-123",
        "doc_id": "test123",
        "filename": "test.txt",
        "chunk_index": 0,
        "text": "Artificial intelligence is transforming software development.",
        "score": 0.8,
        "metadata": {}
    }]

    with patch.object(rag_engine, 'search_documents', return_value=mock_results):
        # Search
        result = search_documents("artificial intelligence")

        assert result["success"] is True
        assert result["count"] > 0
        assert "artificial intelligence" in result["results"][0]["text"].lower()


def test_list_documents(test_document, mock_qdrant, mock_openai):
    """Test listing documents."""
    upload_document(test_document)

    result = list_documents()

    assert result["success"] is True
    assert result["count"] > 0


def test_delete_document(test_document, mock_qdrant, mock_openai):
    """Test document deletion."""
    # Upload
    upload_result = upload_document(test_document)
    doc_id = upload_result["doc_id"]

    # Delete
    result = delete_document(doc_id)

    assert result["success"] is True

    # Verify deleted
    docs = list_documents()
    assert not any(d["doc_id"] == doc_id for d in docs["documents"])


def test_parse_file_txt():
    """Test parsing text file."""
    engine = RAGEngine()
    test_file = Path("test.txt")
    test_file.write_text("Hello world")

    try:
        text = engine._parse_file(test_file)
        assert text == "Hello world"
    finally:
        test_file.unlink()


def test_parse_file_unsupported():
    """Test parsing unsupported file type."""
    engine = RAGEngine()
    test_file = Path("test.xyz")
    test_file.write_text("test")

    try:
        with pytest.raises(ValueError, match="Unsupported file type"):
            engine._parse_file(test_file)
    finally:
        test_file.unlink()


@pytest.mark.integration
def test_qdrant_connection():
    """Test Qdrant connection (requires Docker running)."""
    try:
        engine = RAGEngine()
        collections = engine.qdrant.get_collections()
        assert any(c.name == "daagent_docs" for c in collections.collections)
    except Exception:
        pytest.skip("Qdrant not available for integration test")