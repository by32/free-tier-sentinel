"""Capacity caching system to avoid API rate limits."""

import hashlib
from datetime import UTC, datetime, timedelta

from sentinel.capacity.checker import CapacityResult


class CapacityCache:
    """In-memory cache for capacity check results."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL in seconds."""
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict] = {}

    def _generate_key(self, provider: str, region: str, resource_type: str) -> str:
        """Generate a unique cache key for the given parameters."""
        key_string = f"{provider}:{region}:{resource_type}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(
        self, provider: str, region: str, resource_type: str
    ) -> CapacityResult | None:
        """Get cached capacity result if not expired."""
        key = self._generate_key(provider, region, resource_type)

        if key not in self._cache:
            return None

        cache_entry = self._cache[key]
        cached_time = cache_entry["timestamp"]

        # Check if cache entry has expired
        if datetime.now(UTC) - cached_time > timedelta(seconds=self.ttl_seconds):
            del self._cache[key]
            return None

        return cache_entry["result"]

    def set(
        self, provider: str, region: str, resource_type: str, result: CapacityResult
    ):
        """Store capacity result in cache with current timestamp."""
        key = self._generate_key(provider, region, resource_type)

        self._cache[key] = {"result": result, "timestamp": datetime.now(UTC)}

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()

    def clear_expired(self):
        """Clear only expired cache entries."""
        current_time = datetime.now(UTC)
        expired_keys = []

        for key, cache_entry in self._cache.items():
            if current_time - cache_entry["timestamp"] > timedelta(
                seconds=self.ttl_seconds
            ):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)
