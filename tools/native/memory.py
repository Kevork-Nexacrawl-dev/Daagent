"""
Smart Memory - Daagent Native Tools
Ported from autogen-shop with adaptations for OpenAI function calling.
Uses Redis for hot cache, file-based storage as fallback.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# ============================================
# TOOL SCHEMAS (OpenAI Function Calling Format)
# ============================================

STORE_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "store_memory",
        "description": "Save context or information to persistent memory storage",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier for grouping memories"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Agent name for the memory"
                },
                "content": {
                    "type": "string",
                    "description": "Content to store in memory"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorization"
                }
            },
            "required": ["session_id", "agent_name", "content"]
        }
    }
}

RETRIEVE_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "retrieve_memory",
        "description": "Query and retrieve stored memories by session or content",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier to retrieve memories for"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Agent name to filter memories"
                },
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant memories"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return",
                    "default": 10
                }
            },
            "required": ["session_id"]
        }
    }
}

CLEAR_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "clear_memory",
        "description": "Clear memory for a specific session or all sessions",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier to clear (optional - clears all if not provided)"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Agent name to filter clearing"
                }
            }
        }
    }
}

# ============================================
# MEMORY MANAGER CLASS
# ============================================

class MemoryManager:
    """Simple memory manager with Redis fallback to file storage."""

    def __init__(self):
        self.redis_client = None
        self.memory_dir = Path("daagent/memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_timeout=2
                )
                self.redis_client.ping()
                print("✅ Connected to Redis for memory storage")
            except Exception as e:
                print(f"❌ Redis connection failed: {e}. Using file-based storage.")
                self.redis_client = None

    def _calculate_importance(self, text: str) -> float:
        """Calculate importance score 0.0-1.0."""
        score = 0.1  # Base

        # Keywords that indicate importance
        keywords = ['error', 'critical', 'important', 'key', 'solution', 'result']
        if any(re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE) for kw in keywords):
            score += 0.3

        # Code patterns
        code_patterns = [r'def\s+\w+', r'class\s+\w+', r'import\s+\w+']
        if any(re.search(pattern, text) for pattern in code_patterns):
            score += 0.2

        return min(score, 1.0)

    def _classify_topic(self, text: str) -> str:
        """Simple topic classification."""
        topics = {
            'code': ['def', 'class', 'import', 'function'],
            'error': ['error', 'exception', 'bug', 'fail'],
            'planning': ['plan', 'strategy', 'task'],
            'general': []
        }
        text_lower = text.lower()
        for topic, kws in topics.items():
            if any(kw in text_lower for kw in kws):
                return topic
        return 'general'

    def store_memory(self, session_id: str, agent_name: str, content: str, tags: Optional[List[str]] = None) -> str:
        """Store memory with importance scoring."""
        try:
            importance = self._calculate_importance(content)
            topic = self._classify_topic(content)
            created_at = datetime.now().isoformat()
            tags = tags or []

            memory_entry = {
                "session_id": session_id,
                "agent_name": agent_name,
                "content": content,
                "importance": importance,
                "topic": topic,
                "tags": tags,
                "created_at": created_at
            }

            if self.redis_client:
                # Store in Redis with TTL (24 hours)
                key = f"memory:{session_id}:{agent_name}"
                self.redis_client.lpush(key, json.dumps(memory_entry))
                self.redis_client.expire(key, 86400)  # 24 hours
                # Keep only recent 50 entries
                self.redis_client.ltrim(key, 0, 49)
            else:
                # Fallback to file storage
                session_file = self.memory_dir / f"{session_id}_{agent_name}.json"
                memories = []

                if session_file.exists():
                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            memories = json.load(f)
                    except:
                        memories = []

                memories.append(memory_entry)
                # Keep only recent 50 entries
                memories = memories[-50:]

                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, indent=2, ensure_ascii=False)

            return json.dumps({
                "status": "success",
                "importance_score": importance,
                "topic": topic,
                "storage": "redis" if self.redis_client else "file"
            })

        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    def retrieve_memory(self, session_id: str, agent_name: Optional[str] = None,
                       query: Optional[str] = None, limit: int = 10) -> str:
        """Retrieve memories with optional filtering."""
        try:
            all_memories = []

            if self.redis_client:
                # Get from Redis
                if agent_name:
                    key = f"memory:{session_id}:{agent_name}"
                    raw_memories = self.redis_client.lrange(key, 0, -1) or []
                    all_memories = [json.loads(m) for m in raw_memories]
                else:
                    # Get all agent memories for session
                    keys = self.redis_client.keys(f"memory:{session_id}:*")
                    for key in keys:
                        raw_memories = self.redis_client.lrange(key, 0, -1) or []
                        all_memories.extend([json.loads(m) for m in raw_memories])
            else:
                # Get from files
                if agent_name:
                    session_file = self.memory_dir / f"{session_id}_{agent_name}.json"
                    if session_file.exists():
                        with open(session_file, 'r', encoding='utf-8') as f:
                            all_memories = json.load(f)
                else:
                    # Get all agent files for session
                    for file_path in self.memory_dir.glob(f"{session_id}_*.json"):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                all_memories.extend(json.load(f))
                        except:
                            continue

            # Filter by query if provided
            if query:
                query_lower = query.lower()
                filtered_memories = []
                for mem in all_memories:
                    content_lower = mem.get("content", "").lower()
                    if query_lower in content_lower:
                        filtered_memories.append(mem)
                all_memories = filtered_memories

            # Sort by importance and recency
            all_memories.sort(key=lambda x: (x.get("importance", 0), x.get("created_at", "")), reverse=True)

            # Limit results
            memories = all_memories[:limit]

            return json.dumps({
                "status": "success",
                "memories_found": len(all_memories),
                "memories_returned": len(memories),
                "storage": "redis" if self.redis_client else "file",
                "memories": memories
            })

        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    def clear_memory(self, session_id: Optional[str] = None, agent_name: Optional[str] = None) -> str:
        """Clear memory for session/agent."""
        try:
            cleared_count = 0

            if self.redis_client:
                if session_id and agent_name:
                    key = f"memory:{session_id}:{agent_name}"
                    self.redis_client.delete(key)
                    cleared_count = 1
                elif session_id:
                    keys = self.redis_client.keys(f"memory:{session_id}:*")
                    for key in keys:
                        self.redis_client.delete(key)
                    cleared_count = len(keys)
                else:
                    # Clear all memory keys
                    keys = self.redis_client.keys("memory:*")
                    for key in keys:
                        self.redis_client.delete(key)
                    cleared_count = len(keys)
            else:
                # Clear files
                if session_id and agent_name:
                    session_file = self.memory_dir / f"{session_id}_{agent_name}.json"
                    if session_file.exists():
                        session_file.unlink()
                        cleared_count = 1
                elif session_id:
                    files = list(self.memory_dir.glob(f"{session_id}_*.json"))
                    for file_path in files:
                        file_path.unlink()
                    cleared_count = len(files)
                else:
                    # Clear all memory files
                    files = list(self.memory_dir.glob("*.json"))
                    for file_path in files:
                        file_path.unlink()
                    cleared_count = len(files)

            return json.dumps({
                "status": "success",
                "cleared_count": cleared_count,
                "storage": "redis" if self.redis_client else "file"
            })

        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

# Global memory manager instance
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """Get or create memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

# ============================================
# TOOL IMPLEMENTATIONS
# ============================================

def execute_store_memory(args: Dict[str, Any]) -> str:
    """
    Execute store_memory tool.

    Args:
        args: Dict with session_id, agent_name, content, optional tags

    Returns:
        JSON string with storage result
    """
    try:
        session_id = args.get("session_id", "")
        agent_name = args.get("agent_name", "")
        content = args.get("content", "")
        tags = args.get("tags", [])

        if not session_id or not agent_name or not content:
            return json.dumps({"status": "error", "error": "Missing required parameters"})

        manager = get_memory_manager()
        return manager.store_memory(session_id, agent_name, content, tags)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_retrieve_memory(args: Dict[str, Any]) -> str:
    """
    Execute retrieve_memory tool.

    Args:
        args: Dict with session_id and optional filters

    Returns:
        JSON string with retrieved memories
    """
    try:
        session_id = args.get("session_id", "")
        agent_name = args.get("agent_name")
        query = args.get("query")
        limit = args.get("limit", 10)

        if not session_id:
            return json.dumps({"status": "error", "error": "session_id is required"})

        manager = get_memory_manager()
        return manager.retrieve_memory(session_id, agent_name, query, limit)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def execute_clear_memory(args: Dict[str, Any]) -> str:
    """
    Execute clear_memory tool.

    Args:
        args: Dict with optional session_id and agent_name

    Returns:
        JSON string with clearing result
    """
    try:
        session_id = args.get("session_id")
        agent_name = args.get("agent_name")

        manager = get_memory_manager()
        return manager.clear_memory(session_id, agent_name)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ============================================
# REGISTRY (for agent/core.py to discover)
# ============================================

TOOL_SCHEMAS = [STORE_MEMORY_SCHEMA, RETRIEVE_MEMORY_SCHEMA, CLEAR_MEMORY_SCHEMA]

def execute_tool(operation: str, **kwargs) -> str:
    """
    Execute memory management tool.

    Args:
        operation: Tool operation name
        **kwargs: Tool arguments

    Returns:
        JSON string result
    """
    if operation == "store_memory":
        return execute_store_memory(kwargs)
    elif operation == "retrieve_memory":
        return execute_retrieve_memory(kwargs)
    elif operation == "clear_memory":
        return execute_clear_memory(kwargs)
    else:
        return json.dumps({"status": "error", "error": f"Unknown operation: {operation}"})