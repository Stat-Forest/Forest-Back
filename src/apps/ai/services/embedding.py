import logging
from typing import List

from django.db import models

from apps.ai.models import KnowledgeChunk, KnowledgeDocument
from apps.ai.services.ollama_embeddings import OllamaEmbeddingClient

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self.client = OllamaEmbeddingClient()

    def embed_chunk(self, chunk: KnowledgeChunk) -> bool:
        vector = self.client.embed(chunk.text)
        if not vector:
            return False

        chunk.embedding = vector
        return True

    def embed_document(self, document: KnowledgeDocument, batch_size: int = 100) -> int:
        """
        Generate embeddings only for chunks of one document.
        """
        queryset = KnowledgeChunk.objects.filter(
            document=document
        ).filter(
            models.Q(embedding__isnull=True) | models.Q(embedding=[])
        ).only("id", "text", "embedding", "document_id")

        updated_objects: List[KnowledgeChunk] = []
        updated_count = 0

        for chunk in queryset.iterator(chunk_size=batch_size):
            try:
                if self.embed_chunk(chunk):
                    updated_objects.append(chunk)

                if len(updated_objects) >= batch_size:
                    KnowledgeChunk.objects.bulk_update(
                        updated_objects,
                        ["embedding"],
                        batch_size=batch_size,
                    )
                    updated_count += len(updated_objects)
                    updated_objects.clear()

            except Exception:
                logger.exception("Failed to generate embedding for chunk_id=%s", chunk.id)

        if updated_objects:
            KnowledgeChunk.objects.bulk_update(
                updated_objects,
                ["embedding"],
                batch_size=batch_size,
            )
            updated_count += len(updated_objects)

        return updated_count

    def embed_all(self, batch_size: int = 100) -> int:
        """
        Generate embeddings for all chunks that do not yet have them.
        """
        queryset = KnowledgeChunk.objects.filter(
            models.Q(embedding__isnull=True) | models.Q(embedding=[])
        ).only("id", "text", "embedding")

        updated_objects: List[KnowledgeChunk] = []
        updated_count = 0

        for chunk in queryset.iterator(chunk_size=batch_size):
            try:
                if self.embed_chunk(chunk):
                    updated_objects.append(chunk)

                if len(updated_objects) >= batch_size:
                    KnowledgeChunk.objects.bulk_update(
                        updated_objects,
                        ["embedding"],
                        batch_size=batch_size,
                    )
                    updated_count += len(updated_objects)
                    updated_objects.clear()

            except Exception:
                logger.exception("Failed to generate embedding for chunk_id=%s", chunk.id)

        if updated_objects:
            KnowledgeChunk.objects.bulk_update(
                updated_objects,
                ["embedding"],
                batch_size=batch_size,
            )
            updated_count += len(updated_objects)

        return updated_count