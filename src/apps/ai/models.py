from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.base.models import AbstractBaseModel


class KnowledgeDocument(AbstractBaseModel):
    class SourceType(models.TextChoices):
        MANUAL = "manual", "Qo'lda kiritilgan"
        MODEL_DOC = "model_doc", "Model hujjati"
        WORKFLOW = "workflow", "Ish jarayoni"
        RULE = "rule", "Qoida"

    title = models.CharField(
        max_length=255,
        verbose_name="Sarlavha",
        help_text=(
            "Hujjat nomi. Admin panelda AI knowledge hujjatini tez topish uchun ishlatiladi. "
            "Masalan: 'Muddatni kim yaratadi', 'Hisobot qanday yuboriladi'."
        ),
    )

    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        verbose_name="Manba turi",
        help_text=(
            "Hujjat turi. "
            "'Qo'lda kiritilgan' — oddiy matn, "
            "'Model hujjati' — model yoki tushuncha izohi, "
            "'Ish jarayoni' — workflow, "
            "'Qoida' — biznes qoidasi."
        ),
    )

    source_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Manba kaliti",
        help_text=(
            "Kod orqali yangilash yoki sync qilish uchun unikal kalit. "
            "Masalan management command orqali hujjatni title emas, shu kalit bilan topish mumkin. "
            "Ixtiyoriy, lekin tavsiya qilinadi."
        ),
    )

    content = models.TextField(
        verbose_name="Kontent",
        help_text=(
            "AI foydalanadigan asosiy matn. "
            "Foydalanuvchi savoliga javob berishda aynan shu matndan chunklar ajratilib ishlatiladi. "
            "Matnni iloji boricha tushunarli, aniq va user tilida yozing."
        ),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metama'lumotlar",
        help_text=(
            "Qo'shimcha texnik ma'lumotlar. "
            "Masalan: {'lang': 'uz', 'faq': true, 'priority': 10}. "
            "Hozircha majburiy emas, lekin keyinchalik qidiruv va filtrlash uchun foydali."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
        help_text=(
            "Agar yoqilgan bo'lsa, AI bu hujjatdan foydalanadi. "
            "Agar o'chirilsa, hujjat bazada qoladi, lekin AI qidiruvida ishlatilmaydi."
        ),
    )

    class Meta:
        db_table = "ai_knowledge_document"
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["source_type", "is_active"]),
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_key"],
                condition=~Q(source_key=""),
                name="uq_ai_knowledge_document_source_key_not_empty",
            )
        ]

    def clean(self):
        self.title = (self.title or "").strip()
        self.source_key = (self.source_key or "").strip()
        self.content = (self.content or "").strip()

        if not self.title:
            raise ValidationError({"title": "Sarlavha bo'sh bo'lmasligi kerak."})

        if not self.content:
            raise ValidationError({"content": "Kontent bo'sh bo'lmasligi kerak."})

    def __str__(self):
        return self.title


class KnowledgeChunk(AbstractBaseModel):
    document = models.ForeignKey(
        KnowledgeDocument,
        related_name="chunks",
        on_delete=models.CASCADE,
        verbose_name="Hujjat",
        help_text=(
            "Bu chunk qaysi hujjatga tegishli ekanini ko'rsatadi. "
            "Bitta hujjat bir nechta chunklarga bo'linishi mumkin."
        ),
    )

    chunk_index = models.PositiveIntegerField(
        verbose_name="Bo'lak indeksi",
        help_text=(
            "Hujjat ichidagi chunk tartib raqami. "
            "Masalan 0, 1, 2 ... ko'rinishida bo'ladi."
        ),
    )

    text = models.TextField(
        verbose_name="Matn",
        help_text=(
            "Hujjatning AI qidiruvda ishlatiladigan bo'lagi. "
            "Bu odatda asosiy kontentdan avtomatik ajratilgan kichik matn parchasidir."
        ),
    )

    embedding = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Embedding",
        help_text=(
            "Chunk matnining vektor ko'rinishi. "
            "Bu AI semantic qidiruv qilishi uchun kerak bo'ladi. "
            "Odatda avtomatik generatsiya qilinadi, qo'lda to'ldirilmaydi."
        ),
    )

    token_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Tokenlar soni",
        help_text=(
            "Chunk ichidagi taxminiy tokenlar soni. "
            "Prompt uzunligini va matn hajmini nazorat qilish uchun foydali."
        ),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metama'lumotlar",
        help_text=(
            "Chunk darajasidagi qo'shimcha texnik ma'lumotlar. "
            "Masalan document title, til, source type yoki boshqa qidiruvga yordam beruvchi ma'lumotlar."
        ),
    )

    class Meta:
        db_table = "ai_knowledge_chunk"
        verbose_name = "Hujjat bo'lagi"
        verbose_name_plural = "Hujjat bo'laklari"
        ordering = ("document_id", "chunk_index")
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="uq_ai_knowledge_chunk_document_chunk_index",
            )
        ]

    def clean(self):
        self.text = (self.text or "").strip()

        if not self.text:
            raise ValidationError({"text": "Chunk matni bo'sh bo'lmasligi kerak."})

    def __str__(self):
        return f"{self.document.title} #{self.chunk_index}"