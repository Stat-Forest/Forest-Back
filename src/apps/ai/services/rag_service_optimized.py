import math
from typing import Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache

from apps.ai.models import KnowledgeChunk
from apps.ai.services.ollama_embeddings import OllamaEmbeddingClient
from apps.ai.services.terminology_normalizer import TerminologyNormalizer
from apps.utils.ai_cache.semantic_cache_service import SemanticCacheService


class RAGService:
    CACHE_KEY = "ai_rag_chunks_v4"

    def __init__(self) -> None:
        self.client = OllamaEmbeddingClient()
        self.top_k = getattr(settings, "AI_TOP_K", 2)
        self.max_context_chars = getattr(settings, "AI_MAX_CONTEXT_CHARS", 1200)
        self.cache_ttl = getattr(settings, "AI_RAG_CACHE_TTL", 600)

    def _load_chunks(self) -> List[Dict]:
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return cached

        rows = list(
            KnowledgeChunk.objects
            .filter(document__is_active=True)
            .select_related("document")
            .values(
                "id",
                "text",
                "embedding",
                "metadata",
                "document__title",
                "document__source_type",
                "document__source_key",
            )
        )

        prepared = []
        for row in rows:
            embedding = row.get("embedding") or []
            text = (row.get("text") or "").strip()
            metadata = row.get("metadata") or {}
            document_title = (row.get("document__title") or "").strip()
            source_type = row.get("document__source_type") or ""
            source_key = row.get("document__source_key") or ""

            if not text or not embedding:
                continue

            prepared.append(
                {
                    "id": row["id"],
                    "text": text[: self.max_context_chars],
                    "embedding": embedding,
                    "metadata": metadata,
                    "document_title": document_title,
                    "source_type": source_type,
                    "source_key": source_key,
                }
            )

        cache.set(self.CACHE_KEY, prepared, timeout=self.cache_ttl)
        return prepared

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot / (norm_a * norm_b)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        normalized = TerminologyNormalizer.normalize_text(text)
        return [p for p in normalized.split() if len(p) >= 3]

    def _keyword_overlap_score(self, query: str, chunk_text: str, document_title: str) -> float:
        query_terms = set(TerminologyNormalizer.expand_query_terms(query))
        if not query_terms:
            return 0.0

        text_terms = set(self._tokenize(chunk_text))
        title_terms = set(self._tokenize(document_title))

        text_overlap = len(query_terms.intersection(text_terms))
        title_overlap = len(query_terms.intersection(title_terms))

        return (text_overlap * 0.18) + (title_overlap * 0.45)

    def _exact_title_boost(self, query: str, document_title: str) -> float:
        q = TerminologyNormalizer.normalize_text(query)
        title = TerminologyNormalizer.normalize_text(document_title)

        if not q or not title:
            return 0.0

        if q == title:
            return 1.0

        if q in title or title in q:
            return 0.45

        q_terms = set(self._tokenize(q))
        t_terms = set(self._tokenize(title))
        if not q_terms or not t_terms:
            return 0.0

        overlap_ratio = len(q_terms.intersection(t_terms)) / max(1, len(q_terms))
        if overlap_ratio >= 0.8:
            return 0.35
        if overlap_ratio >= 0.5:
            return 0.20
        return 0.0

    def _source_type_boost(self, query: str, source_type: str) -> float:
        q = TerminologyNormalizer.normalize_text(query)

        if any(word in q for word in ["nima", "farqi", "tushuntir", "nechta bo'lim", "nechta tur"]):
            if source_type == "model_doc":
                return 0.22
            if source_type == "rule":
                return 0.10

        if any(word in q for word in ["qanday", "qachon", "jarayon", "bosqich"]):
            if source_type == "workflow":
                return 0.22

        return 0.0

    def search(self, query: str, top_k: int | None = None) -> List[str]:
        normalized_top_k = max(1, top_k or self.top_k)

        query_vector = SemanticCacheService.get_embedding(query)
        if not query_vector:
            query_vector = self.client.embed(query)
            if query_vector:
                SemanticCacheService.set_embedding(query, query_vector)

        if not query_vector:
            return []

        chunks = self._load_chunks()
        threshold = getattr(settings, "AI_MIN_SIMILARITY", 0.12)

        scored: List[Tuple[float, str]] = []

        for chunk in chunks:
            semantic_score = self.cosine_similarity(query_vector, chunk["embedding"])
            if semantic_score < threshold:
                continue

            keyword_score = self._keyword_overlap_score(
                query=query,
                chunk_text=chunk["text"],
                document_title=chunk["document_title"],
            )
            exact_title_boost = self._exact_title_boost(
                query=query,
                document_title=chunk["document_title"],
            )
            source_boost = self._source_type_boost(
                query=query,
                source_type=chunk["source_type"],
            )

            final_score = semantic_score + keyword_score + exact_title_boost + source_boost
            scored.append((final_score, chunk["text"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:normalized_top_k]]

    def invalidate_cache(self) -> None:
        cache.delete(self.CACHE_KEY)