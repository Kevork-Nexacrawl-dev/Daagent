"""
Vector store integration using ChromaDB for semantic similarity search.
Handles embeddings for high-importance memories.
"""

import os
import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB-based vector store for semantic memory search.

    Features:
    - Embedded ChromaDB (no server required)
    - Sentence-transformers embeddings (free)
    - Privacy filtering (no PII in vectors)
    - Automatic collection management
    """

    def __init__(self,
                 collection_name: str = "daagent_memory",
                 persist_directory: str = ".memory/chroma",
                 model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize vector store.

        Args:
            collection_name: ChromaDB collection name
            persist_directory: Directory for ChromaDB persistence
            model_name: Sentence-transformers model
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.model_name = model_name

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Initialized ChromaDB collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collection: {e}")
            raise

    def add_embedding(self, text: str, memory_id: str, metadata: Dict[str, Any]) -> str:
        """
        Generate and store embedding for memory.

        Args:
            text: Text to embed
            memory_id: Unique memory identifier
            metadata: Memory metadata (for filtering)

        Returns:
            embedding_id: ChromaDB document ID
        """
        try:
            # Check privacy flag
            if metadata.get("privacy_sensitive", False):
                logger.info(f"Skipping embedding for privacy-sensitive memory: {memory_id}")
                return None

            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()

            # Add to collection
            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
                ids=[memory_id]
            )

            logger.debug(f"Added embedding for memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to add embedding for {memory_id}: {e}")
            return None

    def search_similar(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Tuple[str, float]]:
        """
        Search for similar memories using vector similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of (memory_id, similarity_score) tuples
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["distances"]
            )

            # Format results
            memory_results = []
            if results["ids"] and results["ids"][0]:
                for memory_id, distance in zip(results["ids"][0], results["distances"][0]):
                    # Convert distance to similarity (cosine similarity)
                    similarity = 1.0 - distance
                    memory_results.append((memory_id, similarity))

            logger.debug(f"Vector search returned {len(memory_results)} results for query: {query[:50]}...")
            return memory_results

        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")
            return []

    def delete_embedding(self, embedding_id: str) -> bool:
        """
        Remove embedding from store.

        Args:
            embedding_id: ChromaDB document ID to remove

        Returns:
            True if deleted, False otherwise
        """
        try:
            self.collection.delete(ids=[embedding_id])
            logger.debug(f"Deleted embedding: {embedding_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete embedding {embedding_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.

        Returns:
            Dictionary with collection stats
        """
        try:
            count = self.collection.count()
            return {
                "total_embeddings": count,
                "collection_name": self.collection_name,
                "model_name": self.model_name
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}