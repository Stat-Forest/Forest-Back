from django.db import transaction

from apps.ai.models import KnowledgeDocument, KnowledgeChunk
from apps.ai.services.chunking import chunk_text


class KnowledgeIngestionService:
    @transaction.atomic
    def ingest_document(self, document: KnowledgeDocument) -> int:
        """
        KnowledgeDocument.content ni chunklarga ajratadi
        va KnowledgeChunk ga ideal ko'rinishda saqlaydi.
        """
        content = (document.content or "").strip()

        # document bo'sh yoki noactive bo'lsa, chunklar ham bo'lmasin
        document.chunks.all().delete()

        if not content or not document.is_active:
            return 0

        raw_chunks = chunk_text(content, chunk_size=1200, overlap=200)

        chunk_objects = []
        for chunk in raw_chunks:
            chunk_objects.append(
                KnowledgeChunk(
                    document=document,
                    chunk_index=chunk.index,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    metadata={
                        "source_type": document.source_type,
                        "source_key": document.source_key,
                        "document_title": document.title,
                    },
                )
            )

        KnowledgeChunk.objects.bulk_create(chunk_objects, batch_size=100)
        return len(chunk_objects)