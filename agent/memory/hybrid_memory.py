"""
Hybrid Memory System orchestrator.
Implements RAISE architecture with adaptive gating and vector search.
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from agent.config import Config
from agent.memory.categories import MemoryCategory
from agent.memory.vector_store import VectorStore
from agent.memory.extractor import MemoryExtractor
from agent.memory.logger import MemoryLogger

logger = logging.getLogger(__name__)


class HybridMemory:
    """
    Main memory system orchestrator implementing RAISE architecture.

    Layers:
    - Working: In-memory session context
    - Episodic: Time-based conversation events
    - Semantic: Long-term facts with vector search

    Features:
    - Adaptive gating for retrieval
    - Perplexity-style extraction
    - Privacy-aware vector embeddings
    - Structured JSON logging
    """

    def __init__(self, db_path: str = None, log_dir: str = None):
        """
        Initialize hybrid memory system.

        Args:
            db_path: Path to SQLite database (defaults to config)
            log_dir: Directory for logs (defaults to config)
        """
        self.db_path = db_path or Config.MEMORY_DB_PATH
        self.log_dir = log_dir or Config.MEMORY_LOG_DIR

        # Ensure directories exist
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.vector_store = VectorStore()
        self.extractor = MemoryExtractor()
        self.logger = MemoryLogger(self.log_dir)

        # Working memory (in-memory)
        self.working_memory: List[Dict[str, Any]] = []

        # Initialize database
        self._init_database()

        logger.info("Hybrid memory system initialized")

    def _init_database(self) -> None:
        """Initialize SQLite database with schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                with open("agent/memory/schema.sql", "r") as f:
                    schema = f.read()
                conn.executescript(schema)
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ===== STORAGE METHODS =====

    def store_working(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """
        Store in working memory (in-memory session context).

        Args:
            content: Content to store
            metadata: Optional metadata
        """
        entry = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        self.working_memory.append(entry)

        # Keep only last 10 entries
        if len(self.working_memory) > 10:
            self.working_memory = self.working_memory[-10:]

    def store_episodic(self,
                      content: str,
                      session_id: str,
                      importance: float = 0.5,
                      metadata: Dict[str, Any] = None) -> str:
        """
        Store in episodic memory (time-based events).

        Args:
            content: Content to store
            session_id: Session identifier
            importance: Importance score (0.0-1.0)
            metadata: Optional metadata

        Returns:
            Memory ID
        """
        memory_id = str(uuid.uuid4())

        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO episodic_memory
                    (id, session_id, timestamp, content, metadata, importance)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    memory_id,
                    session_id,
                    datetime.now().isoformat(),
                    content,
                    json.dumps(metadata or {}),
                    importance
                ))

            self.logger.log_memory_created({
                "id": memory_id,
                "content": content,
                "importance": importance
            }, "episodic", session_id)

            logger.debug(f"Stored episodic memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store episodic memory: {e}")
            return None

    def store_semantic(self,
                      category: str,
                      content: str,
                      confidence: float = 0.8,
                      source: str = None,
                      metadata: Dict[str, Any] = None) -> str:
        """
        Store in semantic memory (long-term facts).

        Args:
            category: Memory category
            content: Content to store
            confidence: Confidence score (0.0-1.0)
            source: Source session/conversation
            metadata: Optional metadata

        Returns:
            Memory ID
        """
        memory_id = str(uuid.uuid4())

        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO semantic_memory
                    (id, category, content, confidence, source, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    memory_id,
                    category,
                    content,
                    confidence,
                    source,
                    json.dumps(metadata or {})
                ))

            # Create vector embedding if high confidence and not privacy-sensitive
            embedding_id = None
            if confidence >= 0.7:
                embedding_metadata = metadata or {}
                embedding_metadata["category"] = category
                embedding_metadata["confidence"] = confidence

                embedding_id = self.vector_store.add_embedding(
                    text=content,
                    memory_id=memory_id,
                    metadata=embedding_metadata
                )

            # Update embedding ID in database
            if embedding_id:
                conn.execute(
                    "UPDATE semantic_memory SET embedding_id = ? WHERE id = ?",
                    (embedding_id, memory_id)
                )

            self.logger.log_memory_created({
                "id": memory_id,
                "category": category,
                "content": content,
                "confidence": confidence
            }, "semantic", source)

            logger.debug(f"Stored semantic memory: {memory_id} (embedding: {embedding_id})")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store semantic memory: {e}")
            return None

    # ===== RETRIEVAL METHODS =====

    def retrieve_relevant(self,
                         query: str,
                         task_type: str = "general",
                         top_k: int = 5,
                         session_id: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories using adaptive gating.

        Args:
            query: Search query
            task_type: Query type ("recall", "knowledge", "general")
            top_k: Maximum memories to return
            session_id: Current session ID

        Returns:
            List of relevant memory dictionaries
        """
        import time
        start_time = time.time()

        try:
            # Adaptive gating based on task type
            if task_type == "recall":
                # Prioritize episodic (70%) + working (30%)
                episodic_count = int(top_k * 0.7)
                working_count = top_k - episodic_count
                semantic_count = 0
            elif task_type == "knowledge":
                # Prioritize semantic (80%) + episodic (20%)
                semantic_count = int(top_k * 0.8)
                episodic_count = top_k - semantic_count
                working_count = 0
            else:  # general
                # Balanced: 40% semantic, 30% episodic, 30% working
                semantic_count = int(top_k * 0.4)
                episodic_count = int(top_k * 0.3)
                working_count = top_k - semantic_count - episodic_count

            memories = []

            # Retrieve from each layer
            if semantic_count > 0:
                semantic_memories = self._retrieve_semantic(query, semantic_count)
                memories.extend(semantic_memories)

            if episodic_count > 0:
                episodic_memories = self._retrieve_episodic(query, episodic_count, session_id)
                memories.extend(episodic_memories)

            if working_count > 0:
                working_memories = self._retrieve_working(query, working_count)
                memories.extend(working_memories)

            # Sort by relevance and limit
            memories.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            final_memories = memories[:top_k]

            # Log retrieval
            retrieval_time = time.time() - start_time
            self.logger.log_memory_retrieved(
                query=query,
                memories=final_memories,
                retrieval_time_ms=retrieval_time * 1000,
                session_id=session_id
            )

            logger.debug(f"Retrieved {len(final_memories)} memories in {retrieval_time:.2f}s")
            return final_memories

        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return []

    def _retrieve_semantic(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Retrieve from semantic memory using vector search."""
        try:
            # Vector search
            vector_results = self.vector_store.search_similar(query, top_k=top_k)

            memories = []
            for memory_id, similarity_score in vector_results:
                memory = self._get_semantic_memory(memory_id)
                if memory:
                    memory["relevance_score"] = similarity_score
                    memory["layer"] = "semantic"
                    memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Semantic retrieval failed: {e}")
            return []

    def _retrieve_episodic(self, query: str, top_k: int, session_id: str = None) -> List[Dict[str, Any]]:
        """Retrieve from episodic memory using text search."""
        try:
            # Simple text-based search (could be enhanced with BM25)
            with self._get_db_connection() as conn:
                # Prioritize recent, important memories from current session
                cursor = conn.execute("""
                    SELECT id, content, importance, metadata
                    FROM episodic_memory
                    WHERE (session_id = ? OR ? IS NULL)
                      AND content LIKE ?
                    ORDER BY importance DESC, timestamp DESC
                    LIMIT ?
                """, (session_id, session_id, f"%{query}%", top_k * 2))  # Get more for filtering

                memories = []
                for row in cursor:
                    memory = dict(row)
                    memory["metadata"] = json.loads(memory["metadata"] or "{}")
                    memory["relevance_score"] = memory["importance"]  # Use importance as relevance
                    memory["layer"] = "episodic"
                    memories.append(memory)

                return memories[:top_k]

        except Exception as e:
            logger.error(f"Episodic retrieval failed: {e}")
            return []

    def _retrieve_working(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Retrieve from working memory using simple text match."""
        try:
            matching_memories = []
            for entry in reversed(self.working_memory):  # Most recent first
                content = entry["content"].lower()
                query_lower = query.lower()

                # Simple relevance scoring
                if query_lower in content:
                    relevance = 1.0
                elif any(word in content for word in query_lower.split()):
                    relevance = 0.5
                else:
                    continue

                memory = {
                    "content": entry["content"],
                    "metadata": entry["metadata"],
                    "relevance_score": relevance,
                    "layer": "working"
                }
                matching_memories.append(memory)

            return matching_memories[:top_k]

        except Exception as e:
            logger.error(f"Working memory retrieval failed: {e}")
            return []

    def _get_semantic_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get semantic memory by ID."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM semantic_memory WHERE id = ?
                """, (memory_id,))

                row = cursor.fetchone()
                if row:
                    memory = dict(row)
                    memory["metadata"] = json.loads(memory["metadata"] or "{}")
                    return memory

        except Exception as e:
            logger.error(f"Failed to get semantic memory {memory_id}: {e}")

        return None

    # ===== EXTRACTION & CONSOLIDATION =====

    def should_run_extraction(self, conversation_history: List[Dict[str, Any]]) -> bool:
        """
        Determine if extraction should run (cost control).

        Args:
            conversation_history: Full conversation history

        Returns:
            True if extraction should proceed
        """
        if not Config.MEMORY_EXTRACTION_ENABLED:
            return False

        min_turns = Config.MEMORY_MIN_TURNS_FOR_EXTRACTION
        user_messages = [m for m in conversation_history if m.get("role") == "user"]

        return len(user_messages) >= min_turns

    def extract_and_consolidate(self, session_id: str, conversation_history: List[Dict[str, Any]]) -> None:
        """
        Run memory extraction and consolidation on session end.

        Args:
            session_id: Session identifier
            conversation_history: Full conversation history
        """
        try:
            # Check if extraction should run
            if not self.should_run_extraction(conversation_history):
                logger.info(f"Skipping extraction for session {session_id} (cost control)")
                return

            # Extract memories
            extracted_memories = self.extractor.extract_from_session(
                conversation_history=conversation_history,
                session_id=session_id
            )

            if not extracted_memories:
                self.logger.log_extraction_completed(session_id, 0, failed=True, error_message="No memories extracted")
                return

            # Store extracted memories
            stored_count = 0
            for mem in extracted_memories:
                memory_id = self.store_semantic(
                    category=mem["category"],
                    content=mem["content"],
                    confidence=mem["confidence"],
                    source=session_id,
                    metadata=mem.get("metadata", {})
                )
                if memory_id:
                    stored_count += 1

            # Run consolidation (decay old memories)
            self._consolidate_memories()

            # Log completion
            self.logger.log_extraction_completed(session_id, stored_count)

            logger.info(f"Extraction complete: {stored_count}/{len(extracted_memories)} memories stored")

        except Exception as e:
            logger.error(f"Extraction and consolidation failed for session {session_id}: {e}")
            self.logger.log_extraction_completed(session_id, 0, failed=True, error_message=str(e))

    def _consolidate_memories(self) -> None:
        """Run memory consolidation (decay old episodic memories)."""
        try:
            retention_days = Config.MEMORY_RETENTION_DAYS
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            with self._get_db_connection() as conn:
                # Decay old episodic memories
                cursor = conn.execute("""
                    UPDATE episodic_memory
                    SET importance = importance * 0.9
                    WHERE timestamp < ?
                      AND importance > 0.1
                """, (cutoff_date.isoformat(),))

                decayed_count = cursor.rowcount

                # Remove very old, low-importance memories
                cursor = conn.execute("""
                    DELETE FROM episodic_memory
                    WHERE timestamp < ?
                      AND importance < 0.1
                """, (cutoff_date.isoformat(),))

                deleted_count = cursor.rowcount

            self.logger.log_consolidation_event(
                action="decay",
                affected_count=decayed_count,
                notes=f"Decayed {decayed_count} old memories, deleted {deleted_count} very old ones"
            )

            logger.info(f"Consolidation complete: decayed {decayed_count}, deleted {deleted_count}")

        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")

    # ===== UTILITY METHODS =====

    def format_for_injection(self, memories: List[Dict[str, Any]]) -> str:
        """
        Format memories for LLM context injection.

        Args:
            memories: List of memory dictionaries

        Returns:
            Formatted context string (max 200 tokens)
        """
        if not memories:
            return ""

        formatted_memories = []
        total_tokens = 0
        max_tokens = Config.MEMORY_MAX_INJECTION_TOKENS

        for mem in memories:
            category = mem.get("category", "general")
            content = mem.get("content", "")

            # Add privacy indicator
            privacy_flag = "🔒" if mem.get("metadata", {}).get("privacy_sensitive") else ""

            formatted = f"- {privacy_flag}[{category}] {content}"

            # Rough token estimation (1 token ≈ 4 chars)
            token_count = len(formatted) // 4
            if total_tokens + token_count > max_tokens:
                break

            formatted_memories.append(formatted)
            total_tokens += token_count

        if formatted_memories:
            return f"RELEVANT CONTEXT:\n" + "\n".join(formatted_memories)
        else:
            return ""

    def get_all_semantic(self, category: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all semantic memories (for CLI viewing).

        Args:
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of semantic memories
        """
        try:
            with self._get_db_connection() as conn:
                if category:
                    cursor = conn.execute("""
                        SELECT * FROM semantic_memory
                        WHERE category = ?
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT ?
                    """, (category, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM semantic_memory
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT ?
                    """, (limit,))

                memories = []
                for row in cursor:
                    memory = dict(row)
                    memory["metadata"] = json.loads(memory["metadata"] or "{}")
                    memories.append(memory)

                return memories

        except Exception as e:
            logger.error(f"Failed to get semantic memories: {e}")
            return []

    def clear_all(self) -> None:
        """Clear all memories (for testing/reset)."""
        try:
            # Clear database
            with self._get_db_connection() as conn:
                conn.execute("DELETE FROM episodic_memory")
                conn.execute("DELETE FROM semantic_memory")
                conn.execute("DELETE FROM consolidation_log")

            # Clear vector store
            # Note: ChromaDB doesn't have a simple clear method, would need recreation

            # Clear working memory
            self.working_memory = []

            logger.info("All memories cleared")

        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search across all memory layers for CLI usage.

        Args:
            query: Search query
            top_k: Maximum results to return

        Returns:
            List of matching memories with metadata
        """
        try:
            results = []

            # Search semantic memory (vector search)
            semantic_results = self._retrieve_semantic(query, top_k // 2)
            results.extend(semantic_results)

            # Search episodic memory (text search)
            episodic_results = self._retrieve_episodic(query, top_k // 2)
            results.extend(episodic_results)

            # Search working memory
            working_results = self._retrieve_working(query, top_k // 2)
            results.extend(working_results)

            # Sort by relevance and deduplicate
            seen_content = set()
            unique_results = []
            for mem in sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True):
                content = mem.get("content", "")
                if content not in seen_content:
                    seen_content.add(content)
                    unique_results.append(mem)

            return unique_results[:top_k]

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []