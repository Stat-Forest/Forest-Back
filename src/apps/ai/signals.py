from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.ai.models import KnowledgeDocument
from apps.ai.services.embedding import EmbeddingService
from apps.ai.services.ingestion import KnowledgeIngestionService
from apps.ai.services.rag_service_optimized import RAGService


@receiver(post_save, sender=KnowledgeDocument)
def reindex_knowledge_document(sender, instance: KnowledgeDocument, **kwargs):
    """
    KnowledgeDocument saqlansa:
    - content chunklarga bo'linadi
    - embedding generatsiya qilinadi
    - RAG cache tozalanadi
    """
    def _run():
        ingestion_service = KnowledgeIngestionService()
        ingestion_service.ingest_document(instance)

        if instance.is_active:
            embedding_service = EmbeddingService()
            embedding_service.embed_document(instance)

        RAGService().invalidate_cache()

    transaction.on_commit(_run)


@receiver(post_delete, sender=KnowledgeDocument)
def cleanup_knowledge_document(sender, instance: KnowledgeDocument, **kwargs):
    RAGService().invalidate_cache()