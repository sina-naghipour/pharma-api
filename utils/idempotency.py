from django.core.cache import cache
import json

class IdempotencyHelper:
    @staticmethod
    def get_or_create(key, ttl_seconds, processor_func):
        """
        key: string, the idempotency key
        ttl_seconds: int, time to live in seconds
        processor_func: callable that returns (response_data, status_code)
        Returns tuple (response_data, status_code, from_cache)
        """
        cached = cache.get(key)
        if cached is not None:
            return cached['data'], cached['status'], True

        # Execute the processor
        data, status = processor_func()
        # Store response in cache
        cache.set(key, {'data': data, 'status': status}, timeout=ttl_seconds)
        return data, status, False

    @staticmethod
    def generate_key(prefix, *identifiers):
        """Generate a namespaced key from identifiers."""
        return f"idemp:{prefix}:" + ":".join(str(i) for i in identifiers)