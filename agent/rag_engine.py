"""
RAG Engine for Daagent
Handles document chunking, embedding, storage, and retrieval
"""

import json
import hashlib
import tiktoken
from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    """Document ingestion and retrieval engine."""

    def __init__(self, qdrant_url: str = "http://localhost:6333",
                 collection_name: str = "daagent_docs",
                 embedding_model: str = "text-embedding-3-small"):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Metadata storage (track uploaded docs)
        self.metadata_file = Path("storage/rag_metadata.json")
        self.metadata_file.parent.mkdir(exist_ok=True)

        # Lazy initialization
        self._qdrant = None
        self._openai = None

    @property
    def qdrant(self):
        if self._qdrant is None:
            self._qdrant = QdrantClient(url=self.qdrant_url)
            self._init_collection()
        return self._qdrant

    @property
    def openai(self):
        if self._openai is None:
            self._openai = OpenAI()
        return self._openai

    def _init_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            collections = self._qdrant.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                self._qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-small dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Could not initialize Qdrant collection: {e}. Operations will fail until Qdrant is available.")

    def chunk_text(self, text: str, chunk_size: int = 512,
                   overlap: int = 100) -> List[str]:
        """
        Chunk text with token-based sliding window.

        Args:
            text: Input text
            chunk_size: Max tokens per chunk
            overlap: Overlapping tokens between chunks

        Returns:
            List of text chunks
        """
        tokens = self.tokenizer.encode(text)
        chunks = []

        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)

            if i + chunk_size >= len(tokens):
                break

        return chunks

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        response = self.openai.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def ingest_document(self, file_path: str, metadata: Dict[str, Any] = None) -> str:
        """
        Ingest a document: parse → chunk → embed → store.

        Args:
            file_path: Path to document (PDF, TXT, MD, etc.)
            metadata: Optional metadata (author, title, etc.)

        Returns:
            document_id (hash of file path)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate document ID
        doc_id = hashlib.sha256(str(file_path.absolute()).encode()).hexdigest()[:16]

        # Parse document
        text = self._parse_file(file_path)

        # Chunk text
        chunks = self.chunk_text(text)
        logger.info(f"Split {file_path.name} into {len(chunks)} chunks")

        # Embed and store chunks
        try:
            points = []
            for idx, chunk in enumerate(chunks):
                embedding = self.embed_text(chunk)

                # Generate UUID for point ID
                import uuid
                point_id = str(uuid.uuid4())

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "doc_id": doc_id,
                        "chunk_index": idx,
                        "text": chunk,
                        "filename": file_path.name,
                        "filepath": str(file_path.absolute()),
                        "metadata": metadata or {}
                    }
                )
                points.append(point)

            # Batch upload to Qdrant
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            logger.error(f"Failed to store document in Qdrant: {e}")
            raise

        # Save metadata
        self._save_document_metadata(doc_id, file_path, len(chunks), metadata)

        return doc_id

    def search_documents(self, query: str, top_k: int = 5,
                        doc_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Semantic search across ingested documents.

        Args:
            query: Search query
            top_k: Number of results to return
            doc_filter: Optional document ID to search within

        Returns:
            List of chunks with metadata and scores
        """
        try:
            # Embed query
            query_embedding = self.embed_text(query)

            # Search in Qdrant
            search_filter = None
            if doc_filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_filter = Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_filter))]
                )

            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k * 2,  # Fetch extra for hybrid search
                query_filter=search_filter
            )

            # Hybrid search: BM25 reranking
            if results:
                chunks = [r.payload["text"] for r in results]
                bm25 = BM25Okapi([chunk.split() for chunk in chunks])
                bm25_scores = bm25.get_scores(query.split())

                # Combine vector + BM25 scores (weighted average)
                combined_results = []
                max_bm25 = max(bm25_scores + [1])  # Avoid division by zero
                for idx, result in enumerate(results):
                    vector_score = result.score
                    bm25_score = bm25_scores[idx] if bm25_scores else 0
                    combined_score = 0.7 * vector_score + 0.3 * (bm25_score / max_bm25)

                    combined_results.append({
                "chunk_id": result.id,  # This is now the UUID
                        "filename": result.payload["filename"],
                        "chunk_index": result.payload["chunk_index"],
                        "text": result.payload["text"],
                        "score": combined_score,
                        "metadata": result.payload.get("metadata", {})
                    })

                # Sort by combined score and return top_k
                combined_results.sort(key=lambda x: x["score"], reverse=True)
                return combined_results[:top_k]
            else:
                return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all ingested documents."""
        if not self.metadata_file.exists():
            return []

        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)

        return list(metadata.values())

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its chunks."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Delete from Qdrant
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                )
            )
        except Exception as e:
            logger.error(f"Failed to delete from Qdrant: {e}")
            return False

        # Delete from metadata
        metadata = self._load_metadata()
        if doc_id in metadata:
            del metadata[doc_id]
            self._save_metadata(metadata)
            return True

        return False

    def _parse_file(self, file_path: Path) -> str:
        """Parse file content based on extension."""
        ext = file_path.suffix.lower()

        if ext == ".txt" or ext == ".md":
            return file_path.read_text(encoding='utf-8')

        elif ext == ".pdf":
            import pymupdf  # PyMuPDF
            doc = pymupdf.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text

        elif ext == ".docx":
            from docx import Document
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])

        elif ext in [".py", ".js", ".ts", ".java", ".cpp", ".c"]:
            # Code files
            return file_path.read_text(encoding='utf-8')

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _save_document_metadata(self, doc_id: str, file_path: Path,
                               num_chunks: int, metadata: Optional[Dict]):
        """Save document metadata to JSON file."""
        all_metadata = self._load_metadata()

        all_metadata[doc_id] = {
            "doc_id": doc_id,
            "filename": file_path.name,
            "filepath": str(file_path.absolute()),
            "num_chunks": num_chunks,
            "uploaded_at": str(Path(file_path).stat().st_mtime),
            "metadata": metadata or {}
        }

        self._save_metadata(all_metadata)

    def _load_metadata(self) -> Dict:
        """Load metadata from JSON file."""
        if not self.metadata_file.exists():
            return {}

        with open(self.metadata_file, 'r') as f:
            return json.load(f)

    def _save_metadata(self, metadata: Dict):
        """Save metadata to JSON file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)