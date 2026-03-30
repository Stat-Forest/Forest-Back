import hashlib
import json
from typing import List, Optional
from django.core.cache import cache


class SemanticCacheService:
    
    PREFIX = "ai_semantic"
    EMBEDDING_PREFIX = "ai_embedding"
    
    @classmethod
    def _make_key(cls, prefix: str, text: str) -> str:
        normalized = text.strip().lower()
        hashed = hashlib.md5(normalized.encode()).hexdigest()
        return f"{prefix}:{hashed}"
    
    @classmethod
    def get_embedding(cls, text: str) -> Optional[List[float]]:
        key = cls._make_key(cls.EMBEDDING_PREFIX, text)
        return cache.get(key)
    
    @classmethod
    def set_embedding(cls, text: str, embedding: List[float], timeout=60*60*24*7):
        key = cls._make_key(cls.EMBEDDING_PREFIX, text)
        cache.set(key, embedding, timeout=timeout)
    
    @classmethod
    def get_similar_response(cls, query: str, threshold: float = 0.85) -> Optional[str]:
        query_key = cls._make_key(cls.PREFIX, query)
        return cache.get(query_key)
    
    @classmethod
    def set_similar_response(cls, query: str, response: str, timeout=60*60*2):
        query_key = cls._make_key(cls.PREFIX, query)
        cache.set(query_key, response, timeout=timeout)
