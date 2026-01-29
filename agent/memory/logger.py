"""
Structured JSON logging for memory operations.
Copilot-inspired logging with daily rotation.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class MemoryLogger:
    """
    JSON logger for memory operations with daily rotation.

    Logs to: .memory/logs/YYYY-MM-DD.json

    Features:
    - Daily log rotation
    - Structured JSON events
    - Automatic directory creation
    - Event deduplication
    """

    def __init__(self, log_dir: str = ".memory/logs"):
        """
        Initialize memory logger.

        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Current log file tracking
        self._current_date = None
        self._current_file = None

    def _get_log_file(self) -> Path:
        """Get current day's log file path."""
        today = self._get_today_date()

        if self._current_date != today:
            self._current_date = today
            self._current_file = self.log_dir / f"{today}.json"

        return self._current_file

    def _get_today_date(self) -> str:
        """Get today's date in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")

    def _write_event(self, event: Dict[str, Any]) -> None:
        """
        Write event to current log file.

        Args:
            event: Event dictionary to log
        """
        try:
            log_file = self._get_log_file()

            # Read existing events
            events = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        events = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    events = []

            # Add new event
            events.append(event)

            # Write back
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to write memory log event: {e}")

    def log_memory_created(self, memory: Dict[str, Any], layer: str, session_id: Optional[str] = None) -> None:
        """
        Log memory creation event.

        Args:
            memory: Memory dictionary
            layer: Memory layer ("working", "episodic", "semantic")
            session_id: Optional session identifier
        """
        event = {
            "event": "memory_created",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "layer": layer,
            "memory": memory
        }
        self._write_event(event)
        logger.debug(f"Logged memory creation: {memory.get('id', 'unknown')}")

    def log_memory_retrieved(self,
                           query: str,
                           memories: List[Dict[str, Any]],
                           retrieval_time_ms: float,
                           session_id: Optional[str] = None) -> None:
        """
        Log memory retrieval event.

        Args:
            query: Search query used
            memories: Retrieved memories
            retrieval_time_ms: Time taken for retrieval
            session_id: Optional session identifier
        """
        event = {
            "event": "memory_retrieved",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "query": query,
            "memory_count": len(memories),
            "retrieval_time_ms": retrieval_time_ms,
            "memories": [{"id": m.get("id"), "category": m.get("category")} for m in memories]
        }
        self._write_event(event)
        logger.debug(f"Logged memory retrieval: {len(memories)} memories for query: {query[:50]}...")

    def log_extraction_completed(self,
                               session_id: str,
                               extracted_count: int,
                               failed: bool = False,
                               error_message: Optional[str] = None) -> None:
        """
        Log memory extraction completion.

        Args:
            session_id: Session that was processed
            extracted_count: Number of memories extracted
            failed: Whether extraction failed
            error_message: Optional error details
        """
        event = {
            "event": "extraction_completed",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "extracted_count": extracted_count,
            "failed": failed,
            "error_message": error_message
        }
        self._write_event(event)

        if failed:
            logger.error(f"Logged failed extraction for session {session_id}: {error_message}")
        else:
            logger.info(f"Logged successful extraction: {extracted_count} memories from session {session_id}")

    def log_consolidation_event(self,
                              action: str,
                              affected_count: int,
                              notes: Optional[str] = None) -> None:
        """
        Log memory consolidation event.

        Args:
            action: Consolidation action ("extract", "decay", "promote")
            affected_count: Number of memories affected
            notes: Optional details
        """
        event = {
            "event": "consolidation",
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "affected_count": affected_count,
            "notes": notes
        }
        self._write_event(event)
        logger.info(f"Logged consolidation: {action} affected {affected_count} memories")