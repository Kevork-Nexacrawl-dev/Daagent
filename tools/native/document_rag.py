"""
Document RAG Tools for Daagent
Allows agent to upload, search, and manage documents
"""

import json
from pathlib import Path
from typing import Dict, Any
from agent.rag_engine import RAGEngine

# Initialize RAG engine
rag_engine = RAGEngine(
    qdrant_url="http://localhost:6333",
    collection_name="daagent_docs"
)


def upload_document(file_path: str, title: str = None,
                   author: str = None, tags: list = None) -> dict:
    """
    Upload and ingest a document into RAG system.

    Args:
        file_path: Path to document (PDF, TXT, MD, DOCX, code files)
        title: Optional document title
        author: Optional author name
        tags: Optional tags for categorization

    Returns:
        {
            "success": bool,
            "doc_id": str,
            "filename": str,
            "num_chunks": int,
            "message": str
        }
    """
    try:
        metadata = {}
        if title:
            metadata["title"] = title
        if author:
            metadata["author"] = author
        if tags:
            metadata["tags"] = tags

        doc_id = rag_engine.ingest_document(file_path, metadata)

        # Get chunk count from metadata
        docs = rag_engine.list_documents()
        doc_info = next((d for d in docs if d["doc_id"] == doc_id), None)

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": Path(file_path).name,
            "num_chunks": doc_info["num_chunks"] if doc_info else 0,
            "message": f"✓ Uploaded {Path(file_path).name} (ID: {doc_id[:8]}...)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}"
        }


def search_documents(query: str, top_k: int = 5, doc_id: str = None) -> dict:
    """
    Semantic search across uploaded documents.

    Args:
        query: Search query
        top_k: Number of results (default 5, max 20)
        doc_id: Optional document ID to search within

    Returns:
        {
            "success": bool,
            "results": [
                {
                    "text": str,  # Chunk text
                    "filename": str,
                    "chunk_index": int,
                    "score": float,
                    "citation": str  # Format: [filename:chunkN]
                }
            ],
            "count": int
        }
    """
    try:
        results = rag_engine.search_documents(query, min(top_k, 20), doc_id)

        formatted_results = []
        for r in results:
            formatted_results.append({
                "text": r["text"],
                "filename": r["filename"],
                "chunk_index": r["chunk_index"],
                "score": round(r["score"], 3),
                "citation": f"[{r['filename']}:chunk{r['chunk_index']}]"
            })

        return {
            "success": True,
            "results": formatted_results,
            "count": len(formatted_results)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}"
        }


def list_documents() -> dict:
    """
    List all uploaded documents in RAG system.

    Returns:
        {
            "success": bool,
            "documents": [
                {
                    "doc_id": str,
                    "filename": str,
                    "num_chunks": int,
                    "uploaded_at": str,
                    "metadata": dict
                }
            ],
            "count": int
        }
    """
    try:
        docs = rag_engine.list_documents()

        return {
            "success": True,
            "documents": docs,
            "count": len(docs)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}"
        }


def delete_document(doc_id: str) -> dict:
    """
    Delete a document from RAG system.

    Args:
        doc_id: Document ID to delete

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        success = rag_engine.delete_document(doc_id)

        if success:
            return {
                "success": True,
                "message": f"✓ Deleted document {doc_id[:8]}..."
            }
        else:
            return {
                "success": False,
                "error": f"Document {doc_id} not found"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}"
        }


# Tool registration schema
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "upload_document",
            "description": "Upload a document (PDF, TXT, MD, DOCX, code) into the knowledge base for semantic search",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to document file"},
                    "title": {"type": "string", "description": "Optional document title"},
                    "author": {"type": "string", "description": "Optional author name"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search within uploaded documents using semantic similarity. Returns relevant chunks with citations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "default": 5, "maximum": 20, "description": "Number of results"},
                    "doc_id": {"type": "string", "description": "Optional document ID to search within"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "List all documents in the knowledge base",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_document",
            "description": "Delete a document from the knowledge base",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string", "description": "Document ID to delete"}
                },
                "required": ["doc_id"]
            }
        }
    }
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute RAG tool by name."""
    if name == "upload_document":
        return json.dumps(upload_document(**arguments))
    elif name == "search_documents":
        return json.dumps(search_documents(**arguments))
    elif name == "list_documents":
        return json.dumps(list_documents())
    elif name == "delete_document":
        return json.dumps(delete_document(**arguments))
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})