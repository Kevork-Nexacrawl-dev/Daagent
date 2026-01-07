"""
Response caching system for latency optimization.
Provides instant responses for frequently asked questions.
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path


class ResponseCache:
    """
    Disk-persistent cache for FAQ responses with TTL expiration.
    """

    def __init__(self, cache_file: str = "memory-bank/response_cache.json", ttl_hours: int = 24):
        """
        Initialize response cache.

        Args:
            cache_file: Path to cache file
            ttl_hours: Time-to-live in hours
        """
        self.cache_file = Path(cache_file)
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk, cleaning expired entries."""
        if not self.cache_file.exists():
            self.cache = {}
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cache = {}

                # Clean expired entries
                now = datetime.now()
                for key, entry in data.items():
                    if self._is_entry_valid(entry, now):
                        self.cache[key] = entry
                    else:
                        print(f"Cache: Expired entry removed: {entry.get('query', 'unknown')}")

                # Save cleaned cache
                self._save_cache()

        except (json.JSONDecodeError, IOError) as e:
            print(f"Cache: Error loading cache file: {e}")
            self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Cache: Error saving cache file: {e}")

    def _is_entry_valid(self, entry: Dict[str, Any], now: datetime) -> bool:
        """
        Check if cache entry is still valid.

        Args:
            entry: Cache entry
            now: Current datetime

        Returns:
            True if entry is valid
        """
        try:
            timestamp_str = entry.get('timestamp')
            if not timestamp_str:
                return False

            timestamp = datetime.fromisoformat(timestamp_str)
            expiry = timestamp + timedelta(hours=self.ttl_hours)

            return now < expiry
        except (ValueError, TypeError):
            return False

    def _generate_key(self, query: str) -> str:
        """
        Generate cache key from query using hash.

        Args:
            query: The query string

        Returns:
            Hash-based cache key
        """
        # Normalize query for consistent hashing
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]

    def get(self, query: str) -> Optional[str]:
        """
        Get cached response for query.

        Args:
            query: The query to look up

        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_key(query)
        entry = self.cache.get(key)

        if entry and self._is_entry_valid(entry, datetime.now()):
            # Update hit count
            entry['hits'] = entry.get('hits', 0) + 1
            self._save_cache()
            return entry.get('response')

        return None

    def put(self, query: str, response: str) -> None:
        """
        Cache a response for a query.

        Args:
            query: The query
            response: The response to cache
        """
        key = self._generate_key(query)
        now = datetime.now()

        entry = {
            'query': query,
            'response': response,
            'timestamp': now.isoformat(),
            'hits': 1
        }

        self.cache[key] = entry
        self._save_cache()

    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache = {}
        self._save_cache()
        print("Cache: All entries cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self.cache)
        total_hits = sum(entry.get('hits', 0) for entry in self.cache.values())

        if self.cache_file.exists():
            cache_size = self.cache_file.stat().st_size
        else:
            cache_size = 0

        return {
            'total_entries': total_entries,
            'total_hits': total_hits,
            'cache_file_size_kb': round(cache_size / 1024, 2),
            'ttl_hours': self.ttl_hours
        }

    def list_entries(self) -> Dict[str, Dict[str, Any]]:
        """
        List all cache entries with metadata.

        Returns:
            Dictionary of cache entries
        """
        return {
            entry['query']: {
                'response_preview': entry['response'][:100] + '...' if len(entry['response']) > 100 else entry['response'],
                'timestamp': entry['timestamp'],
                'hits': entry.get('hits', 0),
                'expires_in_hours': self._get_expiry_hours(entry)
            }
            for entry in self.cache.values()
        }

    def _get_expiry_hours(self, entry: Dict[str, Any]) -> float:
        """
        Get hours until entry expires.

        Args:
            entry: Cache entry

        Returns:
            Hours until expiry (negative if expired)
        """
        try:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            expiry = timestamp + timedelta(hours=self.ttl_hours)
            now = datetime.now()
            return (expiry - now).total_seconds() / 3600
        except (ValueError, TypeError):
            return -1